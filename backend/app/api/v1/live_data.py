"""
Live Data API Endpoint
Provides real-time device data and database insertions for monitoring.
Also provides direct database browsing capabilities.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import select, and_, desc, func, text, cast, String

from app.core.logging import get_logger
from app.database import async_session_maker
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.device_status import DeviceHourlyStatus, DeviceStatusSnapshot
from app.models.monthly_revenue import MonthlyRevenueRecord
from app.models.device_month_cycle import DeviceMonthCycle
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


# ============================================================================
# DATABASE BROWSER ENDPOINTS - Direct database queries for monitoring
# ============================================================================

class DatabaseStats(BaseModel):
    """Database statistics and counts."""
    table_name: str
    total_count: int
    recent_count_24h: Optional[int] = None
    oldest_record: Optional[str] = None
    newest_record: Optional[str] = None


class DatabaseBrowseResponse(BaseModel):
    """Response for database browsing."""
    table_name: str
    total_count: int
    page: int
    page_size: int
    total_pages: int
    records: List[Dict[str, Any]]


@router.get("/db/stats")
async def get_database_stats():
    """
    Get comprehensive database statistics for all main tables.
    Shows record counts and date ranges.
    """
    try:
        async with async_session_maker() as session:
            stats = []
            
            # Device Readings
            result = await session.execute(select(func.count(DeviceReading.id)))
            readings_count = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(DeviceReading.id))
                .where(DeviceReading.timestamp >= datetime.utcnow() - timedelta(hours=24))
            )
            readings_24h = result.scalar() or 0
            
            result = await session.execute(
                select(func.min(DeviceReading.timestamp), func.max(DeviceReading.timestamp))
            )
            min_ts, max_ts = result.one()
            
            stats.append(DatabaseStats(
                table_name="device_readings",
                total_count=readings_count,
                recent_count_24h=readings_24h,
                oldest_record=min_ts.isoformat() if min_ts else None,
                newest_record=max_ts.isoformat() if max_ts else None
            ))
            
            # Devices
            result = await session.execute(select(func.count(Device.id)))
            devices_count = result.scalar() or 0
            stats.append(DatabaseStats(
                table_name="devices",
                total_count=devices_count
            ))
            
            # Hourly Status
            result = await session.execute(select(func.count(DeviceHourlyStatus.id)))
            hourly_count = result.scalar() or 0
            result = await session.execute(
                select(func.min(DeviceHourlyStatus.hour_start), func.max(DeviceHourlyStatus.hour_start))
            )
            min_h, max_h = result.one()
            stats.append(DatabaseStats(
                table_name="device_hourly_status",
                total_count=hourly_count,
                oldest_record=min_h.isoformat() if min_h else None,
                newest_record=max_h.isoformat() if max_h else None
            ))
            
            # Status Snapshots
            result = await session.execute(select(func.count(DeviceStatusSnapshot.id)))
            snapshot_count = result.scalar() or 0
            result = await session.execute(
                select(func.min(DeviceStatusSnapshot.snapshot_time), func.max(DeviceStatusSnapshot.snapshot_time))
            )
            min_s, max_s = result.one()
            stats.append(DatabaseStats(
                table_name="device_status_snapshots",
                total_count=snapshot_count,
                oldest_record=min_s.isoformat() if min_s else None,
                newest_record=max_s.isoformat() if max_s else None
            ))
            
            # Monthly Revenue
            result = await session.execute(select(func.count(MonthlyRevenueRecord.id)))
            revenue_count = result.scalar() or 0
            stats.append(DatabaseStats(
                table_name="monthly_revenue_records",
                total_count=revenue_count
            ))
            
            # Month Cycles
            result = await session.execute(select(func.count(DeviceMonthCycle.id)))
            cycle_count = result.scalar() or 0
            stats.append(DatabaseStats(
                table_name="device_month_cycles",
                total_count=cycle_count
            ))
            
            return {
                "stats": [s.model_dump() for s in stats],
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise


@router.get("/db/readings", response_model=DatabaseBrowseResponse)
async def browse_device_readings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Records per page"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    status: Optional[str] = Query(None, description="Filter by status (online/offline)"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """
    Browse device_readings table with pagination and filters.
    Returns raw database records for monitoring.
    """
    try:
        async with async_session_maker() as session:
            # Build query
            query = select(DeviceReading).join(Device, DeviceReading.device_id == Device.id)
            
            # Apply filters
            filters = []
            if device_id:
                filters.append(DeviceReading.device_id == device_id)
            if status:
                filters.append(DeviceReading.status == status.lower())
            if start_date:
                filters.append(DeviceReading.timestamp >= start_date)
            if end_date:
                filters.append(DeviceReading.timestamp <= end_date)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(DeviceReading)
            if filters:
                count_query = count_query.where(and_(*filters))
            result = await session.execute(count_query)
            total_count = result.scalar() or 0
            
            # Apply ordering and pagination
            if order == "desc":
                query = query.order_by(desc(DeviceReading.timestamp))
            else:
                query = query.order_by(DeviceReading.timestamp)
            
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # Execute query
            result = await session.execute(query)
            readings = result.scalars().all()
            
            # Get device info for each reading
            device_cache = {}
            records = []
            for reading in readings:
                if reading.device_id not in device_cache:
                    device_result = await session.execute(
                        select(Device).where(Device.id == reading.device_id)
                    )
                    device = device_result.scalar_one_or_none()
                    device_cache[reading.device_id] = device
                
                device = device_cache[reading.device_id]
                records.append({
                    "id": reading.id,
                    "device_id": reading.device_id,
                    "device_code": device.device_code if device else "Unknown",
                    "device_name": device.name if device else "Unknown",
                    "timestamp": reading.timestamp.isoformat(),
                    "counter_19l": reading.counter_19l,
                    "counter_5l": reading.counter_5l,
                    "status": reading.status
                })
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return DatabaseBrowseResponse(
                table_name="device_readings",
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                records=records
            )
            
    except Exception as e:
        logger.error(f"Error browsing device readings: {e}")
        raise


@router.get("/db/devices")
async def browse_devices():
    """
    Get all devices with their latest reading information.
    Useful for monitoring device configurations.
    """
    try:
        async with async_session_maker() as session:
            # Get all devices
            result = await session.execute(
                select(Device).order_by(Device.id)
            )
            devices = result.scalars().all()
            
            records = []
            for device in devices:
                # Get latest reading
                reading_result = await session.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .order_by(desc(DeviceReading.timestamp))
                    .limit(1)
                )
                latest_reading = reading_result.scalar_one_or_none()
                
                # Get reading count
                count_result = await session.execute(
                    select(func.count(DeviceReading.id))
                    .where(DeviceReading.device_id == device.id)
                )
                reading_count = count_result.scalar() or 0
                
                records.append({
                    "id": device.id,
                    "device_code": device.device_code,
                    "name": device.name,
                    "modem_id": device.modem_id,
                    "device_addr": device.device_addr,
                    "location": device.location,
                    "is_enabled": device.is_enabled,
                    "is_pending": device.is_pending,
                    "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
                    "created_at": device.created_at.isoformat(),
                    "total_readings": reading_count,
                    "latest_reading": {
                        "timestamp": latest_reading.timestamp.isoformat(),
                        "counter_19l": latest_reading.counter_19l,
                        "counter_5l": latest_reading.counter_5l,
                        "status": latest_reading.status
                    } if latest_reading else None
                })
            
            return {
                "table_name": "devices",
                "total_count": len(records),
                "records": records,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error browsing devices: {e}")
        raise


@router.get("/db/hourly-status")
async def browse_hourly_status(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    device_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Browse device_hourly_status table."""
    try:
        async with async_session_maker() as session:
            query = select(DeviceHourlyStatus).join(Device, DeviceHourlyStatus.device_id == Device.id)
            
            filters = []
            if device_id:
                filters.append(DeviceHourlyStatus.device_id == device_id)
            if start_date:
                filters.append(DeviceHourlyStatus.hour_start >= start_date)
            if end_date:
                filters.append(DeviceHourlyStatus.hour_start <= end_date)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Count
            count_query = select(func.count()).select_from(DeviceHourlyStatus)
            if filters:
                count_query = count_query.where(and_(*filters))
            result = await session.execute(count_query)
            total_count = result.scalar() or 0
            
            # Query
            query = query.order_by(desc(DeviceHourlyStatus.hour_start))
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            result = await session.execute(query)
            statuses = result.scalars().all()
            
            # Get device info
            device_cache = {}
            records = []
            for status in statuses:
                if status.device_id not in device_cache:
                    device_result = await session.execute(
                        select(Device).where(Device.id == status.device_id)
                    )
                    device = device_result.scalar_one_or_none()
                    device_cache[status.device_id] = device
                
                device = device_cache[status.device_id]
                records.append({
                    "id": status.id,
                    "device_id": status.device_id,
                    "device_code": device.device_code if device else "Unknown",
                    "hour_start": status.hour_start.isoformat(),
                    "hour_end": status.hour_end.isoformat(),
                    "status": status.status,
                    "online_minutes": status.online_minutes,
                    "offline_minutes": status.offline_minutes,
                    "data_points": status.data_points
                })
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                "table_name": "device_hourly_status",
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "records": records
            }
            
    except Exception as e:
        logger.error(f"Error browsing hourly status: {e}")
        raise


