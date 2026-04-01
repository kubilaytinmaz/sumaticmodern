"""
Sumatic Modern IoT - Tuya Cloud Service
Manages Tuya smart devices via Cloud API using tinytuya library.
Supports device discovery, status monitoring, and control (on/off/toggle).
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.database import async_session_maker
from app.models.tuya_device import TuyaDevice

# Import tinytuya at module level
import sys

def get_tinytuya():
    """Get tinytuya module, trying multiple import strategies."""
    # First check sys.modules cache
    if 'tinytuya' in sys.modules:
        return sys.modules['tinytuya']
    # Try standard import
    try:
        import tinytuya
        return tinytuya
    except ImportError:
        pass
    # Try importlib as fallback
    try:
        import importlib
        tinytuya = importlib.import_module('tinytuya')
        return tinytuya
    except (ImportError, ModuleNotFoundError):
        pass
    return None

_tinytuya_mod = get_tinytuya()
TINYTUYA_AVAILABLE = _tinytuya_mod is not None

logger = get_logger(__name__)
settings = get_settings()


class TuyaCloudError(Exception):
    """Custom exception for Tuya Cloud API errors."""
    pass


class TuyaService:
    """
    Service for managing Tuya smart devices via Cloud API.
    
    Uses tinytuya library for cloud communication.
    Handles device discovery, status polling, and control commands.
    """

    def __init__(self):
        self._cloud: Optional[Any] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_poll: float = 0.0
        # Cache for device states: device_id -> {"online": bool, "on": bool, "last_updated": float}
        self._state_cache: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize Tuya Cloud connection."""
        if not settings.TUYA_ACCESS_ID or not settings.TUYA_ACCESS_SECRET:
            logger.warning("Tuya Cloud credentials not configured. Set TUYA_ACCESS_ID and TUYA_ACCESS_SECRET.")
            return

        try:
            _tinytuya = get_tinytuya()
            if _tinytuya is None:
                raise TuyaCloudError("tinytuya library not installed. Run: pip install tinytuya")
            
            self._cloud = _tinytuya.Cloud(
                apiRegion=settings.TUYA_API_REGION,
                apiKey=settings.TUYA_ACCESS_ID,
                apiSecret=settings.TUYA_ACCESS_SECRET,
            )
            
            # Test connection - Cloud constructor automatically gets token
            # Verify we got a valid token
            if self._cloud.token:
                logger.info(f"Tuya Cloud API connection established (region: {settings.TUYA_API_REGION})")
            else:
                error_msg = getattr(self._cloud, 'error', 'Unknown error')
                logger.warning(f"Tuya Cloud token not received: {error_msg}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Tuya Cloud: {e}")
            self._cloud = None
            raise

    async def start_polling(self) -> None:
        """Start background polling for device status updates."""
        if self._running:
            return
        
        if not self._cloud:
            logger.warning("Tuya Cloud not initialized, skipping polling start")
            return
        
        self._running = True
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info("Tuya device polling started")

    async def stop_polling(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        logger.info("Tuya device polling stopped")

    async def _poll_loop(self) -> None:
        """Background polling loop for device status."""
        while self._running:
            try:
                await self._poll_all_devices()
            except Exception as e:
                logger.error(f"Error in Tuya polling loop: {e}")
            
            await asyncio.sleep(settings.TUYA_POLL_INTERVAL_SECONDS)

    def _extract_power_state(self, status_list: list) -> Optional[bool]:
        """
        Extract power state from Tuya device status list.
        Tries switch_led, switch_1, switch codes in order.
        """
        if not status_list or not isinstance(status_list, list):
            return None
        
        # Priority order: switch_led (for light devices), switch_1, switch
        for code in ("switch_led", "switch_1", "switch"):
            for dp in status_list:
                if dp.get("code") == code:
                    return bool(dp.get("value", False))
        return None

    async def _poll_all_devices(self) -> None:
        """Poll status for all enabled Tuya devices from cloud."""
        if not self._cloud:
            return

        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(TuyaDevice).where(TuyaDevice.is_enabled == True)
                )
                devices = result.scalars().all()

                if not devices:
                    return

                # Get all device statuses from cloud in one call
                try:
                    cloud_devices = self._cloud.getdevices()
                    # DEBUG: Log the actual return type and content
                    logger.info(f"[TUYA DEBUG] getdevices() type={type(cloud_devices).__name__}")
                    if isinstance(cloud_devices, list):
                        logger.info(f"[TUYA DEBUG] getdevices() returned list with {len(cloud_devices)} items")
                        if cloud_devices:
                            logger.info(f"[TUYA DEBUG] First item keys: {list(cloud_devices[0].keys()) if isinstance(cloud_devices[0], dict) else 'not a dict'}")
                            logger.info(f"[TUYA DEBUG] First item: {cloud_devices[0]}")
                    elif isinstance(cloud_devices, dict):
                        logger.info(f"[TUYA DEBUG] getdevices() returned dict with keys: {list(cloud_devices.keys())}")
                except Exception as e:
                    logger.error(f"Failed to get devices from Tuya Cloud: {e}")
                    return

                # Build a map of cloud device statuses
                # Handle different response formats from tinytuya
                cloud_status_map: Dict[str, Dict[str, Any]] = {}
                device_list = []
                
                if cloud_devices:
                    if isinstance(cloud_devices, list):
                        device_list = cloud_devices
                    elif isinstance(cloud_devices, dict):
                        # Try different dict response formats
                        if "result" in cloud_devices:
                            result_data = cloud_devices["result"]
                            if isinstance(result_data, dict):
                                # Format 1: {result: {devices: [...]}}
                                device_list = result_data.get("devices", [])
                                # Format 2: {result: {list: [...]}}
                                if not device_list:
                                    device_list = result_data.get("list", [])
                            elif isinstance(result_data, list):
                                device_list = result_data
                    
                logger.info(f"[TUYA DEBUG] device_list has {len(device_list)} items, cloud_status_map keys: {list(cloud_status_map.keys())}")
                for dev in device_list:
                    dev_id = dev.get("id", "")
                    if dev_id:
                        cloud_status_map[dev_id] = dev
                        logger.info(f"[TUYA DEBUG] Cloud device {dev_id}: online={dev.get('online')!r} (type={type(dev.get('online')).__name__})")

                # Update each device
                for device in devices:
                    try:
                        cloud_info = cloud_status_map.get(device.device_id)
                        
                        if cloud_info:
                            is_online = cloud_info.get("online", False)
                            
                            # Get detailed status for this device
                            power_state = device.power_state
                            try:
                                status = self._cloud.getstatus(device.device_id)
                                extracted = self._extract_power_state(status)
                                if extracted is not None:
                                    power_state = extracted
                            except Exception as e:
                                logger.debug(f"Could not get status for {device.device_id}: {e}")

                            # Update device in database
                            device.is_online = is_online
                            device.power_state = power_state
                            device.last_seen_at = datetime.utcnow() if is_online else device.last_seen_at

                            # Update cache
                            self._state_cache[device.device_id] = {
                                "online": is_online,
                                "on": power_state,
                                "last_updated": time.time(),
                            }
                        else:
                            # Device not found in cloud - mark offline
                            device.is_online = False

                    except Exception as e:
                        logger.error(f"Error polling Tuya device {device.device_id}: {e}")

                await session.commit()

        except Exception as e:
            logger.error(f"Error in poll_all_devices: {e}")

    async def get_devices(self, db: AsyncSession) -> List[TuyaDevice]:
        """Get all Tuya devices from database, updating cloud status if available."""
        result = await db.execute(
            select(TuyaDevice).order_by(TuyaDevice.name)
        )
        devices = list(result.scalars().all())
        
        # If cloud is available, refresh status from cloud
        if self._cloud and devices:
            try:
                cloud_devices = self._cloud.getdevices()
                # Handle different response formats from tinytuya
                cloud_map: Dict[str, Dict[str, Any]] = {}
                device_list = []
                
                if cloud_devices:
                    if isinstance(cloud_devices, list):
                        device_list = cloud_devices
                    elif isinstance(cloud_devices, dict):
                        # Try different dict response formats
                        if "result" in cloud_devices:
                            result = cloud_devices["result"]
                            if isinstance(result, dict):
                                # Format 1: {result: {devices: [...]}}
                                device_list = result.get("devices", [])
                                # Format 2: {result: {list: [...]}}
                                if not device_list:
                                    device_list = result.get("list", [])
                            elif isinstance(result, list):
                                device_list = result
                
                for dev in device_list:
                    dev_id = dev.get("id", "")
                    if dev_id:
                        cloud_map[dev_id] = dev
                
                updated = False
                for device in devices:
                    cloud_info = cloud_map.get(device.device_id)
                    if cloud_info:
                        new_online = cloud_info.get("online", False)
                        if device.is_online != new_online:
                            device.is_online = new_online
                            updated = True
                        if new_online:
                            device.last_seen_at = datetime.utcnow()
                            updated = True
                        
                        # Try to get power state from status
                        try:
                            status = self._cloud.getstatus(device.device_id)
                            extracted = self._extract_power_state(status)
                            if extracted is not None and device.power_state != extracted:
                                device.power_state = extracted
                                updated = True
                        except Exception:
                            pass
                        
                        # Update cache
                        self._state_cache[device.device_id] = {
                            "online": device.is_online,
                            "on": device.power_state,
                            "last_updated": time.time(),
                        }
                
                if updated:
                    await db.commit()
                    # Re-read to get updated data
                    result = await db.execute(
                        select(TuyaDevice).order_by(TuyaDevice.name)
                    )
                    devices = list(result.scalars().all())
                    
            except Exception as e:
                logger.debug(f"Could not refresh cloud status in get_devices: {e}")
        
        return devices

    async def get_device(self, db: AsyncSession, device_id: int) -> Optional[TuyaDevice]:
        """Get a single Tuya device by internal ID."""
        result = await db.execute(
            select(TuyaDevice).where(TuyaDevice.id == device_id)
        )
        return result.scalar_one_or_none()

    async def get_device_by_tuya_id(self, db: AsyncSession, tuya_device_id: str) -> Optional[TuyaDevice]:
        """Get a single Tuya device by Tuya device ID."""
        result = await db.execute(
            select(TuyaDevice).where(TuyaDevice.device_id == tuya_device_id)
        )
        return result.scalar_one_or_none()

    async def create_device(self, db: AsyncSession, device_data: Dict[str, Any]) -> TuyaDevice:
        """Create a new Tuya device in database."""
        device = TuyaDevice(**device_data)
        db.add(device)
        await db.flush()
        await db.refresh(device)
        logger.info(f"Tuya device created: {device.device_id} ({device.name})")
        return device

    async def update_device(self, db: AsyncSession, device: TuyaDevice, update_data: Dict[str, Any]) -> TuyaDevice:
        """Update a Tuya device in database."""
        for key, value in update_data.items():
            if value is not None and hasattr(device, key):
                setattr(device, key, value)
        await db.flush()
        await db.refresh(device)
        logger.info(f"Tuya device updated: {device.device_id}")
        return device

    async def delete_device(self, db: AsyncSession, device: TuyaDevice) -> None:
        """Delete a Tuya device from database."""
        await db.delete(device)
        logger.info(f"Tuya device deleted: {device.device_id}")

    def _detect_switch_code(self, device_id: str) -> str:
        """
        Detect the correct switch code for a device by checking its status.
        Returns the appropriate switch code (switch_led, switch_1, or switch).
        """
        try:
            status = self._cloud.getstatus(device_id)
            if status and isinstance(status, list):
                codes = [dp.get("code", "") for dp in status]
                # Priority: switch_led (lights), switch_1 (plugs), switch (generic)
                for code in ("switch_led", "switch_1", "switch"):
                    if code in codes:
                        return code
        except Exception as e:
            logger.debug(f"Could not detect switch code for {device_id}: {e}")
        
        return "switch_1"  # Default fallback

    async def control_device(self, db: AsyncSession, device_id: int, action: str) -> Dict[str, Any]:
        """
        Control a Tuya device (turn on, turn off, or toggle).
        
        Args:
            db: Database session
            device_id: Internal device ID
            action: 'turn_on', 'turn_off', or 'toggle'
            
        Returns:
            Dict with success status and new power state
        """
        if not self._cloud:
            raise TuyaCloudError("Tuya Cloud not initialized. Check API credentials.")

        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")
        
        if not device.is_enabled:
            raise TuyaCloudError(f"Device is disabled: {device.name}")
        
        # Don't check online status here - let Tuya Cloud API handle it
        # The cloud will return an error if device is offline
        logger.info(f"Attempting to control device {device.name} ({device.device_id})")

        # Determine new state
        if action == "turn_on":
            new_state = True
        elif action == "turn_off":
            new_state = False
        elif action == "toggle":
            # Get current state from cloud for accurate toggle
            try:
                status = self._cloud.getstatus(device.device_id)
                current = self._extract_power_state(status)
                if current is not None:
                    new_state = not current
                else:
                    new_state = not device.power_state
            except Exception:
                new_state = not device.power_state
        else:
            raise TuyaCloudError(f"Invalid action: {action}")

        # Detect the correct switch code for this device
        switch_code = self._detect_switch_code(device.device_id)
        logger.info(f"Using switch code '{switch_code}' for device {device.device_id}")

        try:
            # Send command via Tuya Cloud API
            commands = {
                "commands": [
                    {
                        "code": switch_code,
                        "value": new_state,
                    }
                ]
            }
            
            result = self._cloud.sendcommand(device.device_id, commands)
            logger.info(f"Tuya sendcommand result for {device.device_id}: {result}")

            # tinytuya Cloud sendcommand returns the API response
            # Check if the result indicates success
            success = False
            if isinstance(result, dict):
                success = result.get("success", False)
            
            if success:
                # Update database
                device.power_state = new_state
                device.last_control_at = datetime.utcnow()
                await db.flush()
                await db.refresh(device)

                # Update cache
                self._state_cache[device.device_id] = {
                    "online": True,
                    "on": new_state,
                    "last_updated": time.time(),
                }

                logger.info(f"Tuya device {device.name}: {'ON' if new_state else 'OFF'} (action: {action})")
                
                return {
                    "success": True,
                    "power_state": new_state,
                    "message": f"Device {'turned on' if new_state else 'turned off'} successfully",
                }
            else:
                # Try fallback switch codes
                fallback_codes = ["switch_led", "switch_1", "switch"]
                fallback_codes = [c for c in fallback_codes if c != switch_code]
                
                for fallback_code in fallback_codes:
                    try:
                        commands["commands"][0]["code"] = fallback_code
                        result = self._cloud.sendcommand(device.device_id, commands)
                        logger.info(f"Fallback sendcommand with '{fallback_code}': {result}")
                        
                        if isinstance(result, dict) and result.get("success", False):
                            # Update database
                            device.power_state = new_state
                            device.last_control_at = datetime.utcnow()
                            await db.flush()
                            await db.refresh(device)

                            self._state_cache[device.device_id] = {
                                "online": True,
                                "on": new_state,
                                "last_updated": time.time(),
                            }

                            logger.info(f"Tuya device {device.name}: {'ON' if new_state else 'OFF'} via fallback '{fallback_code}'")
                            
                            return {
                                "success": True,
                                "power_state": new_state,
                                "message": f"Device {'turned on' if new_state else 'turned off'} successfully",
                            }
                    except Exception as e2:
                        logger.debug(f"Fallback '{fallback_code}' failed: {e2}")
                        continue
                
                error_msg = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
                raise TuyaCloudError(f"Failed to control device: {error_msg}")

        except TuyaCloudError:
            raise
        except Exception as e:
            logger.error(f"Error controlling Tuya device {device.device_id}: {e}")
            raise TuyaCloudError(f"Error controlling device: {str(e)}")

    async def get_device_status(self, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """Get real-time status of a Tuya device from cloud."""
        if not self._cloud:
            raise TuyaCloudError("Tuya Cloud not initialized")

        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")

        try:
            # Get online status from cloud
            cloud_devices = self._cloud.getdevices()
            is_online = False
            
            # Handle different response formats from tinytuya
            device_list = []
            if isinstance(cloud_devices, dict):
                # Format: {result: {devices: [...]}}
                if "result" in cloud_devices and isinstance(cloud_devices["result"], dict):
                    device_list = cloud_devices["result"].get("devices", [])
                # Format: {result: {list: [...]}}
                elif "result" in cloud_devices and isinstance(cloud_devices["result"], dict):
                    device_list = cloud_devices["result"].get("list", [])
            elif isinstance(cloud_devices, list):
                device_list = cloud_devices
            
            # Search for device in the list
            for dev in device_list:
                if dev.get("id") == device.device_id:
                    is_online = dev.get("online", False)
                    break
            
            status = self._cloud.getstatus(device.device_id)
            
            result = {
                "id": device.id,
                "device_id": device.device_id,
                "name": device.name,
                "is_online": is_online,
                "power_state": device.power_state,
                "dps": {},
            }

            if status and isinstance(status, list):
                for dp in status:
                    code = dp.get("code", "")
                    value = dp.get("value")
                    result["dps"][code] = value
                
                # Extract power state
                extracted = self._extract_power_state(status)
                if extracted is not None:
                    result["power_state"] = extracted

            # Update DB with cloud status
            if device.is_online != is_online or device.power_state != result["power_state"]:
                device.is_online = is_online
                device.power_state = result["power_state"]
                if is_online:
                    device.last_seen_at = datetime.utcnow()
                await db.commit()

            return result

        except Exception as e:
            logger.error(f"Error getting status for Tuya device {device.device_id}: {e}")
            raise TuyaCloudError(f"Error getting device status: {str(e)}")

    async def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Discover all devices from Tuya Cloud.
        Returns list of device info dicts from the cloud.
        """
        if not self._cloud:
            raise TuyaCloudError("Tuya Cloud not initialized")

        try:
            devices = self._cloud.getdevices()
            if not devices:
                return []
            
            discovered = []
            for dev in devices:
                discovered.append({
                    "device_id": dev.get("id", ""),
                    "name": dev.get("name", "Unknown"),
                    "product_id": dev.get("product_id", ""),
                    "product_name": dev.get("product_name", ""),
                    "device_type": dev.get("model", "unknown"),
                    "is_online": dev.get("online", False),
                    "ip": dev.get("ip", ""),
                    "local_key": dev.get("local_key", ""),
                })
            
            return discovered

        except Exception as e:
            logger.error(f"Error discovering Tuya devices: {e}")
            raise TuyaCloudError(f"Error discovering devices: {str(e)}")

    async def update_config(self, access_id: str, access_secret: str, api_region: str = "eu") -> None:
        """Update Tuya Cloud configuration and reinitialize connection."""
        # Stop current polling if running
        await self.stop_polling()
        
        # Update settings (runtime only - not persisted to .env)
        settings.TUYA_ACCESS_ID = access_id
        settings.TUYA_ACCESS_SECRET = access_secret
        settings.TUYA_API_REGION = api_region
        
        # Store credentials locally for get_status
        self._access_id = access_id
        self._access_secret = access_secret
        self._api_region = api_region
        
        # Reinitialize cloud connection
        self._cloud = None
        try:
            await self.initialize()
        except Exception as e:
            logger.warning(f"Failed to reinitialize Tuya Cloud after config update: {e}")
            # Still consider config updated - user may need to restart server
        
        # Start polling if initialization succeeded
        if self._cloud:
            await self.start_polling()
            logger.info(f"Tuya Cloud reconfigured with region: {api_region}")
        else:
            logger.warning("Tuya Cloud not connected after config update - credentials saved for next restart")

    def get_status(self) -> Dict[str, Any]:
        """Get Tuya service status."""
        access_id = getattr(self, '_access_id', settings.TUYA_ACCESS_ID) or ""
        api_region = getattr(self, '_api_region', settings.TUYA_API_REGION) or "eu"
        has_creds = bool(
            (getattr(self, '_access_id', None) or settings.TUYA_ACCESS_ID) and
            (getattr(self, '_access_secret', None) or settings.TUYA_ACCESS_SECRET)
        )
        return {
            "initialized": self._cloud is not None,
            "polling": self._running,
            "cached_devices": len(self._state_cache),
            "api_region": api_region,
            "has_credentials": has_creds,
            "access_id": access_id,
        }


# Global singleton
_tuya_service: Optional[TuyaService] = None


def get_tuya_service() -> TuyaService:
    """Get or create the Tuya service singleton."""
    global _tuya_service
    if _tuya_service is None:
        _tuya_service = TuyaService()
    return _tuya_service
