"""
Sumatic Modern IoT - Tuya Cloud Service
Manages Tuya smart devices via Cloud API using tinytuya library.
Supports device discovery, status monitoring, and control (on/off/toggle).
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.database import async_session_maker
from app.models.tuya_device import TuyaDevice
from app.models.tuya_device_control_log import TuyaDeviceControlLog

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
        self._initialization_attempted = False
        self._initialization_failed = False

    async def _ensure_cloud_connection(self) -> None:
        """
        Ensure cloud connection is initialized.
        If not, attempt to initialize it (lazy initialization / auto-reconnect).
        Raises TuyaCloudError if initialization fails.
        """
        if self._cloud is not None:
            return  # Already connected
        
        logger.info("Cloud connection not available, attempting (re)initialization...")
        
        if not settings.TUYA_ACCESS_ID or not settings.TUYA_ACCESS_SECRET:
            raise TuyaCloudError("Tuya Cloud credentials not configured. Set TUYA_ACCESS_ID and TUYA_ACCESS_SECRET.")
        
        try:
            await self.initialize()
        except Exception as e:
            logger.error(f"Cloud connection initialization failed: {e}")
            raise TuyaCloudError(f"Failed to initialize Tuya Cloud: {str(e)}")
        
        if self._cloud is None:
            raise TuyaCloudError("Tuya Cloud not initialized. Check API credentials.")

    async def initialize(self) -> None:
        """Initialize Tuya Cloud connection."""
        self._initialization_attempted = True
        if not settings.TUYA_ACCESS_ID or not settings.TUYA_ACCESS_SECRET:
            logger.warning("Tuya Cloud credentials not configured. Set TUYA_ACCESS_ID and TUYA_ACCESS_SECRET.")
            self._initialization_failed = True
            return

        try:
            # Always try direct import - don't rely on module-level cache
            # Works better in --reload mode and process restarts
            try:
                import tinytuya
                logger.info(f"tinytuya imported successfully, version: {getattr(tinytuya, '__version__', 'unknown')}")
            except ImportError as e:
                logger.error(f"Failed to import tinytuya: {e}")
                raise TuyaCloudError("tinytuya library not installed. Run: pip install tinytuya")
            
            self._cloud = tinytuya.Cloud(
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
        Tries switch_1, switch_led, switch codes in order.
        switch_1 is prioritized for plugs/switches, switch_led for lights.
        """
        if not status_list or not isinstance(status_list, list):
            return None
        
        # Priority order: switch_1 (plugs/switches), switch_led (lights), switch (generic)
        # This ensures plug devices work correctly even if they have switch_led in status
        for code in ("switch_1", "switch_led", "switch"):
            for dp in status_list:
                if dp.get("code") == code:
                    return bool(dp.get("value", False))
        return None

    async def _poll_all_devices(self) -> None:
        """Poll status for all enabled Tuya devices from cloud.
        
        Uses getdevices() API to get accurate online status from Tuya Cloud.
        Only devices that are truly online and reachable are marked as online.
        """
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
                # IMPORTANT: Use verbose=True to get raw JSON with 'online' status
                # Run in thread to avoid blocking the event loop (tinytuya uses sync urllib3)
                try:
                    cloud_response = await asyncio.to_thread(self._cloud.getdevices, verbose=True)
                except Exception as e:
                    logger.error(f"Failed to get devices from Tuya Cloud: {e}")
                    return

                # Build a map of cloud device statuses with online field
                cloud_status_map: Dict[str, Dict[str, Any]] = {}
                device_list = []
                
                # getdevices(verbose=True) returns raw dict with 'result' key containing the device list
                if cloud_response and isinstance(cloud_response, dict):
                    if 'result' in cloud_response:
                        # Handle both dict with 'devices' list (from associated-users API)
                        # and direct list (from iot-03 API)
                        result = cloud_response['result']
                        if isinstance(result, dict) and 'devices' in result:
                            device_list = result['devices']
                        elif isinstance(result, list):
                            device_list = result
                        
                        logger.debug(f"📋 Retrieved {len(device_list)} devices from cloud")
                        for dev in device_list:
                            dev_id = dev.get("id", "")
                            if dev_id:
                                cloud_status_map[dev_id] = dev
                                logger.debug(f"  - Device {dev_id}: online={dev.get('online', False)}")
                    else:
                        logger.warning(f"⚠️ getdevices() response missing 'result' key")
                        logger.debug(f"Response keys: {cloud_response.keys()}")
                else:
                    logger.warning(f"⚠️ Unexpected getdevices() response type: {type(cloud_response)}")
                    logger.debug(f"Response: {str(cloud_response)[:500]}")

                # Update each device
                for device in devices:
                    try:
                        cloud_info = cloud_status_map.get(device.device_id)
                        
                        # CRITICAL: Use the online field from getdevices API
                        # This is the most reliable indicator of device connectivity
                        if not cloud_info:
                            # Device not found in cloud response - mark offline
                            device.is_online = False
                            logger.debug(f"Device {device.device_id} not found in cloud - marking offline")
                            continue
                        
                        # Get online status from cloud API (this is the TRUTH)
                        is_online = cloud_info.get("online", False)
                        power_state = device.power_state
                        
                        # Only try to get detailed status if device is online
                        if is_online:
                            try:
                                status = await asyncio.to_thread(self._cloud.getstatus, device.device_id)
                                extracted = self._extract_power_state(status)
                                if extracted is not None:
                                    power_state = extracted
                            except Exception as e:
                                logger.debug(f"Could not get detailed status for {device.device_id}: {e}")
                                # Keep existing power_state if status fetch fails

                        # Update device in database
                        device.is_online = is_online
                        device.power_state = power_state
                        if is_online:
                            device.last_seen_at = datetime.utcnow()
                        # Don't update last_seen_at if offline - preserve last known time

                        # Update cache
                        self._state_cache[device.device_id] = {
                            "online": is_online,
                            "on": power_state,
                            "last_updated": time.time(),
                        }

                    except Exception as e:
                        logger.error(f"Error polling Tuya device {device.device_id}: {e}", exc_info=True)

                await session.commit()

        except Exception as e:
            logger.error(f"Error in poll_all_devices: {e}")

    async def get_devices(self, db: AsyncSession) -> List[TuyaDevice]:
        """Get all Tuya devices from database.
        
        Note: Device status is updated by the background polling task (_poll_all_devices).
        This method simply returns the current database state without making API calls.
        """
        result = await db.execute(
            select(TuyaDevice).order_by(TuyaDevice.name)
        )
        devices = list(result.scalars().all())
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
        Returns the appropriate switch code (switch_1, switch_led, or switch).
        switch_1 is prioritized for plugs/switches.
        """
        try:
            status = self._cloud.getstatus(device_id)
            if status and isinstance(status, list):
                codes = [dp.get("code", "") for dp in status]
                # Priority: switch_1 (plugs/switches), switch_led (lights), switch (generic)
                for code in ("switch_1", "switch_led", "switch"):
                    if code in codes:
                        return code
        except Exception as e:
            logger.debug(f"Could not detect switch code for {device_id}: {e}")
        
        return "switch_1"  # Default fallback

    async def control_device(self, db: AsyncSession, device_id: int, action: str, performed_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Control a Tuya device (turn on, turn off, or toggle) with audit logging.
        
        Args:
            db: Database session
            device_id: Internal device ID
            action: 'turn_on', 'turn_off', or 'toggle'
            performed_by: Optional username/identifier of who performed the action
            
        Returns:
            Dict with success status and new power state
        """
        await self._ensure_cloud_connection()

        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")
        
        if not device.is_enabled:
            raise TuyaCloudError(f"Device is disabled: {device.name}")
        
        # Store previous state for audit log
        previous_state = device.power_state
        
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

        success = False
        error_message = None
        actual_new_state = new_state

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

            # Check if the result indicates success
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
                            success = True
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
                            break
                    except Exception as e2:
                        logger.debug(f"Fallback '{fallback_code}' failed: {e2}")
                        continue
                
                if not success:
                    error_message = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Error controlling Tuya device {device.device_id}: {e}")

        # Create audit log entry
        control_log = TuyaDeviceControlLog(
            tuya_device_id=device.id,
            action=action,
            previous_state=previous_state,
            new_state=actual_new_state if success else None,
            success=success,
            error_message=error_message,
            performed_by=performed_by,
            performed_at=datetime.utcnow()
        )
        db.add(control_log)
        await db.commit()

        if not success:
            raise TuyaCloudError(f"Failed to control device: {error_message or 'Unknown error'}")
        
        return {
            "success": True,
            "power_state": new_state,
            "message": f"Device {'turned on' if new_state else 'turned off'} successfully",
        }

    async def get_device_status(self, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """Get real-time status of a Tuya device from cloud.
        
        Uses getdevices() API for accurate online status, then getstatus() for power state.
        """
        await self._ensure_cloud_connection()

        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")

        try:
            # Get online status from cloud with cache fallback
            is_online = self._get_cloud_online_status(device.device_id)
            
            # Only get detailed status if device is online
            power_state = device.power_state
            dps: Dict[str, Any] = {}
            
            if is_online:
                try:
                    status = self._cloud.getstatus(device.device_id)
                    if status and isinstance(status, list):
                        for dp in status:
                            code = dp.get("code", "")
                            value = dp.get("value")
                            dps[code] = value
                        
                        # Extract power state
                        extracted = self._extract_power_state(status)
                        if extracted is not None:
                            power_state = extracted
                except Exception as e:
                    logger.debug(f"Could not get detailed status for {device.device_id}: {e}")

            result = {
                "id": device.id,
                "device_id": device.device_id,
                "name": device.name,
                "is_online": is_online,
                "power_state": power_state,
                "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
                "last_control_at": device.last_control_at.isoformat() if device.last_control_at else None,
                "dps": dps,
            }

            # Update DB with cloud status
            if device.is_online != is_online or device.power_state != power_state:
                device.is_online = is_online
                device.power_state = power_state
                if is_online:
                    device.last_seen_at = datetime.utcnow()
                await db.commit()

            return result

        except Exception as e:
            logger.error(f"Error getting status for Tuya device {device.device_id}: {e}")
            raise TuyaCloudError(f"Error getting device status: {str(e)}")

    async def get_control_history(self, db: AsyncSession, device_id: int, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get paginated control history for a device."""
        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")
        
        offset = (page - 1) * page_size
        
        # Get total count
        count_result = await db.execute(
            select(func.count(TuyaDeviceControlLog.id)).where(
                TuyaDeviceControlLog.tuya_device_id == device_id
            )
        )
        total = count_result.scalar() or 0
        
        # Get paginated logs
        result = await db.execute(
            select(TuyaDeviceControlLog)
            .where(TuyaDeviceControlLog.tuya_device_id == device_id)
            .order_by(TuyaDeviceControlLog.performed_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        logs = list(result.scalars().all())
        
        return {
            "items": logs,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_device_details(self, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        """Get detailed device info with recent control history and stats."""
        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")
        
        # Get control stats
        total_result = await db.execute(
            select(func.count(TuyaDeviceControlLog.id)).where(
                TuyaDeviceControlLog.tuya_device_id == device_id
            )
        )
        total_controls = total_result.scalar() or 0
        
        success_result = await db.execute(
            select(func.count(TuyaDeviceControlLog.id)).where(
                TuyaDeviceControlLog.tuya_device_id == device_id,
                TuyaDeviceControlLog.success == True
            )
        )
        successful_controls = success_result.scalar() or 0
        
        failed_controls = total_controls - successful_controls
        
        # Get recent 10 control logs
        recent_result = await db.execute(
            select(TuyaDeviceControlLog)
            .where(TuyaDeviceControlLog.tuya_device_id == device_id)
            .order_by(TuyaDeviceControlLog.performed_at.desc())
            .limit(10)
        )
        recent_controls = list(recent_result.scalars().all())
        
        return {
            "device": device,
            "recent_controls": recent_controls,
            "total_controls": total_controls,
            "successful_controls": successful_controls,
            "failed_controls": failed_controls,
        }

    async def discover_devices(self) -> List[Dict[str, Any]]:
        """
        Discover all devices from Tuya Cloud.
        Returns list of device info dicts from the cloud.
        """
        await self._ensure_cloud_connection()

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
        
        # Update runtime settings
        settings.TUYA_ACCESS_ID = access_id
        settings.TUYA_ACCESS_SECRET = access_secret
        settings.TUYA_API_REGION = api_region
        
        # Store credentials locally for get_status
        self._access_id = access_id
        self._access_secret = access_secret
        self._api_region = api_region
        
        # Persist to .env file so it survives restarts
        try:
            import os
            from pathlib import Path
            
            # Find .env file in backend directory
            env_path = Path(__file__).parent.parent.parent / ".env"
            
            # Read existing .env content
            env_content = {}
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_content[key.strip()] = value.strip()
            
            # Update Tuya config
            env_content['TUYA_ACCESS_ID'] = access_id
            env_content['TUYA_ACCESS_SECRET'] = access_secret
            env_content['TUYA_API_REGION'] = api_region
            
            # Write back to .env
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in sorted(env_content.items()):
                    f.write(f"{key}={value}\n")
            
            logger.info(f"Tuya config persisted to {env_path}")
        except Exception as e:
            logger.warning(f"Failed to persist Tuya config to .env: {e}. Config will be lost on restart.")
        
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

    def _check_countdown_support(self, device_tuya_id: str) -> Optional[str]:
        """
        Check if a Tuya device supports countdown/timer DP for hardware-based restart.
        
        Returns the countdown DP code if supported, None otherwise.
        Checks for: countdown_1, countdown, add_ele
        """
        if not self._cloud:
            return None
        
        try:
            status = self._cloud.getstatus(device_tuya_id)
            if not status or not isinstance(status, list):
                return None
            
            codes = [dp.get("code", "") for dp in status]
            logger.info(f"Device {device_tuya_id} DPS codes: {codes}")
            
            # Priority order for countdown DP codes
            for code in ("countdown_1", "countdown", "add_ele"):
                if code in codes:
                    logger.info(f"Device {device_tuya_id} supports countdown via '{code}'")
                    return code
            
            logger.info(f"Device {device_tuya_id} does NOT support countdown")
            return None
        except Exception as e:
            logger.debug(f"Could not check countdown support for {device_tuya_id}: {e}")
            return None

    def _check_relay_status_support(self, device_tuya_id: str) -> bool:
        """
        Check if device supports relay_status (power-on recovery) DP.
        This allows the device to auto-turn-on after power is restored.
        """
        if not self._cloud:
            return False
        
        try:
            status = self._cloud.getstatus(device_tuya_id)
            if not status or not isinstance(status, list):
                return False
            
            codes = [dp.get("code", "") for dp in status]
            return "relay_status" in codes
        except Exception:
            return False

    def _get_cloud_online_status(self, device_tuya_id: str) -> bool:
        """
        Get online status from Tuya Cloud with cache fallback.
        
        Priority:
        1. Check Tuya Cloud API (getdevices with verbose=True)
        2. Fallback to _state_cache if API fails
        
        Returns True if device is online, False otherwise.
        """
        # Try cloud API first - use verbose=True to get raw JSON with online field
        try:
            cloud_response = self._cloud.getdevices(verbose=True)
            logger.debug(f"_get_cloud_online_status: getdevices(verbose=True) returned type={type(cloud_response)}")
            
            # getdevices(verbose=True) returns a dict with 'result' key
            if cloud_response and isinstance(cloud_response, dict):
                result = cloud_response.get("result", {})
                
                # Handle both dict with 'devices' list (from associated-users API)
                # and dict with 'list' key (from iot-03 API)
                device_list = []
                if isinstance(result, dict) and "devices" in result:
                    device_list = result["devices"]
                elif isinstance(result, dict) and "list" in result:
                    device_list = result["list"]
                elif isinstance(result, list):
                    device_list = result
                
                if device_list:
                    logger.debug(f"_get_cloud_online_status: Processing {len(device_list)} devices from cloud")
                    for dev in device_list:
                        if dev.get("id") == device_tuya_id:
                            is_online = dev.get("online", False)
                            logger.info(f"Device {device_tuya_id} cloud status: online={is_online}")
                            return is_online
                    
                    logger.warning(f"Device {device_tuya_id} not found in cloud devices list")
                else:
                    logger.warning(f"_get_cloud_online_status: No devices found in cloud response")
            else:
                logger.warning(f"_get_cloud_online_status: getdevices() returned unexpected format: {type(cloud_response)}")
        except Exception as e:
            logger.error(f"_get_cloud_online_status: Cloud API failed for {device_tuya_id}: {e}")
        
        # Fallback to cache
        cached = self._state_cache.get(device_tuya_id)
        if cached:
            cache_age = time.time() - cached.get("last_updated", 0)
            is_online = cached.get("online", False)
            logger.info(
                f"Device {device_tuya_id} using CACHED status: online={is_online} "
                f"(cache age: {cache_age:.1f}s)"
            )
            return is_online
        
        logger.warning(f"Device {device_tuya_id} not found in cloud or cache - assuming offline")
        return False

    async def restart_device(
        self,
        db: AsyncSession,
        device_id: int,
        delay_seconds: int = 5,
        force: bool = False,
        performed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Smart restart a Tuya device with automatic strategy selection.
        
        Strategy selection:
        1. If device supports countdown DP -> Hardware timer restart (works even if device controls modem)
        2. If device supports relay_status -> Set power-on recovery + turn off (device auto-recovers)
        3. Fallback -> Sequential restart (turn_off -> sleep -> turn_on)
        
        Args:
            db: Database session
            device_id: Internal device ID
            delay_seconds: Seconds to wait between off and on (2-30)
            force: Force restart even for network-critical devices
            performed_by: Optional username/identifier
            
        Returns:
            Dict with success status, strategy used, and final power state
        """
        await self._ensure_cloud_connection()

        device = await self.get_device(db, device_id)
        if not device:
            raise TuyaCloudError(f"Device not found: {device_id}")
        
        if not device.is_enabled:
            raise TuyaCloudError(f"Device is disabled: {device.name}")
        
        # Check real-time online status from cloud before restart
        logger.info(f"Restart request for device {device.name} ({device.device_id})")
        logger.debug(f"Device DB state: is_online={device.is_online}, power_state={device.power_state}")
        
        is_online = self._get_cloud_online_status(device.device_id)
        
        if not is_online:
            raise TuyaCloudError(
                f"Cihaz offline: {device.name}. "
                "Restart işlemi için cihazın online olması gerekiyor."
            )
        
        # Update database with latest online status
        if not device.is_online:
            device.is_online = True
            device.last_seen_at = datetime.utcnow()
            await db.flush()
            logger.info(f"Updated device {device.name} online status to True before restart")

        # Store previous state for audit log
        previous_state = device.power_state
        logger.info(f"Starting restart for device {device.name} ({device.device_id})")

        # Strategy 1: Try Cloud Timer restart (best for modem-connected plugs)
        # Timer is pushed to device firmware and executes locally even without internet
        timer_result = await self._restart_with_cloud_timer(
            db, device, delay_seconds, previous_state, performed_by
        )
        if timer_result:
            return timer_result

        # Strategy 2: Try countdown-based restart (hardware timer)
        countdown_code = self._check_countdown_support(device.device_id)
        if countdown_code:
            logger.info(f"Using COUNTDOWN strategy for {device.name} (code: {countdown_code})")
            result = await self._restart_with_countdown(
                db, device, countdown_code, delay_seconds, previous_state, performed_by
            )
            return result

        # Strategy 3: Try relay_status (power-on recovery)
        if self._check_relay_status_support(device.device_id):
            logger.info(f"Using RELAY_STATUS strategy for {device.name}")
            result = await self._restart_with_relay_status(
                db, device, delay_seconds, previous_state, performed_by
            )
            return result

        # Strategy 4: Sequential restart (fallback)
        logger.info(f"Using SEQUENTIAL strategy for {device.name}")
        result = await self._restart_sequential(
            db, device, delay_seconds, previous_state, performed_by
        )
        return result

    async def _restart_with_cloud_timer(
        self,
        db: AsyncSession,
        device: TuyaDevice,
        delay_seconds: int,
        previous_state: bool,
        performed_by: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Restart using Tuya Cloud Timer API.
        Creates two timers: OFF in 2 minutes, ON in 3 minutes.
        Timers are pushed to device firmware and execute locally even without internet.
        This is the BEST strategy for modem-connected plugs.
        
        Returns None if timer API fails (to fallback to other strategies).
        """
        if not self._cloud:
            logger.warning("Cloud not available for timer restart")
            return None
        
        success = False
        error_message = None
        timer_ids = []
        
        try:
            from datetime import datetime, timedelta
            
            now = datetime.now()
            # Use 3 minutes for OFF, 4 minutes for ON (timer needs enough lead time)
            turn_off_time = now + timedelta(minutes=3)
            turn_on_time = now + timedelta(minutes=4)
            
            # IMPORTANT: Timer API always expects "power" code regardless of device's actual function code
            # This was discovered through testing - Timer API rejects "switch_1" and "switch_led"
            # Device might use "switch_1", "switch_led", or "power" for control commands,
            # but Timer API ONLY accepts "power" code
            timer_api_code = "power"
            logger.info(f"Using Cloud Timer API for {device.name} with code={timer_api_code}")
            
            # Create OFF timer
            off_payload = {
                "time": turn_off_time.strftime("%H:%M"),
                "timezone_id": "Europe/Istanbul",
                "date": turn_off_time.strftime("%Y%m%d"),
                "loops": "0000000",  # One-time
                "functions": [{"code": timer_api_code, "value": False}]
            }
            
            off_uri = f"/v2.0/cloud/timer/device/{device.device_id}"
            off_result = self._cloud.cloudrequest(off_uri, action="POST", post=off_payload)
            
            if not off_result or not off_result.get("success"):
                logger.warning(f"Cloud Timer OFF failed for {device.device_id}: {off_result}")
                return None
            
            timer_id_off = off_result.get("result", {}).get("timer_id")
            timer_ids.append(timer_id_off)
            logger.info(f"Created OFF timer {timer_id_off} for {device.name} at {turn_off_time.strftime('%H:%M')}")
            
            # Wait 20 seconds before creating ON timer to avoid overwhelming Tuya Cloud API
            import asyncio
            await asyncio.sleep(20)
            logger.debug(f"Waited 20 seconds after OFF timer creation, now creating ON timer")
            
            # Create ON timer
            on_payload = {
                "time": turn_on_time.strftime("%H:%M"),
                "timezone_id": "Europe/Istanbul",
                "date": turn_on_time.strftime("%Y%m%d"),
                "loops": "0000000",  # One-time
                "functions": [{"code": timer_api_code, "value": True}]
            }
            
            on_result = self._cloud.cloudrequest(off_uri, action="POST", post=on_payload)
            
            if not on_result or not on_result.get("success"):
                logger.warning(f"Cloud Timer ON failed for {device.device_id}: {on_result}")
                # Clean up OFF timer
                try:
                    del_uri = f"/v2.0/cloud/timer/device/{device.device_id}/{timer_id_off}"
                    self._cloud.cloudrequest(del_uri, action="DELETE")
                except:
                    pass
                return None
            
            timer_id_on = on_result.get("result", {}).get("timer_id")
            timer_ids.append(timer_id_on)
            logger.info(f"Created ON timer {timer_id_on} for {device.name} at {turn_on_time.strftime('%H:%M')}")
            
            success = True
            
            # Update database
            device.power_state = False  # Will be off soon
            device.last_control_at = datetime.utcnow()
            await db.flush()
            
            # Update cache
            self._state_cache[device.device_id] = {
                "online": True,
                "on": False,
                "last_updated": time.time(),
                "restart_pending": True,
                "restart_eta": time.time() + delay_seconds,
                "timer_ids": timer_ids,
            }
            
            logger.info(
                f"Device {device.name}: Cloud Timer restart initiated "
                f"(OFF at {turn_off_time.strftime('%H:%M')}, ON at {turn_on_time.strftime('%H:%M')})"
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Error in Cloud Timer restart for {device.device_id}: {e}")
        
        # Create audit log
        control_log = TuyaDeviceControlLog(
            tuya_device_id=device.id,
            action="restart_timer",
            previous_state=previous_state,
            new_state=False if success else None,
            success=success,
            error_message=error_message,
            performed_by=performed_by,
            performed_at=datetime.utcnow(),
        )
        db.add(control_log)
        await db.commit()
        
        if not success:
            return None
        
        return {
            "success": True,
            "power_state": False,
            "strategy": "timer",
            "message": (
                f"Cihaz 3 dakika sonra kapanacak, 4 dakika sonra açılacak. "
                f"Timer'lar cihazın hafızasına kaydedildi, internet olmasa bile çalışacak."
            ),
            "delay_seconds": delay_seconds,
            "timer_ids": timer_ids,
        }

    async def _restart_with_countdown(
        self,
        db: AsyncSession,
        device: TuyaDevice,
        countdown_code: str,
        delay_seconds: int,
        previous_state: bool,
        performed_by: Optional[str],
    ) -> Dict[str, Any]:
        """
        Restart using hardware countdown timer.
        Sends turn_off + countdown in a single command.
        The device's internal timer will turn it back on after delay_seconds.
        This works even if the device controls the modem/router.
        """
        switch_code = self._detect_switch_code(device.device_id)
        
        success = False
        error_message = None

        try:
            # Send both commands together: turn off + set countdown to auto-turn-on
            commands = {
                "commands": [
                    {"code": switch_code, "value": False},
                    {"code": countdown_code, "value": delay_seconds},
                ]
            }
            
            result = self._cloud.sendcommand(device.device_id, commands)
            logger.info(f"Countdown restart result for {device.device_id}: {result}")
            
            if isinstance(result, dict):
                success = result.get("success", False)
            
            if success:
                # Update database - device will be off now, but will auto-turn-on
                device.power_state = False  # Currently off
                device.last_control_at = datetime.utcnow()
                await db.flush()
                await db.refresh(device)

                # Update cache
                self._state_cache[device.device_id] = {
                    "online": True,
                    "on": False,
                    "last_updated": time.time(),
                    "restart_pending": True,
                    "restart_eta": time.time() + delay_seconds,
                }

                logger.info(
                    f"Device {device.name}: RESTART initiated via countdown "
                    f"(will auto-turn-on in {delay_seconds}s)"
                )
            else:
                error_message = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
                
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Error in countdown restart for {device.device_id}: {e}")

        # Create audit log
        control_log = TuyaDeviceControlLog(
            tuya_device_id=device.id,
            action="restart_countdown",
            previous_state=previous_state,
            new_state=True if success else None,
            success=success,
            error_message=error_message,
            performed_by=performed_by,
            performed_at=datetime.utcnow(),
        )
        db.add(control_log)
        await db.commit()

        if not success:
            raise TuyaCloudError(f"Countdown restart failed: {error_message or 'Unknown error'}")
        
        return {
            "success": True,
            "power_state": False,  # Currently off, will auto-turn-on
            "strategy": "countdown",
            "message": f"Cihaz countdown ile yeniden başlatılıyor ({delay_seconds} saniye içinde açılacak)",
            "delay_seconds": delay_seconds,
        }

    async def _restart_with_relay_status(
        self,
        db: AsyncSession,
        device: TuyaDevice,
        delay_seconds: int,
        previous_state: bool,
        performed_by: Optional[str],
    ) -> Dict[str, Any]:
        """
        Restart using relay_status (power-on recovery) + turn off.
        Sets relay_status to 'power_on' so device auto-recovers, then turns off.
        """
        switch_code = self._detect_switch_code(device.device_id)
        
        success = False
        error_message = None

        try:
            # First, set relay_status to power_on (auto-recover after power loss)
            commands = {
                "commands": [
                    {"code": "relay_status", "value": "power_on"},
                    {"code": switch_code, "value": False},
                ]
            }
            
            result = self._cloud.sendcommand(device.device_id, commands)
            logger.info(f"Relay status restart result for {device.device_id}: {result}")
            
            if isinstance(result, dict):
                success = result.get("success", False)
            
            if success:
                device.power_state = False
                device.last_control_at = datetime.utcnow()
                await db.flush()
                await db.refresh(device)

                self._state_cache[device.device_id] = {
                    "online": True,
                    "on": False,
                    "last_updated": time.time(),
                    "restart_pending": True,
                }

                logger.info(f"Device {device.name}: RESTART via relay_status (power-on recovery enabled)")
            else:
                error_message = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
                
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Error in relay_status restart for {device.device_id}: {e}")

        # Create audit log
        control_log = TuyaDeviceControlLog(
            tuya_device_id=device.id,
            action="restart_relay",
            previous_state=previous_state,
            new_state=True if success else None,
            success=success,
            error_message=error_message,
            performed_by=performed_by,
            performed_at=datetime.utcnow(),
        )
        db.add(control_log)
        await db.commit()

        if not success:
            raise TuyaCloudError(f"Relay status restart failed: {error_message or 'Unknown error'}")
        
        return {
            "success": True,
            "power_state": False,
            "strategy": "relay_status",
            "message": "Cihaz power-on recovery ile yeniden başlatılıyor (elektrik gelince otomatik açılacak)",
            "delay_seconds": delay_seconds,
        }

    async def _restart_sequential(
        self,
        db: AsyncSession,
        device: TuyaDevice,
        delay_seconds: int,
        previous_state: bool,
        performed_by: Optional[str],
    ) -> Dict[str, Any]:
        """
        Restart using sequential commands: turn_off -> sleep -> turn_on.
        This is the fallback strategy. Works for normal devices but NOT for
        devices that control the modem/router (internet will be lost).
        """
        switch_code = self._detect_switch_code(device.device_id)
        
        # Phase 1: Turn off
        off_success = False
        off_error = None
        
        try:
            commands = {"commands": [{"code": switch_code, "value": False}]}
            result = self._cloud.sendcommand(device.device_id, commands)
            logger.info(f"Sequential restart - turn_off result for {device.device_id}: {result}")
            
            if isinstance(result, dict):
                off_success = result.get("success", False)
            
            if off_success:
                device.power_state = False
                device.last_control_at = datetime.utcnow()
                await db.flush()

                # Log turn_off phase
                off_log = TuyaDeviceControlLog(
                    tuya_device_id=device.id,
                    action="restart_off",
                    previous_state=previous_state,
                    new_state=False,
                    success=True,
                    performed_by=performed_by,
                    performed_at=datetime.utcnow(),
                )
                db.add(off_log)
                await db.commit()
            else:
                off_error = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
                
        except Exception as e:
            off_success = False
            off_error = str(e)
            logger.error(f"Sequential restart - turn_off failed for {device.device_id}: {e}")

        if not off_success:
            # Log failed turn_off
            off_log = TuyaDeviceControlLog(
                tuya_device_id=device.id,
                action="restart_off",
                previous_state=previous_state,
                new_state=None,
                success=False,
                error_message=off_error,
                performed_by=performed_by,
                performed_at=datetime.utcnow(),
            )
            db.add(off_log)
            await db.commit()
            raise TuyaCloudError(f"Restart failed at turn_off phase: {off_error or 'Unknown error'}")

        # Phase 2: Wait
        logger.info(f"Sequential restart - waiting {delay_seconds}s for {device.name}")
        await asyncio.sleep(delay_seconds)

        # Phase 3: Turn on (fire-and-forget - don't fail if turn_on doesn't work)
        on_success = False
        on_error = None
        turn_on_attempted = True
        
        try:
            commands = {"commands": [{"code": switch_code, "value": True}]}
            result = self._cloud.sendcommand(device.device_id, commands)
            logger.info(f"Sequential restart - turn_on result for {device.device_id}: {result}")
            
            if isinstance(result, dict):
                on_success = result.get("success", False)
            
            if on_success:
                device.power_state = True
                device.last_control_at = datetime.utcnow()
                await db.flush()
                await db.refresh(device)

                self._state_cache[device.device_id] = {
                    "online": True,
                    "on": True,
                    "last_updated": time.time(),
                }

                logger.info(f"Device {device.name}: Sequential restart completed successfully")
            else:
                on_error = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
                logger.warning(f"Sequential restart - turn_on failed for {device.device_id}: {on_error}")
                
        except Exception as e:
            on_success = False
            on_error = str(e)
            logger.warning(f"Sequential restart - turn_on failed for {device.device_id}: {e} (fire-and-forget mode)")

        # Log turn_on phase
        on_log = TuyaDeviceControlLog(
            tuya_device_id=device.id,
            action="restart_on",
            previous_state=False,
            new_state=True if on_success else None,
            success=on_success,
            error_message=on_error,
            performed_by=performed_by,
            performed_at=datetime.utcnow(),
        )
        db.add(on_log)
        await db.commit()

        # Fire-and-forget: Return success even if turn_on failed
        # The device was turned off successfully, and we attempted to turn it back on.
        # If the device controls the modem/router, turn_on will fail because internet is down.
        # The device may need to be manually turned on, or it will come back when power is restored.
        if on_success:
            return {
                "success": True,
                "power_state": True,
                "strategy": "sequential",
                "message": "Cihaz başarıyla yeniden başlatıldı",
                "delay_seconds": delay_seconds,
            }
        else:
            return {
                "success": True,
                "power_state": False,
                "strategy": "sequential",
                "turn_on_failed": True,
                "message": (
                    f"Cihaz kapatıldı ve {delay_seconds} saniye beklendi. "
                    f"Tekrar açma komutu gönderilemedi (muhtemelen internet bağlantısı kesildi). "
                    f"Cihaz countdown/cycle desteklemediği için bu beklenen bir durumdur. "
                    f"Cihazı fiziksel olarak (butondan) açmanız gerekebilir."
                ),
                "delay_seconds": delay_seconds,
            }


# Global singleton
_tuya_service: Optional[TuyaService] = None


def get_tuya_service() -> TuyaService:
    """Get or create the Tuya service singleton."""
    global _tuya_service
    if _tuya_service is None:
        _tuya_service = TuyaService()
    return _tuya_service
