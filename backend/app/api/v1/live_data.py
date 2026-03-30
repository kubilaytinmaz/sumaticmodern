"""
Live Data API Endpoint
Provides real-time device data and database insertions for monitoring.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc, func

from app.core.logging import get_logger
from app.database import async_session_maker
from app.models.device import Device
from app.models.reading import DeviceReading
from app.services.insertion_log import get_recent_insertions, InsertionLogEntry

logger = get_logger(__name__)
router = APIRouter(tags=["Live Data"])


class DeviceLiveData(BaseModel):
    """Live data for a single device."""
    device_id: int
    device_code: str
    device_name: str
    modem_id: str
    device_addr: int
    is_online: bool
    last_seen_at: Optional[str] = None
    cache_data: Dict[str, int] = {}
    last_db_reading: Optional[Dict[str, Any]] = None




class LiveDataResponse(BaseModel):
    """Response containing all live data."""
    devices: List[DeviceLiveData]
    recent_insertions: List[InsertionLogEntry]
    mqtt_status: Dict[str, Any]
    timestamp: str




@router.get("/live-data", response_model=LiveDataResponse)
async def get_live_data(
    limit_insertions: int = Query(default=50, ge=1, le=200)
):
    """
    Get current live data from all devices.
    
    Args:
        limit_insertions: Maximum number of recent insertions to return
    
    Returns:
        Live data including device status, cache, and recent DB insertions
    """
    try:
        # Import here to avoid circular imports
        from app.services.mqtt_consumer import get_mqtt_consumer
        mqtt_consumer = get_mqtt_consumer()
        mqtt_status = mqtt_consumer.get_status()
        
        # Get device configurations from MQTT consumer
        device_configs = mqtt_consumer._device_cfg
        cache_data = mqtt_consumer._cache
        last_seen = mqtt_consumer._last_seen
        
        devices_live = []
        
        async with async_session_maker() as session:
            # Get all enabled devices
            result = await session.execute(
                select(Device).where(Device.is_enabled == True)
            )
            db_devices = result.scalars().all()
            
            for device in db_devices:
                # Check if device is in MQTT consumer's config
                cfg_key = (device.modem_id, device.device_addr)
                cfg = device_configs.get(cfg_key)
                
                if not cfg:
                    continue
                
                device_code = cfg["device_code"]
                
                # Get cache data for this device
                device_cache = cache_data.get(device_code, {})
                
                # Get last seen time
                last_seen_unix = last_seen.get(device_code, 0)
                last_seen_at = None
                if last_seen_unix > 0:
                    last_seen_at = datetime.fromtimestamp(last_seen_unix).isoformat()
                
                # Determine online status
                from app.config import get_settings
                settings = get_settings()
                age = datetime.now().timestamp() - last_seen_unix
                is_online = last_seen_unix > 0 and age <= settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
                
                # Get last DB reading
                last_reading = None
                reading_result = await session.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .order_by(desc(DeviceReading.timestamp))
                    .limit(1)
                )
                last_reading_obj = reading_result.scalar_one_or_none()
                if last_reading_obj:
                    last_reading = {
                        "timestamp": last_reading_obj.timestamp.isoformat(),
                        "counter_19l": last_reading_obj.counter_19l,
                        "counter_5l": last_reading_obj.counter_5l,
                        "status": last_reading_obj.status
                    }
                
                devices_live.append(DeviceLiveData(
                    device_id=device.id,
                    device_code=device_code,
                    device_name=device.name or device_code,
                    modem_id=device.modem_id,
                    device_addr=device.device_addr,
                    is_online=is_online,
                    last_seen_at=last_seen_at,
                    cache_data=device_cache,
                    last_db_reading=last_reading
                ))
        
        return LiveDataResponse(
            devices=devices_live,
            recent_insertions=get_recent_insertions(limit_insertions),
            mqtt_status=mqtt_status,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting live data: {e}")
        raise


@router.get("/live-data/insertions", response_model=List[InsertionLogEntry])
async def get_live_insertions(limit: int = Query(default=50, ge=1, le=200)):
    """Get recent database insertion logs."""
    return get_recent_insertions(limit)


@router.websocket("/ws/live-data")
async def live_data_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time live data streaming.
    Sends updates every 2 seconds.
    """
    await websocket.accept()
    logger.info("Live data WebSocket client connected")
    
    try:
        # Send initial data
        initial_data = await get_live_data()
        await websocket.send_json({
            "type": "initial",
            "data": initial_data.model_dump()
        })
        
        # Keep connection alive and send updates
        while True:
            import asyncio
            await asyncio.sleep(2)  # Update every 2 seconds
            
            # Send current live data
            current_data = await get_live_data()
            await websocket.send_json({
                "type": "update",
                "data": current_data.model_dump()
            })
            
            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("Live data WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Live data WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