@router.get("/db/monthly-revenue")
async def browse_monthly_revenue():
    """Browse monthly_revenue_records table."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(MonthlyRevenueRecord)
                .join(Device, MonthlyRevenueRecord.device_id == Device.id)
                .order_by(desc(MonthlyRevenueRecord.year), desc(MonthlyRevenueRecord.month))
            )
            revenues = result.scalars().all()
            
            # Get device info
            device_cache = {}
            records = []
            for revenue in revenues:
                if revenue.device_id not in device_cache:
                    device_result = await session.execute(
                        select(Device).where(Device.id == revenue.device_id)
                    )
                    device = device_result.scalar_one_or_none()
                    device_cache[revenue.device_id] = device
                
                device = device_cache[revenue.device_id]
                records.append({
                    "id": revenue.id,
                    "device_id": revenue.device_id,
                    "device_code": device.device_code if device else "Unknown",
                    "year": revenue.year,
                    "month": revenue.month,
                    "month_start_date": revenue.month_start_date.isoformat(),
                    "month_end_date": revenue.month_end_date.isoformat() if revenue.month_end_date else None,
                    "closing_counter_19l": revenue.closing_counter_19l,
                    "closing_counter_5l": revenue.closing_counter_5l,
                    "total_revenue": revenue.total_revenue,
                    "is_closed": revenue.is_closed,
                    "created_at": revenue.created_at.isoformat(),
                    "updated_at": revenue.updated_at.isoformat()
                })
            
            return {
                "table_name": "monthly_revenue_records",
                "total_count": len(records),
                "records": records,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error browsing monthly revenue: {e}")
        raise
