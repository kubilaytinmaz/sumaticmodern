"""
Sumatic Modern IoT - Device Chart Data Endpoint
Serves aggregated readings for device detail charts.
Uses sumatic_modern.db (SQLAlchemy ORM) instead of doludb.db.

YENİ MANTIK:
- Süre (slots): 7, 14, 30 mum
- Periyot (period): 10min, hourly, daily, weekly, monthly
- Metrik: counter_19l, counter_5l, total, delta (sadece artı��)
"""
from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from app.database import get_db
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.device_status import DeviceHourlyStatus
from app.config import get_settings

router = APIRouter(prefix="/charts", tags=["Charts"])
settings = get_settings()


def _get_device_online_status(last_seen_at: Optional[datetime]) -> bool:
    """
    Helper function to determine if a device is online based on last_seen_at.
    Uses consistent threshold from config and proper UTC timezone handling.
    """
    if not last_seen_at:
        return False
    
    now_utc = datetime.now(timezone.utc)
    
    if hasattr(last_seen_at, 'tzinfo') and last_seen_at.tzinfo is not None:
        if last_seen_at.tzinfo != timezone.utc:
            last_seen_utc = last_seen_at.astimezone(timezone.utc)
        else:
            last_seen_utc = last_seen_at
    else:
        last_seen_utc = last_seen_at.replace(tzinfo=timezone.utc)
    
    age_seconds = (now_utc - last_seen_utc).total_seconds()
    return age_seconds < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS


async def _get_latest_device_value(db: AsyncSession, device_id: int) -> Dict[str, Any]:
    """
    Bir cihaz için son pozitif (>0) counter değerlerini al.
    
    Mantık:
    1. Her sayaç için ayrı ayrı son pozitif (>0) değeri bul
    2. counter_19l için son pozitif değeri al
    3. counter_5l için son pozitif değeri al
    4. Hiç veri yoksa {counter_19l: 0, counter_5l: 0} döndür
    
    Not: 0 değeri NULL gibi davranır - cihaz kapalıyken gelen 0 değerlerini
    geçip son gerçek sayaç değerini bulur.
    
    Args:
        db: AsyncSession
        device_id: Cihaz ID
        
    Returns:
        {
            "counter_19l": float,
            "counter_5l": float,
            "timestamp": datetime or None
        }
    """
    # counter_19l için son pozitif (>0) değeri al
    result_19l = await db.execute(
        select(DeviceReading)
        .where(DeviceReading.device_id == device_id)
        .where(DeviceReading.counter_19l > 0)
        .order_by(DeviceReading.timestamp.desc())
        .limit(1)
    )
    reading_19l = result_19l.scalar_one_or_none()
    
    # counter_5l için son pozitif (>0) değeri al
    result_5l = await db.execute(
        select(DeviceReading)
        .where(DeviceReading.device_id == device_id)
        .where(DeviceReading.counter_5l > 0)
        .order_by(DeviceReading.timestamp.desc())
        .limit(1)
    )
    reading_5l = result_5l.scalar_one_or_none()
    
    # Her iki sayaç için de değerleri al
    counter_19l = reading_19l.counter_19l if reading_19l else 0
    counter_5l = reading_5l.counter_5l if reading_5l else 0
    
    # Timestamp: en son okunan değerin timestamp'ini kullan
    # Her iki okuma varsa daha yeni olanı seç
    timestamp = None
    if reading_19l and reading_5l:
        timestamp = max(reading_19l.timestamp, reading_5l.timestamp)
    elif reading_19l:
        timestamp = reading_19l.timestamp
    elif reading_5l:
        timestamp = reading_5l.timestamp
    
    return {
        "counter_19l": counter_19l,
        "counter_5l": counter_5l,
        "timestamp": timestamp
    }


async def _fill_null_with_last_value(readings):
    """
    Fill null counter values with the last known non-null value.
    This function processes readings in chronological order and carries forward
    the last known value when encountering null values.
    """
    if not readings:
        return readings
    
    # Convert to list if it's a ScalarResult
    readings_list = list(readings) if hasattr(readings, '__iter__') else readings
    
    last_c19 = None
    last_c5 = None
    
    for reading in readings_list:
        # For counter_19l
        if reading.counter_19l is not None and reading.counter_19l > 0:
            last_c19 = reading.counter_19l
        elif reading.counter_19l is None or reading.counter_19l == 0:
            # Use last known value (carry-forward)
            if last_c19 is not None:
                reading.counter_19l = last_c19
        
        # For counter_5l
        if reading.counter_5l is not None and reading.counter_5l > 0:
            last_c5 = reading.counter_5l
        elif reading.counter_5l is None or reading.counter_5l == 0:
            # Use last known value (carry-forward)
            if last_c5 is not None:
                reading.counter_5l = last_c5
    
    return readings_list


class ChartDataPoint(BaseModel):
    timestamp: str
    label: str
    total_value: float
    delta: float
    delta_19l: float = 0
    delta_5l: float = 0
    total_value_19l: float = 0
    total_value_5l: float = 0
    is_offline: bool = False
    offline_hours: float = 0.0
    online_status: str = "online"


class ChartResponse(BaseModel):
    device_id: int
    device_name: str
    period: str
    slots: int
    data: List[ChartDataPoint]
    summary: Dict[str, Any]
    monthly_revenue: Optional[float] = None  # Son 1 ayın cirosu (toplam)
    monthly_revenue_19l: Optional[float] = None  # Sayaç 1 (19L) cirosu
    monthly_revenue_5l: Optional[float] = None  # Sayaç 2 (5L) cirosu


class MonthlyRevenueResponse(BaseModel):
    device_id: int
    device_name: str
    monthly_revenue: float
    monthly_delta: float


def format_label(ts_str: str, period: str) -> str:
    """Format timestamp to display label based on period (Turkish format)."""
    try:
        dt = datetime.fromisoformat(ts_str.replace(" ", "T"))
        if period == "daily":
            return dt.strftime("%d.%m.%Y")
        elif period == "hourly":
            return dt.strftime("%d.%m %H:%M")
        elif period == "10min":
            return dt.strftime("%d.%m %H:%M")
        elif period == "weekly":
            return dt.strftime("%d.%m.%Y")
        elif period == "monthly":
            return dt.strftime("%m.%Y")
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return ts_str


def get_period_start_time(period: str, slots: int, period_offset: int = 0) -> datetime:
    """Calculate start time based on period, slots and period offset."""
    end_time = datetime.now()
    
    # Apply period offset (0 = current period, -1 = previous period, etc.)
    if period == "daily":
        end_time = end_time - timedelta(days=abs(period_offset))
    elif period == "hourly":
        end_time = end_time - timedelta(hours=abs(period_offset))
    elif period == "10min":
        end_time = end_time - timedelta(minutes=abs(period_offset) * 10)
    elif period == "weekly":
        end_time = end_time - timedelta(weeks=abs(period_offset))
    elif period == "monthly":
        end_time = end_time - timedelta(days=abs(period_offset) * 30)
    
    # Calculate start time based on slots
    if period == "daily":
        return end_time - timedelta(days=slots)
    elif period == "hourly":
        return end_time - timedelta(hours=slots)
    elif period == "10min":
        return end_time - timedelta(minutes=slots * 10)
    elif period == "weekly":
        return end_time - timedelta(weeks=slots)
    elif period == "monthly":
        return end_time - timedelta(days=slots * 30)
    else:
        return end_time - timedelta(days=slots)


def get_period_key(timestamp: datetime, period: str) -> str:
    """Get period key for grouping."""
    if period == "daily":
        return timestamp.strftime("%Y-%m-%d 00:00:00")
    elif period == "hourly":
        return timestamp.strftime("%Y-%m-%d %H:00:00")
    elif period == "10min":
        minute = (timestamp.minute // 10) * 10
        return timestamp.strftime(f"%Y-%m-%d %H:{minute:02d}:00")
    elif period == "weekly":
        days_since_monday = timestamp.weekday()
        monday = timestamp - timedelta(days=days_since_monday)
        return monday.strftime("%Y-%m-%d 00:00:00")
    elif period == "monthly":
        return timestamp.strftime("%Y-%m-01 00:00:00")
    else:
        return timestamp.strftime("%Y-%m-%d 00:00:00")


def get_period_duration_hours(period: str) -> float:
    """Get period duration in hours for offline calculation."""
    if period == "hourly":
        return 1
    elif period == "10min":
        return 10 / 60
    elif period == "weekly":
        return 24 * 7
    elif period == "monthly":
        return 24 * 30
    else:  # daily
        return 24


def normalize_metric(metric: str) -> str:
    """Normalize metric parameter from frontend to backend format."""
    metric_map = {
        "sayac1": "counter_19l",
        "sayac2": "counter_5l",
        "total": "total",
        "counter_19l": "counter_19l",
        "counter_5l": "counter_5l",
    }
    return metric_map.get(metric, "total")


@router.get("/devices/summary")
async def get_all_devices_summary(db: AsyncSession = Depends(get_db)):
    """
    Get summary for all devices from sumatic_modern.db.
    Returns latest readings for all devices.
    All values are the latest cumulative counter values (counter_19l + counter_5l).
    """
    try:
        result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = result.scalars().all()
        
        result_list = []
        
        for device in devices:
            # Get the most recent valid reading for this device (with fallback)
            latest_data = await _get_latest_device_value(db, device.id)
            counter_19l = latest_data["counter_19l"]
            counter_5l = latest_data["counter_5l"]
            last_reading_at = latest_data["timestamp"].isoformat() if latest_data["timestamp"] else None
            
            total = counter_19l + counter_5l
            is_online = _get_device_online_status(device.last_seen_at)
            
            # current_value and monthly_revenue are now the cumulative total (latest counter values)
            current_value = total
            monthly_revenue = total
            
            result_list.append({
                "id": device.id,
                "device_code": device.device_code,
                "name": device.name or f"Device {device.device_code}",
                "modem_id": device.modem_id,
                "device_addr": device.device_addr,
                "last_reading_at": last_reading_at,
                "counter_19l": counter_19l,
                "counter_5l": counter_5l,
                "total": total,
                "fault_status": 0,
                "is_online": is_online,
                "current_value": float(current_value),
                "monthly_revenue": float(monthly_revenue),
            })
        
        return {"devices": result_list, "count": len(result_list)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching device summary: {str(e)}")


@router.get("/devices/per-device-summary")
async def get_per_device_summary(
    period: str = Query("daily", description="Period: 10min, hourly, daily, weekly, monthly"),
    slots: int = Query(30, ge=5, le=100, description="Number of slots to return"),
    metric: str = Query("total", description="Metric: counter_19l, counter_5l, total"),
    db: AsyncSession = Depends(get_db),
):
    # Normalize metric parameter
    metric = normalize_metric(metric)
    """
    Get per-device summary for the latest period.
    Returns current value, last delta, and offline info for each device.
    """
    try:
        result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = result.scalars().all()
        
        start_time = get_period_start_time(period, slots)
        # +1 saat buffer: güncel verilerin kesinlikle dahil edilmesi için
        end_time = datetime.now() + timedelta(hours=1)
        
        result_list = []
        
        for device in devices:
            readings_result = await db.execute(
                select(DeviceReading)
                .where(
                    (DeviceReading.device_id == device.id) &
                    (DeviceReading.timestamp >= start_time) &
                    (DeviceReading.timestamp <= end_time)
                )
                .order_by(DeviceReading.timestamp.asc())
            )
            readings = readings_result.scalars().all()
            
            if readings:
                latest = readings[-1]
                
                if metric == "counter_19l":
                    current_value = latest.counter_19l or 0
                elif metric == "counter_5l":
                    current_value = latest.counter_5l or 0
                else:
                    current_value = (latest.counter_19l or 0) + (latest.counter_5l or 0)
                
                if len(readings) > 1:
                    prev = readings[-2]
                    if metric == "counter_19l":
                        prev_value = prev.counter_19l or 0
                    elif metric == "counter_5l":
                        prev_value = prev.counter_5l or 0
                    else:
                        prev_value = (prev.counter_19l or 0) + (prev.counter_5l or 0)
                    
                    last_delta = max(0, current_value - prev_value)
                else:
                    last_delta = 0
                
                deltas = []
                for i in range(1, len(readings)):
                    if metric == "counter_19l":
                        curr_val = readings[i].counter_19l or 0
                        prev_val = readings[i-1].counter_19l or 0
                    elif metric == "counter_5l":
                        curr_val = readings[i].counter_5l or 0
                        prev_val = readings[i-1].counter_5l or 0
                    else:
                        curr_val = (readings[i].counter_19l or 0) + (readings[i].counter_5l or 0)
                        prev_val = (readings[i-1].counter_19l or 0) + (readings[i-1].counter_5l or 0)
                    
                    delta = max(0, curr_val - prev_val)
                    if delta > 0:
                        deltas.append(delta)
                
                total_delta = sum(deltas)
                avg_delta = sum(deltas) / len(deltas) if deltas else 0
                
                if device.last_seen_at is None:
                    online_status = "no_data"
                elif _get_device_online_status(device.last_seen_at):
                    online_status = "online"
                else:
                    online_status = "offline"
                offline_hours = 0.0
                
                last_reading_at = latest.timestamp.isoformat() if latest.timestamp else None
            else:
                # Veri yoksa, son çekilmiş NULL olmayan değerleri kullan (fallback)
                latest_data = await _get_latest_device_value(db, device.id)
                counter_19l = latest_data["counter_19l"]
                counter_5l = latest_data["counter_5l"]
                
                if metric == "counter_19l":
                    current_value = counter_19l
                elif metric == "counter_5l":
                    current_value = counter_5l
                else:
                    current_value = counter_19l + counter_5l
                
                last_delta = 0
                total_delta = 0
                avg_delta = 0
                offline_hours = 0.0
                online_status = "no_data"
                last_reading_at = latest_data["timestamp"].isoformat() if latest_data["timestamp"] else None
            
            result_list.append({
                "id": device.id,
                "device_code": device.device_code,
                "device_name": device.name or f"Device {device.device_code}",
                "modem_id": device.modem_id,
                "device_addr": device.device_addr,
                "current_value": current_value,
                "last_delta": last_delta,
                "total_delta": total_delta,
                "avg_delta": round(avg_delta, 2),
                "offline_hours": offline_hours,
                "online_status": online_status,
                "is_online": online_status in ["online", "partial"],
                "last_reading_at": last_reading_at,
            })
        
        return {
            "devices": result_list,
            "count": len(result_list),
            "period": period,
            "slots": slots,
            "metric": metric,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching per-device summary: {str(e)}")


@router.get("/devices/all-chart-data")
async def get_all_devices_chart_data(
    period: str = Query("daily", description="Period: 10min, hourly, daily, weekly, monthly"),
    slots: int = Query(30, ge=5, le=100, description="Number of slots to return"),
    metric: str = Query("total", description="Metric: counter_19l, counter_5l, total"),
    period_offset: int = Query(0, ge=-12, le=0, description="Period offset: 0=current, -1=previous, -2=2 periods ago, etc."),
    anchor_date: Optional[str] = Query(None, description="Anchor date for drill-down (ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS). When provided, slots are centered around this date."),
    db: AsyncSession = Depends(get_db),
):
    # Normalize metric parameter
    metric = normalize_metric(metric)
    """
    Get aggregated chart data for ALL devices combined.
    Supports drill-down via anchor_date parameter.
    """
    try:
        devices_result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = devices_result.scalars().all()
        
        if not devices:
            return {
                "device_id": 0,
                "device_name": "Tüm Cihazlar",
                "period": period,
                "slots": slots,
                "period_offset": period_offset,
                "data": [],
                "summary": {"current_value": 0, "min_delta": 0, "max_delta": 0, "avg_delta": 0, "total_delta": 0},
                "monthly_revenue": 0,
                "last_period_delta": 0,
                "total_period_revenue": 0,
                "avg_revenue": 0,
                "active_device_count": 0,
                "offline_hours": 0,
                "total_device_count": 0,
            }
        
        # If anchor_date is provided, build a time window around it
        if anchor_date:
            try:
                anchor_dt = datetime.fromisoformat(anchor_date.replace("T", " ").replace("Z", ""))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid anchor_date format: {anchor_date}. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
            
            # Build start_time and end_time around anchor based on period
            if period == "daily":
                # anchor is a day; center window = slots days ending at anchor + 1 day
                end_time = anchor_dt.replace(hour=23, minute=59, second=59)
                start_time = end_time - timedelta(days=slots - 1)
                start_time = start_time.replace(hour=0, minute=0, second=0)
            elif period == "hourly":
                # anchor is an hour; window = slots hours ending at anchor end
                end_time = anchor_dt.replace(minute=59, second=59)
                start_time = end_time - timedelta(hours=slots - 1)
                start_time = start_time.replace(minute=0, second=0)
            elif period == "10min":
                # anchor is 10-min slot
                minute_block = (anchor_dt.minute // 10) * 10
                end_time = anchor_dt.replace(minute=minute_block + 9 if minute_block + 9 < 60 else 59, second=59)
                start_time = end_time - timedelta(minutes=(slots - 1) * 10)
                start_time = start_time.replace(second=0)
            elif period == "weekly":
                end_time = anchor_dt + timedelta(days=6 - anchor_dt.weekday())
                end_time = end_time.replace(hour=23, minute=59, second=59)
                start_time = end_time - timedelta(weeks=slots - 1)
                start_time = start_time.replace(hour=0, minute=0, second=0)
            elif period == "monthly":
                end_time = anchor_dt.replace(day=1, hour=0, minute=0, second=0) + timedelta(days=32)
                end_time = end_time.replace(day=1) - timedelta(seconds=1)
                start_time = (anchor_dt.replace(day=1) - timedelta(days=(slots - 1) * 30)).replace(day=1, hour=0, minute=0, second=0)
            else:
                end_time = anchor_dt
                start_time = end_time - timedelta(days=slots)
        else:
            start_time = get_period_start_time(period, slots, period_offset)
            # +1 saat buffer: güncel verilerin kesinlikle dahil edilmesi için
            end_time = datetime.now() + timedelta(hours=1)
            
            # Calculate end time with period offset applied
            if period_offset != 0:
                end_time = get_period_start_time(period, abs(period_offset), 0)
        
        device_period_data: Dict[int, Dict[str, Dict[str, Any]]] = {}
        
        for device in devices:
            device_period_data[device.id] = {}
            
            readings_result = await db.execute(
                select(DeviceReading)
                .where(
                    (DeviceReading.device_id == device.id) &
                    (DeviceReading.timestamp >= start_time) &
                    (DeviceReading.timestamp <= end_time)
                )
                .order_by(DeviceReading.timestamp.asc())
            )
            readings = readings_result.scalars().all()
            
            for reading in readings:
                if not reading.timestamp:
                    continue
                
                period_key = get_period_key(reading.timestamp, period)
                
                if period_key not in device_period_data[device.id]:
                    device_period_data[device.id][period_key] = {
                        "counter_19l_values": [],
                        "counter_5l_values": [],
                    }
                
                c19 = reading.counter_19l
                c5 = reading.counter_5l
                
                if c19 is not None:
                    device_period_data[device.id][period_key]["counter_19l_values"].append(c19)
                if c5 is not None:
                    device_period_data[device.id][period_key]["counter_5l_values"].append(c5)
        
        all_periods = set()
        for device_data in device_period_data.values():
            all_periods.update(device_data.keys())
        
        if not all_periods:
            return {
                "device_id": 0,
                "device_name": "Tüm Cihazlar",
                "period": period,
                "slots": slots,
                "data": [],
                "summary": {"current_value": 0, "min_delta": 0, "max_delta": 0, "avg_delta": 0, "total_delta": 0},
                "monthly_revenue": 0
            }
        
        device_last_values: Dict[int, Dict[str, float]] = {}
        for device in devices:
            # Get the last known value BEFORE start_time for proper carry-forward initialization
            # This ensures that if a device has no data in the time window, we still use its
            # last known cumulative counter value instead of starting from 0
            pre_start_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp < start_time)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            pre_start_reading = pre_start_result.scalar_one_or_none()
            
            if pre_start_reading:
                device_last_values[device.id] = {
                    "counter_19l": pre_start_reading.counter_19l or 0,
                    "counter_5l": pre_start_reading.counter_5l or 0,
                }
            else:
                # No data before start_time, start from 0
                device_last_values[device.id] = {"counter_19l": 0, "counter_5l": 0}
        
        period_totals: Dict[str, float] = {}
        period_totals_19l: Dict[str, float] = {}
        period_totals_5l: Dict[str, float] = {}
        
        for period_key in sorted(all_periods):
            total_19l = 0
            total_5l = 0
            
            for device_id in device_period_data.keys():
                device_data = device_period_data[device_id]
                
                # Carry-forward: Use the last known value for devices without data in this period
                # This ensures the cumulative total is accurate even when some devices are offline
                if period_key in device_data:
                    c19_vals = device_data[period_key]["counter_19l_values"]
                    c5_vals = device_data[period_key]["counter_5l_values"]
                    
                    # Use LAST value (most recent reading) for the period
                    # Counters are cumulative, so the last reading represents the current state
                    # Only use carry-forward if there's NO new data (values list is empty)
                    if c19_vals:
                        # New data available - use LAST value from this period
                        period_c19 = c19_vals[-1]
                    else:
                        # No new data - use last known value (carry-forward)
                        period_c19 = device_last_values[device_id]["counter_19l"]
                    
                    if c5_vals:
                        # New data available - use LAST value from this period
                        period_c5 = c5_vals[-1]
                    else:
                        # No new data - use last known value (carry-forward)
                        period_c5 = device_last_values[device_id]["counter_5l"]
                    
                    # Update last known values for this device
                    device_last_values[device_id]["counter_19l"] = period_c19
                    device_last_values[device_id]["counter_5l"] = period_c5
                else:
                    # Device has no data in this period, use last known value (carry-forward)
                    period_c19 = device_last_values[device_id]["counter_19l"]
                    period_c5 = device_last_values[device_id]["counter_5l"]
                
                total_19l += period_c19
                total_5l += period_c5
            
            period_totals_19l[period_key] = total_19l
            period_totals_5l[period_key] = total_5l
            
            if metric == "counter_19l":
                period_totals[period_key] = total_19l
            elif metric == "counter_5l":
                period_totals[period_key] = total_5l
            else:
                period_totals[period_key] = total_19l + total_5l
        
        sorted_periods = sorted(period_totals.keys(), reverse=True)[:slots]
        sorted_periods.reverse()
        
        current_total_19l = 0
        current_total_5l = 0
        device_current_values: Dict[int, Dict[str, float]] = {}
        
        for device in devices:
            # Get the most recent valid reading for this device
            # Use the same query as /devices/summary for consistency
            latest_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            latest_reading = latest_result.scalar_one_or_none()
            
            # If no valid reading found, try to get any reading
            if not latest_reading:
                fallback_result = await db.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .order_by(DeviceReading.timestamp.desc())
                    .limit(1)
                )
                latest_reading = fallback_result.scalar_one_or_none()
            
            if latest_reading:
                c19 = latest_reading.counter_19l or 0
                c5 = latest_reading.counter_5l or 0
                current_total_19l += c19
                current_total_5l += c5
                device_current_values[device.id] = {"counter_19l": c19, "counter_5l": c5}
            else:
                device_current_values[device.id] = {"counter_19l": 0, "counter_5l": 0}
        
        if metric == "counter_19l":
            current_total = current_total_19l
        elif metric == "counter_5l":
            current_total = current_total_5l
        else:
            current_total = current_total_19l + current_total_5l
        
        data_points = []
        deltas = []
        
        period_duration_hours = get_period_duration_hours(period)
        
        for i, period_key in enumerate(sorted_periods):
            # Calculate period-over-period difference (actual revenue for this period)
            # Counters are cumulative, so we need the difference between periods
            if i > 0:
                prev_value_19l = period_totals_19l[sorted_periods[i - 1]]
                prev_value_5l = period_totals_5l[sorted_periods[i - 1]]
                value_19l = period_totals_19l[period_key]
                value_5l = period_totals_5l[period_key]
                # Calculate delta for each counter type separately, then sum
                delta_19l = max(0, value_19l - prev_value_19l)
                delta_5l = max(0, value_5l - prev_value_5l)
                delta = delta_19l + delta_5l
            else:
                # First period - no previous period to compare
                delta_19l = 0
                delta_5l = 0
                delta = 0
                value_19l = period_totals_19l[period_key]
                value_5l = period_totals_5l[period_key]
            
            deltas.append(delta)
            
            offline_device_count = 0
            total_offline_hours = 0.0
            
            for device in devices:
                device_was_online = False
                
                if device.id in device_period_data and period_key in device_period_data[device.id]:
                    device_was_online = True
                else:
                    if device.last_seen_at:
                        try:
                            period_start = datetime.strptime(period_key, "%Y-%m-%d %H:%M:%S")
                            period_end = period_start + timedelta(hours=period_duration_hours)
                            
                            if device.last_seen_at < period_start:
                                offline_device_count += 1
                                total_offline_hours += period_duration_hours
                            elif device.last_seen_at > period_end:
                                offline_device_count += 1
                                total_offline_hours += period_duration_hours
                        except:
                            pass
                    else:
                        offline_device_count += 1
                        total_offline_hours += period_duration_hours
            
            avg_offline_hours = total_offline_hours / len(devices) if devices else 0.0
            
            offline_ratio = offline_device_count / len(devices) if devices else 0
            
            if offline_ratio >= 0.5:
                online_status = "offline"
            elif offline_ratio >= 0.1:
                online_status = "partial"
            else:
                online_status = "online"
            
            data_points.append({
                "timestamp": period_key,
                "label": format_label(period_key, period),
                "total_value": period_totals[period_key],  # Cumulative total of all devices for this period
                "delta": delta,
                "delta_19l": delta_19l,
                "delta_5l": delta_5l,
                "total_value_19l": period_totals_19l[period_key],  # Cumulative 19L value for this period
                "total_value_5l": period_totals_5l[period_key],  # Cumulative 5L value for this period
                "is_offline": offline_ratio > 0,
                "offline_hours": round(avg_offline_hours, 1),
                "online_status": online_status,
            })
        
        non_zero_deltas = [d for d in deltas if d > 0]
        summary = {
            "current_value": current_total,
            "min_delta": min(non_zero_deltas) if non_zero_deltas else 0,
            "max_delta": max(non_zero_deltas) if non_zero_deltas else 0,
            "avg_delta": round(sum(non_zero_deltas) / len(non_zero_deltas), 2) if non_zero_deltas else 0,
            "total_delta": sum(non_zero_deltas),
        }
        
        # Calculate monthly revenue from the selected period window
        # Get the last counter values within the selected time window (start_time to end_time)
        monthly_revenue_19l = 0
        monthly_revenue_5l = 0
        
        for device in devices:
            # Get the most recent reading for this device within the selected period window
            latest_in_period_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp >= start_time)
                .where(DeviceReading.timestamp <= end_time)
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            latest_in_period = latest_in_period_result.scalar_one_or_none()
            
            # Add the latest counter values within the period to the totals
            if latest_in_period:
                if latest_in_period.counter_19l is not None:
                    monthly_revenue_19l += latest_in_period.counter_19l
                if latest_in_period.counter_5l is not None:
                    monthly_revenue_5l += latest_in_period.counter_5l
        
        # Monthly revenue is the sum of latest counter values
        monthly_total = monthly_revenue_19l + monthly_revenue_5l
        monthly_total_19l = monthly_revenue_19l
        monthly_total_5l = monthly_revenue_5l
        
        # --- New aggregated metrics for the selected period/offset window ---
        total_device_count = len(devices)
        
        # total_period_revenue: sum of all positive deltas in this window (actual revenue)
        total_period_revenue = sum(non_zero_deltas)
        
        # avg_revenue: average of non-zero deltas
        avg_revenue = round(sum(non_zero_deltas) / len(non_zero_deltas), 2) if non_zero_deltas else 0
        
        # last_period_delta: delta value of the most recent slot
        last_period_delta = deltas[-1] if deltas else 0
        
        # today_vs_yesterday_delta: difference between last two slots (today - yesterday)
        today_vs_yesterday_delta = 0
        if len(deltas) >= 2:
            today_vs_yesterday_delta = deltas[-1] - deltas[-2]
        
        # monthly_revenue should be the sum of latest counter values from all devices
        # This represents the cumulative total of all devices' latest readings
        monthly_total = monthly_revenue_19l + monthly_revenue_5l
        monthly_total_19l = monthly_revenue_19l
        monthly_total_5l = monthly_revenue_5l
        
        # active_device_count: devices that had at least one reading in the window
        active_device_ids = set()
        for device_id_key, pdata in device_period_data.items():
            if pdata:  # has at least one period with data
                active_device_ids.add(device_id_key)
        active_device_count = len(active_device_ids)
        
        # offline_hours: total offline hours across all devices in the most recent slot
        total_offline_hours_period = 0.0
        if sorted_periods:
            last_period_key = sorted_periods[-1]
            for device in devices:
                device_was_online = (
                    device.id in device_period_data
                    and last_period_key in device_period_data[device.id]
                )
                if not device_was_online:
                    total_offline_hours_period += period_duration_hours
        
        return {
            "device_id": 0,
            "device_name": "Tüm Cihazlar",
            "period": period,
            "slots": slots,
            "period_offset": period_offset,
            "data": data_points,
            "summary": summary,
            "monthly_revenue": current_total,  # Sum of all devices' latest cumulative counter values (all-time)
            "monthly_revenue_19l": current_total_19l,
            "monthly_revenue_5l": current_total_5l,
            "last_period_delta": last_period_delta,
            "today_vs_yesterday_delta": today_vs_yesterday_delta,
            "total_period_revenue": total_period_revenue,
            "avg_revenue": avg_revenue,
            "active_device_count": active_device_count,
            "offline_hours": round(total_offline_hours_period, 1),
            "total_device_count": total_device_count,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")


@router.get("/device/{device_id}/monthly-revenue", response_model=MonthlyRevenueResponse)
async def get_device_monthly_revenue(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get device's latest cumulative counter value (counter_19l + counter_5l).
    """
    try:
        device_result = await db.execute(select(Device).where(Device.id == device_id))
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Get latest reading with fallback (son NULL olmayan değeri al)
        latest_data = await _get_latest_device_value(db, device_id)
        counter_19l = latest_data["counter_19l"]
        counter_5l = latest_data["counter_5l"]
        total = counter_19l + counter_5l
        
        # Return the latest cumulative value
        return MonthlyRevenueResponse(
            device_id=device_id,
            device_name=device.name or f"Device {device.device_code}",
            monthly_revenue=total,
            monthly_delta=total
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching monthly revenue: {str(e)}")


@router.get("/device/{device_id}", response_model=ChartResponse)
async def get_device_chart_data(
    device_id: int,
    period: str = Query("daily", description="Period: 10min, hourly, daily, weekly, monthly"),
    slots: int = Query(30, ge=5, le=100, description="Number of slots to return"),
    metric: str = Query("total", description="Metric: counter_19l, counter_5l, total"),
    fill_nulls: bool = Query(True, description="Fill null counter values with last known value (API layer only)"),
    db: AsyncSession = Depends(get_db),
):
    # Normalize metric parameter
    metric = normalize_metric(metric)
    """
    Get aggregated chart data for a device from sumatic_modern.db.
    """
    try:
        device_result = await db.execute(select(Device).where(Device.id == device_id))
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        start_time = get_period_start_time(period, slots)
        # +1 saat buffer: güncel verilerin kesinlikle dahil edilmesi için
        end_time = datetime.now() + timedelta(hours=1)
        
        # Get the last known value BEFORE start_time for proper carry-forward initialization
        # Helper fonksiyonu kullan: son NULL olmayan değeri al
        pre_start_result = await db.execute(
            select(DeviceReading)
            .where(DeviceReading.device_id == device_id)
            .where(DeviceReading.timestamp < start_time)
            .order_by(DeviceReading.timestamp.desc())
            .limit(1)
        )
        pre_start_reading = pre_start_result.scalar_one_or_none()
        
        # Initialize with the last known value BEFORE the time window
        # This ensures we start with the correct cumulative value
        if pre_start_reading:
            last_c19 = pre_start_reading.counter_19l or 0
            last_c5 = pre_start_reading.counter_5l or 0
        else:
            # No data before start_time, try to get ANY last reading (fallback)
            latest_data = await _get_latest_device_value(db, device_id)
            last_c19 = latest_data["counter_19l"]
            last_c5 = latest_data["counter_5l"]
        
        # Initialize prev_total with the starting cumulative value
        prev_total = last_c19 + last_c5
        
        readings_result = await db.execute(
            select(DeviceReading)
            .where(
                (DeviceReading.device_id == device_id) &
                (DeviceReading.timestamp >= start_time) &
                (DeviceReading.timestamp <= end_time)
            )
            .order_by(DeviceReading.timestamp.asc())
        )
        readings = readings_result.scalars().all()
        
        # Apply null filling if requested
        if fill_nulls and readings:
            readings = await _fill_null_with_last_value(readings)
        
        period_data: Dict[str, Dict[str, Any]] = {}
        
        for reading in readings:
            if not reading.timestamp:
                continue
            
            period_key = get_period_key(reading.timestamp, period)
            
            if period_key not in period_data:
                period_data[period_key] = {
                    "counter_19l_values": [],
                    "counter_5l_values": [],
                    "faults": 0,
                }
            
            c19 = reading.counter_19l
            c5 = reading.counter_5l
            
            if c19 is not None:
                period_data[period_key]["counter_19l_values"].append(c19)
            if c5 is not None:
                period_data[period_key]["counter_5l_values"].append(c5)
        
        sorted_periods = sorted(period_data.keys())
        
        if sorted_periods and period == "daily":
            first_period = sorted_periods[0]
            last_period = sorted_periods[-1]
            
            first_date = datetime.strptime(first_period, "%Y-%m-%d %H:%M:%S")
            last_date = datetime.strptime(last_period, "%Y-%m-%d %H:%M:%S")
            
            current = first_date
            while current <= last_date:
                period_key = current.strftime("%Y-%m-%d 00:00:00")
                if period_key not in period_data:
                    period_data[period_key] = {
                        "counter_19l_values": [],
                        "counter_5l_values": [],
                        "faults": 0,
                    }
                current += timedelta(days=1)
            
            sorted_periods = sorted(period_data.keys())
        
        data_points = []
        deltas = []
        
        # Don't reset last_c19 and last_c5 - they already have the correct initial values
        # prev_total is also already initialized above
        # Also track previous values for separate 19L and 5L deltas
        prev_c19 = last_c19
        prev_c5 = last_c5
        
        # Store the final period_c19 and period_c5 values for monthly revenue calculation
        final_period_c19 = 0
        final_period_c5 = 0
        
        for i, period_key in enumerate(sorted_periods):
            data = period_data[period_key]
            
            c19_values = data["counter_19l_values"]
            c5_values = data["counter_5l_values"]
            
            # Use LAST value (most recent reading) for the period
            # Counters are cumulative, so the last reading represents the current state
            # Only use carry-forward if there's NO new data (values list is empty)
            if c19_values:
                # New data available - use LAST value from this period
                period_c19 = c19_values[-1]
            else:
                # No new data - use last known value (carry-forward)
                period_c19 = last_c19
            
            if c5_values:
                # New data available - use LAST value from this period
                period_c5 = c5_values[-1]
            else:
                # No new data - use last known value (carry-forward)
                period_c5 = last_c5
            
            # Update last_c19 and last_c5 for next iteration
            last_c19 = period_c19
            last_c5 = period_c5
            
            # Store the final period values for monthly revenue calculation
            if i == len(sorted_periods) - 1:
                final_period_c19 = period_c19
                final_period_c5 = period_c5
            
            if metric == "counter_19l":
                max_value = period_c19
            elif metric == "counter_5l":
                max_value = period_c5
            else:
                max_value = period_c19 + period_c5
            
            # Calculate delta: difference between current cumulative value and previous cumulative value
            # This represents the actual revenue for this period
            delta = max(0, max_value - prev_total) if i > 0 else 0
            
            # Calculate separate deltas for 19L and 5L
            delta_19l = max(0, period_c19 - prev_c19) if i > 0 else 0
            delta_5l = max(0, period_c5 - prev_c5) if i > 0 else 0
            
            # Update prev_total and prev_c19/prev_c5 for next iteration
            prev_total = max_value
            prev_c19 = period_c19
            prev_c5 = period_c5
            
            deltas.append(delta)
            
            data_points.append(ChartDataPoint(
                timestamp=period_key,
                label=format_label(period_key, period),
                total_value=max_value,
                delta=delta,
                delta_19l=delta_19l,
                delta_5l=delta_5l,
                total_value_19l=period_c19,
                total_value_5l=period_c5,
                is_offline=(data["faults"] > 0),
            ))
        
        non_zero_deltas = [d for d in deltas if d > 0]
        
        # Get the most recent valid reading for cumulative value (latest counter values)
        # This is the cumulative total, not a monthly delta
        latest_result = await db.execute(
            select(DeviceReading)
            .where(DeviceReading.device_id == device_id)
            .where(DeviceReading.counter_19l.isnot(None))
            .where(DeviceReading.counter_5l.isnot(None))
            .order_by(DeviceReading.timestamp.desc())
            .limit(1)
        )
        latest_reading = latest_result.scalar_one_or_none()
        
        # If no valid reading found, try to get any reading
        if not latest_reading:
            fallback_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device_id)
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            latest_reading = fallback_result.scalar_one_or_none()
        
        # current_value and monthly_revenue are now the cumulative total (latest counter values)
        current_value = 0
        monthly_revenue_19l = 0
        monthly_revenue_5l = 0
        
        if latest_reading:
            c19 = latest_reading.counter_19l or 0
            c5 = latest_reading.counter_5l or 0
            current_value = c19 + c5
            monthly_revenue_19l = c19
            monthly_revenue_5l = c5
        
        monthly_revenue = current_value
        
        summary = {
            "current_value": current_value,
            "min_delta": min(non_zero_deltas) if non_zero_deltas else 0,
            "max_delta": max(non_zero_deltas) if non_zero_deltas else 0,
            "avg_delta": round(sum(non_zero_deltas) / len(non_zero_deltas), 2) if non_zero_deltas else 0,
            "total_delta": sum(non_zero_deltas),
        }
        
        return ChartResponse(
            device_id=device_id,
            device_name=device.name or f"Device {device.device_code}",
            period=period,
            slots=slots,
            data=data_points,
            summary=summary,
            monthly_revenue=monthly_revenue,
            monthly_revenue_19l=monthly_revenue_19l,
            monthly_revenue_5l=monthly_revenue_5l,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching device chart data: {str(e)}")


# New endpoints for monthly dashboard statistics
class DeviceOfflineInfo(BaseModel):
    """Per-device offline hours info."""
    device_id: int
    device_name: str
    offline_hours: float


class MonthlyStatsResponse(BaseModel):
    """Response model for monthly statistics."""
    month: str  # Format: "YYYY-MM"
    month_name: str  # Turkish month name, e.g., "Mart 2026"
    last_day_revenue: float  # Son günün cirosu
    yesterday_revenue: float  # Dünün cirosu
    max_day_revenue: float  # Ayda en fazla ciro yapılan günün cirosu
    max_day_date: str  # En fazla ciro yapılan gün (format: "DD.MM.YYYY")
    avg_daily_revenue: float  # Ortalama günlük kazanç
    total_month_revenue: float  # Ayın toplam cirosu
    daily_offline_hours_yesterday: float  # Dünün offline süresi (saat)
    total_devices: int  # Toplam cihaz sayısı
    active_devices: int  # Aktif cihaz sayısı
    device_offline_hours: List[DeviceOfflineInfo] = []  # Her cihaz için bu ay toplam offline saat


@router.get("/devices/monthly-stats", response_model=MonthlyStatsResponse)
async def get_monthly_stats(
    year: int = Query(..., description="Year (e.g., 2026)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get monthly statistics for all devices.
    
    Returns:
        - Son günün cirosu
        - Ayda en fazla ciro yapılan gün ve cirosu
        - Ortalama günlük kazanç
        - Günlük toplam makine başına offline süresi
    """
    try:
        # Get current local time for offline calculations
        now_local = datetime.now()
        
        # Calculate month start and end
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Turkish month name
        month_names_tr = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_name = f"{month_names_tr[month - 1]} {year}"
        
        # Get all enabled devices
        devices_result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = devices_result.scalars().all()
        
        if not devices:
            return MonthlyStatsResponse(
                month=f"{year}-{month:02d}",
                month_name=month_name,
                last_day_revenue=0,
                yesterday_revenue=0,
                max_day_revenue=0,
                max_day_date="",
                avg_daily_revenue=0,
                total_month_revenue=0,
                daily_offline_hours_yesterday=0,
                total_devices=0,
                active_devices=0,
                device_offline_hours=[],
            )
        
        total_devices = len(devices)
        
        # Get readings for the month
        readings_result = await db.execute(
            select(DeviceReading)
            .where(
                (DeviceReading.timestamp >= month_start) &
                (DeviceReading.timestamp <= month_end)
            )
            .order_by(DeviceReading.timestamp.asc())
        )
        readings = readings_result.scalars().all()
        
        # Group by day and calculate daily deltas
        daily_data: Dict[str, Dict[str, Any]] = {}
        
        # Initialize with last known values before month start
        device_last_values: Dict[int, Dict[str, float]] = {}
        for device in devices:
            pre_month_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp < month_start)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            pre_month_reading = pre_month_result.scalar_one_or_none()
            
            if pre_month_reading:
                device_last_values[device.id] = {
                    "counter_19l": pre_month_reading.counter_19l or 0,
                    "counter_5l": pre_month_reading.counter_5l or 0,
                }
            else:
                device_last_values[device.id] = {"counter_19l": 0, "counter_5l": 0}
        
        # Process readings day by day, per device
        # Structure: daily_data[day_key][device_id] = {counter_19l, counter_5l}
        daily_data: Dict[str, Dict[int, Dict[str, float]]] = {}
        
        for reading in readings:
            if not reading.timestamp:
                continue
            
            # Skip readings with None counter values (carry-forward will use last known value)
            if reading.counter_19l is None or reading.counter_5l is None:
                continue
            
            day_key = reading.timestamp.strftime("%Y-%m-%d")
            
            if day_key not in daily_data:
                daily_data[day_key] = {}
            
            # Store the latest reading for this device on this day
            daily_data[day_key][reading.device_id] = {
                "counter_19l": reading.counter_19l,
                "counter_5l": reading.counter_5l,
            }
        
        # Calculate daily cumulative totals first (like all-chart-data does)
        # Then calculate deltas between consecutive days
        period_totals_19l: Dict[str, float] = {}
        period_totals_5l: Dict[str, float] = {}
        daily_offline_hours: Dict[str, float] = {}
        
        # Get all unique days
        all_days = sorted(daily_data.keys())
        
        # Track previous day's values for carry-forward (like all-chart-data)
        prev_day_values: Dict[int, Dict[str, float]] = device_last_values.copy()
        
        # Calculate daily deltas using per-device approach
        # For each day, calculate delta for each device, then sum them
        for day_key in all_days:
            day_delta_19l = 0
            day_delta_5l = 0
            devices_with_data = set()
            
            # Process each device for this day
            if day_key in daily_data:
                for device_id, values in daily_data[day_key].items():
                    today_19l = values["counter_19l"]
                    today_5l = values["counter_5l"]
                    
                    # Get previous day's values (carry-forward)
                    prev_19l = prev_day_values.get(device_id, {}).get("counter_19l", 0)
                    prev_5l = prev_day_values.get(device_id, {}).get("counter_5l", 0)
                    
                    # Calculate delta for this device (max(0, today - prev))
                    delta_19l = max(0, today_19l - prev_19l)
                    delta_5l = max(0, today_5l - prev_5l)
                    
                    day_delta_19l += delta_19l
                    day_delta_5l += delta_5l
                    devices_with_data.add(device_id)
                    
                    # Update prev_day_values for next iteration
                    prev_day_values[device_id] = {
                        "counter_19l": today_19l,
                        "counter_5l": today_5l,
                    }
            
            period_totals_19l[day_key] = day_delta_19l
            period_totals_5l[day_key] = day_delta_5l
            
            # Calculate offline hours for this day
            devices_without_data = total_devices - len(devices_with_data)
            daily_offline_hours[day_key] = devices_without_data * 24  # 24 hours per day
        
        # period_totals_19l/5l artık günlük delta değerlerini içeriyor
        # (per-device delta hesaplaması sonucu)
        # daily_deltas bu değerlerin toplamı
        daily_deltas: Dict[str, float] = {}
        
        for day_key in all_days:
            # Her gün için 19l ve 5l deltalarını topla
            daily_deltas[day_key] = period_totals_19l[day_key] + period_totals_5l[day_key]
        
        # Calculate total_month_revenue as sum of last non-null values for all devices
        # This is the cumulative total at the end of the month
        total_month_revenue = 0
        
        # Get the last reading for each device in the month
        for device in devices:
            last_reading_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp >= month_start)
                .where(DeviceReading.timestamp < month_end)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            last_reading = last_reading_result.scalar_one_or_none()
            
            if last_reading:
                total_month_revenue += (last_reading.counter_19l or 0) + (last_reading.counter_5l or 0)
        
        # Calculate statistics
        if all_days:
            # Son Günün Cirosu = Son günün delta değeri (dünden bugüne toplam artış)
            last_day_key = all_days[-1]
            last_day_revenue = daily_deltas.get(last_day_key, 0)
            
            # Dünün Cirosu = Gerçek dünün (yesterday) delta değeri
            # Şu anki tarihin bir önceki gününü bul
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            yesterday_key = yesterday.strftime("%Y-%m-%d")
            
            # Eğer dün bu ay içindeyse, dünün cirosunu al
            if yesterday_key in daily_deltas:
                yesterday_revenue = daily_deltas.get(yesterday_key, 0)
                daily_offline_hours_yesterday = daily_offline_hours.get(yesterday_key, 0)
            else:
                # Dün bu ay içinde değilse (ayın ilk günündeysek), son günden bir önceki günü kullan
                if len(all_days) >= 2:
                    yesterday_key = all_days[-2]
                    yesterday_revenue = daily_deltas.get(yesterday_key, 0)
                    daily_offline_hours_yesterday = daily_offline_hours.get(yesterday_key, 0)
                else:
                    yesterday_revenue = 0
                    daily_offline_hours_yesterday = 0
            
            # En İyi Gün = En fazla delta yapılan gün
            max_day_revenue = max(daily_deltas.values()) if daily_deltas else 0
            max_day_date = max(daily_deltas, key=daily_deltas.get) if daily_deltas else ""
            if max_day_date:
                max_day_date = datetime.strptime(max_day_date, "%Y-%m-%d").strftime("%d.%m.%Y")
            
            # Ortalama Günlük Kazanç = Aylık kümülatif toplam / gün sayısı
            # Ayın kaçıncı günündeyiz (örn: 26)
            last_day_obj = datetime.strptime(all_days[-1], "%Y-%m-%d")
            days_in_month = last_day_obj.day
            avg_daily_revenue = total_month_revenue / days_in_month if days_in_month > 0 else 0
        else:
            last_day_revenue = 0
            yesterday_revenue = 0
            max_day_revenue = 0
            max_day_date = ""
            avg_daily_revenue = 0
            total_month_revenue = 0
            daily_offline_hours_yesterday = 0
        
        # Count active devices (devices currently online based on last_seen_at)
        # NOT based on whether they sent data this month
        active_devices = 0
        for device in devices:
            if _get_device_online_status(device.last_seen_at):
                active_devices += 1
        
        # Calculate per-device offline hours from device_readings.status
        # Her cihaz için o ay içinde OFFLINE sürelerini hesapla
        # Timestamp farklarını kullanarak gerçek offline süresini hesapla
        month_start_dt = datetime(year, month, 1)
        if month == 12:
            month_end_dt = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end_dt = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        device_offline_hours_list = []
        for device in devices:
            # Query device_readings for this device in the month with offline status
            # Sıralı şekilde alarak timestamp farklarını hesapla
            offline_readings_result = await db.execute(
                select(DeviceReading.timestamp, DeviceReading.status)
                .where(
                    (DeviceReading.device_id == device.id) &
                    (DeviceReading.timestamp >= month_start_dt) &
                    (DeviceReading.timestamp <= month_end_dt)
                )
                .order_by(DeviceReading.timestamp.asc())
            )
            offline_readings = offline_readings_result.all()
            
            # Offline sürelerini hesapla
            offline_hours = 0.0
            offline_start = None
            
            for reading in offline_readings:
                timestamp, status = reading
                
                if status == 'offline' and offline_start is None:
                    # Offline başlangıcı
                    offline_start = timestamp
                elif status == 'online' and offline_start is not None:
                    # Offline bitişi, süreyi ekle
                    duration = (timestamp - offline_start).total_seconds() / 3600.0
                    offline_hours += duration
                    offline_start = None
                elif status == 'offline' and offline_start is not None:
                    # Hala offline, süre devam ediyor (hiçbir şey yapma)
                    pass
            
            # Eğer ay sonunda hala offline ise, ay sonuna kadar olan süreyi ekle
            if offline_start is not None:
                duration = (month_end_dt - offline_start).total_seconds() / 3600.0
                offline_hours += max(0, duration)
            
            device_name = device.name or device.device_code or f"Cihaz {device.id}"
            device_offline_hours_list.append(DeviceOfflineInfo(
                device_id=device.id,
                device_name=device_name,
                offline_hours=round(offline_hours, 2),
            ))
        
        # Sort by offline_hours descending (most offline first)
        device_offline_hours_list.sort(key=lambda x: x.offline_hours, reverse=True)
        
        return MonthlyStatsResponse(
            month=f"{year}-{month:02d}",
            month_name=month_name,
            last_day_revenue=round(last_day_revenue, 2),
            yesterday_revenue=round(yesterday_revenue, 2),
            max_day_revenue=round(max_day_revenue, 2),
            max_day_date=max_day_date,
            avg_daily_revenue=round(avg_daily_revenue, 2),
            total_month_revenue=round(total_month_revenue, 2),
            daily_offline_hours_yesterday=round(daily_offline_hours_yesterday, 2),
            total_devices=total_devices,
            active_devices=active_devices,
            device_offline_hours=device_offline_hours_list,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching monthly stats: {str(e)}")


@router.get("/devices/weekly-stats")
async def get_weekly_stats(
    year: int = Query(..., description="Year (e.g., 2026)"),
    week: int = Query(..., ge=1, le=53, description="Week number (1-53)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get weekly statistics for all devices.
    
    Returns weekly revenue data broken down by day.
    """
    try:
        # Calculate week start and end (ISO week date)
        # Week 1 is the week with the first Thursday of the year
        jan4 = datetime(year, 1, 4)
        week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week - 1)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Get all enabled devices
        devices_result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = devices_result.scalars().all()
        
        if not devices:
            return {
                "year": year,
                "week": week,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "daily_data": [],
                "total_week_revenue": 0,
                "avg_daily_revenue": 0,
            }
        
        total_devices = len(devices)
        
        # Initialize with last known values before week start
        device_last_values: Dict[int, Dict[str, float]] = {}
        for device in devices:
            pre_week_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp < week_start)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            pre_week_reading = pre_week_result.scalar_one_or_none()
            
            if pre_week_reading:
                device_last_values[device.id] = {
                    "counter_19l": pre_week_reading.counter_19l or 0,
                    "counter_5l": pre_week_reading.counter_5l or 0,
                }
            else:
                device_last_values[device.id] = {"counter_19l": 0, "counter_5l": 0}
        
        # Get readings for the week
        readings_result = await db.execute(
            select(DeviceReading)
            .where(
                (DeviceReading.timestamp >= week_start) &
                (DeviceReading.timestamp <= week_end)
            )
            .order_by(DeviceReading.timestamp.asc())
        )
        readings = readings_result.scalars().all()
        
        # Group by day, per device
        # Structure: daily_data[day_key][device_id] = {counter_19l, counter_5l}
        # Note: Each counter value is already the daily total revenue for that device
        daily_data: Dict[str, Dict[int, Dict[str, float]]] = {}
        day_names_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        day_labels: Dict[str, str] = {}
        
        for reading in readings:
            if not reading.timestamp:
                continue
            
            # Skip readings with None counter values (carry-forward will use last known value)
            if reading.counter_19l is None or reading.counter_5l is None:
                continue
            
            day_key = reading.timestamp.strftime("%Y-%m-%d")
            day_of_week = (reading.timestamp.weekday() + 1) % 7  # Monday = 0, Sunday = 6
            day_labels[day_key] = day_names_tr[day_of_week]
            
            if day_key not in daily_data:
                daily_data[day_key] = {}
            
            # Store the latest reading for this device on this day
            daily_data[day_key][reading.device_id] = {
                "counter_19l": reading.counter_19l,
                "counter_5l": reading.counter_5l,
            }
        
        # Calculate daily cumulative totals first (like all-chart-data does)
        # Then calculate deltas between consecutive days
        period_totals_19l: Dict[str, float] = {}
        period_totals_5l: Dict[str, float] = {}
        
        # Get all unique days
        all_days = sorted(daily_data.keys())
        
        # Track previous day's values for carry-forward (like all-chart-data)
        prev_day_values: Dict[int, Dict[str, float]] = device_last_values.copy()
        
        # Calculate cumulative totals for each day
        # Sadece o gün veri gönderen makineler toplanır (carry-forward yok)
        for day_key in all_days:
            day_total_19l = 0
            day_total_5l = 0
            
            # Sadece o gün verisi olan makineleri topla
            if day_key in daily_data:
                for device_id, values in daily_data[day_key].items():
                    today_19l = values["counter_19l"]
                    today_5l = values["counter_5l"]
                    
                    day_total_19l += today_19l
                    day_total_5l += today_5l
            
            period_totals_19l[day_key] = day_total_19l
            period_totals_5l[day_key] = day_total_5l
        
        # Get all devices' latest counter values for cumulative total_week_revenue
        total_all_devices_19l = 0
        total_all_devices_5l = 0
        
        for device in devices:
            latest_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            latest_reading = latest_result.scalar_one_or_none()
            
            if not latest_reading:
                fallback_result = await db.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .order_by(DeviceReading.timestamp.desc())
                    .limit(1)
                )
                latest_reading = fallback_result.scalar_one_or_none()
            
            if latest_reading:
                total_all_devices_19l += latest_reading.counter_19l or 0
                total_all_devices_5l += latest_reading.counter_5l or 0
        
        # total_week_revenue is cumulative (all devices' latest counter values)
        total_week_revenue = total_all_devices_19l + total_all_devices_5l
        
        # Calculate daily DELTAs (artış miktarı)
        # Delta = bugünün kümülatif - dünün kümülatif
        daily_deltas: Dict[str, float] = {}
        
        for i, day_key in enumerate(all_days):
            if i == 0:
                # İlk gün - delta = kümülatif değer (önceki gün yok)
                daily_deltas[day_key] = period_totals_19l[day_key] + period_totals_5l[day_key]
            else:
                # Delta = bugünün kümülatif - dünün kümülatif
                prev_day_key = all_days[i - 1]
                today_19l = period_totals_19l[day_key]
                today_5l = period_totals_5l[day_key]
                prev_19l = period_totals_19l[prev_day_key]
                prev_5l = period_totals_5l[prev_day_key]
                
                delta_19l = max(0, today_19l - prev_19l)
                delta_5l = max(0, today_5l - prev_5l)
                daily_deltas[day_key] = delta_19l + delta_5l
        
        # Calculate statistics
        # Ortalama Günlük Kazanç = Haftalık kümülatif toplam / 7 gün
        avg_daily_revenue = total_week_revenue / 7 if total_week_revenue > 0 else 0
        
        # Build daily list with delta values
        daily_list = []
        
        for day_key in all_days:
            day_delta = daily_deltas.get(day_key, 0)
            
            day_entry = {
                "date": day_key,
                "day_name": day_labels.get(day_key, ""),
                "counter_19l": period_totals_19l.get(day_key, 0),
                "counter_5l": period_totals_5l.get(day_key, 0),
                "revenue": round(day_delta, 2),
            }
            
            daily_list.append(day_entry)
        
        return {
            "year": year,
            "week": week,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "daily_data": daily_list,
            "total_week_revenue": round(total_week_revenue, 2),
            "avg_daily_revenue": round(avg_daily_revenue, 2),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weekly stats: {str(e)}")


@router.get("/devices/monthly-breakdown")
async def get_monthly_breakdown(
    year: int = Query(..., description="Year (e.g., 2026)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed monthly breakdown with daily data.
    
    Returns daily revenue data for the entire month.
    """
    try:
        # Calculate month start and end
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Get all enabled devices
        devices_result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = devices_result.scalars().all()
        
        if not devices:
            return {
                "year": year,
                "month": month,
                "month_start": month_start.isoformat(),
                "month_end": month_end.isoformat(),
                "daily_data": [],
                "total_month_revenue": 0,
                "avg_daily_revenue": 0,
                "max_day_revenue": 0,
                "max_day_date": "",
            }
        
        total_devices = len(devices)
        
        # Initialize with last known values before month start
        device_last_values: Dict[int, Dict[str, float]] = {}
        for device in devices:
            pre_month_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp < month_start)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            pre_month_reading = pre_month_result.scalar_one_or_none()
            
            if pre_month_reading:
                device_last_values[device.id] = {
                    "counter_19l": pre_month_reading.counter_19l or 0,
                    "counter_5l": pre_month_reading.counter_5l or 0,
                }
            else:
                device_last_values[device.id] = {"counter_19l": 0, "counter_5l": 0}
        
        # Get readings for the month
        readings_result = await db.execute(
            select(DeviceReading)
            .where(
                (DeviceReading.timestamp >= month_start) &
                (DeviceReading.timestamp <= month_end)
            )
            .order_by(DeviceReading.timestamp.asc())
        )
        readings = readings_result.scalars().all()
        
        # Group by day, per device
        # Structure: daily_data[day_key][device_id] = {counter_19l, counter_5l}
        # Note: Each counter value is already the daily total revenue for that device
        daily_data: Dict[str, Dict[int, Dict[str, float]]] = {}
        day_labels: Dict[str, str] = {}
        
        for reading in readings:
            if not reading.timestamp:
                continue
            
            # Skip readings with None counter values (carry-forward will use last known value)
            if reading.counter_19l is None or reading.counter_5l is None:
                continue
            
            day_key = reading.timestamp.strftime("%Y-%m-%d")
            day_labels[day_key] = reading.timestamp.strftime("%d.%m.%Y")
            
            if day_key not in daily_data:
                daily_data[day_key] = {}
            
            # Store the latest reading for this device on this day
            daily_data[day_key][reading.device_id] = {
                "counter_19l": reading.counter_19l,
                "counter_5l": reading.counter_5l,
            }
        
        # Calculate daily cumulative totals first (like all-chart-data does)
        # Then calculate deltas between consecutive days
        period_totals_19l: Dict[str, float] = {}
        period_totals_5l: Dict[str, float] = {}
        devices_with_data_per_day: Dict[str, set] = {}
        
        # Get all unique days
        all_days = sorted(daily_data.keys())
        
        # Track previous day's values for carry-forward (like all-chart-data)
        prev_day_values: Dict[int, Dict[str, float]] = device_last_values.copy()
        
        # Calculate cumulative totals for each day WITH CARRY-FORWARD
        # Include all devices (those with data today + those with carry-forward)
        for day_key in all_days:
            day_total_19l = 0
            day_total_5l = 0
            devices_with_data = set()
            
            # Update device values from today's data
            if day_key in daily_data:
                for device_id, values in daily_data[day_key].items():
                    prev_day_values[device_id] = values
                    devices_with_data.add(device_id)
            
            # Sum ALL devices (with today's data or carry-forward from previous days)
            for device in devices:
                if device.id in prev_day_values:
                    device_values = prev_day_values[device.id]
                    day_total_19l += device_values["counter_19l"]
                    day_total_5l += device_values["counter_5l"]
            
            period_totals_19l[day_key] = day_total_19l
            period_totals_5l[day_key] = day_total_5l
            devices_with_data_per_day[day_key] = devices_with_data
        
        # Get all devices' latest counter values for cumulative total_month_revenue
        total_all_devices_19l = 0
        total_all_devices_5l = 0
        
        for device in devices:
            latest_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            latest_reading = latest_result.scalar_one_or_none()
            
            if not latest_reading:
                fallback_result = await db.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .order_by(DeviceReading.timestamp.desc())
                    .limit(1)
                )
                latest_reading = fallback_result.scalar_one_or_none()
            
            if latest_reading:
                total_all_devices_19l += latest_reading.counter_19l or 0
                total_all_devices_5l += latest_reading.counter_5l or 0
        
        # total_month_revenue is cumulative (all devices' latest counter values)
        total_month_revenue = total_all_devices_19l + total_all_devices_5l
        
        # Calculate daily DELTAs (artış miktarı)
        # Delta = bugünün kümülatif - dünün kümülatif
        daily_deltas: Dict[str, float] = {}
        
        for i, day_key in enumerate(all_days):
            if i == 0:
                # İlk gün - delta = kümülatif değer (önceki gün yok)
                daily_deltas[day_key] = period_totals_19l[day_key] + period_totals_5l[day_key]
            else:
                # Delta = bugünün kümülatif - dünün kümülatif
                prev_day_key = all_days[i - 1]
                today_19l = period_totals_19l[day_key]
                today_5l = period_totals_5l[day_key]
                prev_19l = period_totals_19l[prev_day_key]
                prev_5l = period_totals_5l[prev_day_key]
                
                delta_19l = max(0, today_19l - prev_19l)
                delta_5l = max(0, today_5l - prev_5l)
                daily_deltas[day_key] = delta_19l + delta_5l
        
        # Calculate statistics
        # Use the actual day of month for average calculation
        if all_days:
            last_day_obj = datetime.strptime(all_days[-1], "%Y-%m-%d")
            days_in_month = last_day_obj.day
        else:
            days_in_month = month_start.day
        
        # Ortalama Günlük Kazanç = Aylık kümülatif toplam / gün sayısı
        avg_daily_revenue = total_month_revenue / days_in_month if days_in_month > 0 else 0
        
        # En İyi Gün = En fazla delta yapılan gün
        if daily_deltas:
            max_day_revenue = max(daily_deltas.values())
            max_day_date = max(daily_deltas, key=daily_deltas.get)
        else:
            max_day_revenue = 0
            max_day_date = ""
        
        # Build daily list with delta values
        daily_list = []
        
        for day_key in all_days:
            devices_with_data = devices_with_data_per_day.get(day_key, set())
            day_delta = daily_deltas.get(day_key, 0)
            
            day_entry = {
                "date": day_key,
                "date_label": day_labels.get(day_key, day_key),
                "counter_19l": period_totals_19l.get(day_key, 0),
                "counter_5l": period_totals_5l.get(day_key, 0),
                "revenue": round(day_delta, 2),
                "devices_with_data_count": len(devices_with_data),
                "devices_without_data_count": total_devices - len(devices_with_data),
                "offline_hours": (total_devices - len(devices_with_data)) * 24,
            }
            
            daily_list.append(day_entry)
        
        if max_day_date:
            max_day_date = datetime.strptime(max_day_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        
        return {
            "year": year,
            "month": month,
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "daily_data": daily_list,
            "total_month_revenue": round(total_month_revenue, 2),
            "avg_daily_revenue": round(avg_daily_revenue, 2),
            "max_day_revenue": round(max_day_revenue, 2),
            "max_day_date": max_day_date,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching monthly breakdown: {str(e)}")


# New endpoint for cumulative monthly comparison
class CumulativeComparisonResponse(BaseModel):
    """Response model for cumulative monthly comparison."""
    month1_data: List[Dict[str, Any]]
    month2_data: List[Dict[str, Any]]
    month1_name: str
    month2_name: str
    month1_total: float
    month2_total: float


@router.get("/devices/monthly-cumulative-comparison", response_model=CumulativeComparisonResponse)
async def get_monthly_cumulative_comparison(
    year1: int = Query(..., description="First month year (e.g., 2026)"),
    month1: int = Query(..., ge=1, le=12, description="First month (1-12)"),
    year2: int = Query(..., description="Second month year (e.g., 2026)"),
    month2: int = Query(..., ge=1, le=12, description="Second month (1-12)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cumulative revenue comparison for two months.
    
    Returns daily cumulative revenue data for both months.
    Cumulative means: day 1 = day 1 revenue, day 2 = day 1 + day 2 revenue, etc.
    """
    try:
        # Turkish month names
        month_names_tr = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        
        month1_name = f"{month_names_tr[month1 - 1]} {year1}"
        month2_name = f"{month_names_tr[month2 - 1]} {year2}"
        
        # Get all enabled devices
        devices_result = await db.execute(select(Device).where(Device.is_enabled == True))
        devices = devices_result.scalars().all()
        
        if not devices:
            return CumulativeComparisonResponse(
                month1_data=[],
                month2_data=[],
                month1_name=month1_name,
                month2_name=month2_name,
                month1_total=0,
                month2_total=0,
            )
        
        total_devices = len(devices)
        
        # Helper function to calculate cumulative data for a month
        async def calculate_month_cumulative(year: int, month: int):
            # Calculate month start and end
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
             
            # Get readings for the month
            readings_result = await db.execute(
                select(DeviceReading)
                .where(
                    (DeviceReading.timestamp >= month_start) &
                    (DeviceReading.timestamp <= month_end)
                )
                .order_by(DeviceReading.timestamp.asc())
            )
            readings = readings_result.scalars().all()
             
            # Group by day, per device - store latest reading per device per day
            daily_data: Dict[str, Dict[int, Dict[str, float]]] = {}
             
            for reading in readings:
                if not reading.timestamp:
                    continue
                
                # Skip readings with None counter values (carry-forward will use last known value)
                if reading.counter_19l is None or reading.counter_5l is None:
                    continue
                  
                day_key = reading.timestamp.strftime("%Y-%m-%d")
                  
                if day_key not in daily_data:
                    daily_data[day_key] = {}
                  
                # Store the latest reading for this device on this day
                daily_data[day_key][reading.device_id] = {
                    "counter_19l": reading.counter_19l,
                    "counter_5l": reading.counter_5l,
                }
             
            # Get all unique days
            all_days = sorted(daily_data.keys())
             
            # Track last known counter values for each device (carry-forward)
            last_known_values: Dict[int, Dict[str, float]] = {}
             
            # Calculate cumulative values - sum of last readings for each day
            cumulative_data = []
            day_number = 1
             
            for day_key in all_days:
                # For this day, sum the last reading values for all devices
                day_cumulative = 0
                day_daily_revenue = 0
                  
                if day_key in daily_data:
                    for device_id, values in daily_data[day_key].items():
                        # Update last known values for this device
                        last_known_values[device_id] = values
                        # Cumulative: sum of absolute counter values
                        day_cumulative += values["counter_19l"] + values["counter_5l"]
                
                # Include devices that didn't report today (carry-forward their last values)
                for device in devices:
                    if device.id not in daily_data.get(day_key, {}):
                        # Device didn't report today - use last known value
                        if device.id in last_known_values:
                            day_cumulative += last_known_values[device.id]["counter_19l"] + last_known_values[device.id]["counter_5l"]
                
                # Calculate daily revenue (delta from previous day)
                if day_number > 1 and cumulative_data:
                    prev_cumulative = cumulative_data[-1]["cumulative_revenue"]
                    day_daily_revenue = max(0, day_cumulative - prev_cumulative)
                else:
                    # First day - use cumulative as daily
                    day_daily_revenue = day_cumulative
                 
                # Parse day_key to get day label and actual calendar day
                day_date = datetime.strptime(day_key, "%Y-%m-%d")
                day_label = day_date.strftime("%d.%m")
                calendar_day = day_date.day  # Actual day of month (1-31)
                  
                cumulative_data.append({
                    "day": calendar_day,
                    "day_label": day_label,
                    "daily_revenue": round(day_daily_revenue, 2),
                    "cumulative_revenue": round(day_cumulative, 2),
                })
                day_number += 1
             
            # Calculate total cumulative revenue for the month
            # Use the sum of last readings for each device (same as monthly-stats)
            month_total = 0
            for device in devices:
                # Calculate month end date clearly (handle December -> next year)
                if month < 12:
                    month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
                else:
                    month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                
                last_reading_result = await db.execute(
                    select(DeviceReading)
                    .where(DeviceReading.device_id == device.id)
                    .where(DeviceReading.timestamp >= datetime(year, month, 1))
                    .where(DeviceReading.timestamp <= month_end)
                    .where(DeviceReading.counter_19l.isnot(None))
                    .where(DeviceReading.counter_5l.isnot(None))
                    .order_by(DeviceReading.timestamp.desc())
                    .limit(1)
                )
                last_reading = last_reading_result.scalar_one_or_none()
                if last_reading:
                    month_total += (last_reading.counter_19l or 0) + (last_reading.counter_5l or 0)
            
            # Fill missing days with carry-forward values
            # Create a map of existing days
            existing_days_map = {d["day"]: d for d in cumulative_data}
             
            # Get the last day with actual data
            last_day_with_data = max(existing_days_map.keys()) if existing_days_map else 0
             
            # Get current date to limit display to actual days that have passed
            now = datetime.now()
            current_year = now.year
            current_month = now.month
            current_day = now.day
             
            # Determine the max day to display
            # If this is the current month and year, only show up to current day
            # Otherwise, show all days that have data
            if year == current_year and month == current_month:
                max_day_to_show = min(last_day_with_data, current_day)
            else:
                # For past months, show all days that have data
                max_day_to_show = last_day_with_data
             
            # Fill all days up to max_day_to_show with carry-forward values
            filled_cumulative_data = []
            last_cumulative_value = 0
             
            for day in range(1, max_day_to_show + 1):
                if day in existing_days_map:
                    # Use existing data and update last value
                    data_point = existing_days_map[day]
                    last_cumulative_value = data_point["cumulative_revenue"]
                    filled_cumulative_data.append(data_point)
                else:
                    # Fill missing day with carry-forward value
                    # Create a placeholder label for missing days
                    filled_cumulative_data.append({
                        "day": day,
                        "day_label": f"{day:02d}.{month:02d}",
                        "daily_revenue": 0,
                        "cumulative_revenue": last_cumulative_value,
                    })
             
            return filled_cumulative_data, month_total
        
        # Calculate cumulative data for both months
        month1_data, month1_total = await calculate_month_cumulative(year1, month1)
        month2_data, month2_total = await calculate_month_cumulative(year2, month2)
        
        return CumulativeComparisonResponse(
            month1_data=month1_data,
            month2_data=month2_data,
            month1_name=month1_name,
            month2_name=month2_name,
            month1_total=round(month1_total, 2),
            month2_total=round(month2_total, 2),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cumulative comparison: {str(e)}")


# New endpoint for hourly online/offline status tracking
class HourlyStatusResponse(BaseModel):
    """Response model for hourly device status."""
    device_id: int
    device_name: str
    date: str  # Format: "YYYY-MM-DD"
    hourly_data: List[Dict[str, Any]]  # List of 24 hourly status entries


class HourlyStatusEntry(BaseModel):
    """Single hour status entry."""
    hour_start: str  # Format: "YYYY-MM-DD HH:00:00"
    hour_end: str  # Format: "YYYY-MM-DD HH:59:59"
    hour_label: str  # Format: "HH:00-HH:59"
    status: str  # ONLINE, OFFLINE, PARTIAL
    online_minutes: int
    offline_minutes: int
    data_points: int


@router.get("/devices/{device_id}/hourly-status", response_model=HourlyStatusResponse)
async def get_device_hourly_status(
    device_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hourly online/offline status for a device on a specific date.
    
    Returns 24 hourly status entries showing:
    - Hour range (e.g., "00:00-01:00")
    - Status (ONLINE, OFFLINE, PARTIAL)
    - Online minutes (0-60)
    - Offline minutes (0-60)
    - Data points received during that hour
    """
    try:
        # Parse the date
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {date}. Use YYYY-MM-DD")
        
        # Get device
        device_result = await db.execute(select(Device).where(Device.id == device_id))
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # Calculate day start and end (in UTC)
        day_start = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = query_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Import DeviceHourlyStatus model
        from app.models.device_status import DeviceHourlyStatus
        
        # Query hourly status records for this device and date
        hourly_status_result = await db.execute(
            select(DeviceHourlyStatus)
            .where(DeviceHourlyStatus.device_id == device_id)
            .where(DeviceHourlyStatus.hour_start >= day_start)
            .where(DeviceHourlyStatus.hour_end <= day_end)
            .order_by(DeviceHourlyStatus.hour_start.asc())
        )
        hourly_records = hourly_status_result.scalars().all()
        
        # Build a map of existing records
        hourly_map = {}
        for record in hourly_records:
            hour_key = record.hour_start.hour
            hourly_map[hour_key] = {
                "hour_start": record.hour_start.strftime("%Y-%m-%d %H:00:00"),
                "hour_end": record.hour_end.strftime("%Y-%m-%d %H:59:59"),
                "hour_label": f"{hour_key:02d}:00-{hour_key+1:02d}:59",
                "status": record.status,
                "online_minutes": record.online_minutes,
                "offline_minutes": record.offline_minutes,
                "data_points": record.data_points,
            }
        
        # Build 24 hourly entries (fill missing hours with OFFLINE status)
        hourly_data = []
        for hour in range(24):
            if hour in hourly_map:
                # Use existing record
                hourly_data.append(hourly_map[hour])
            else:
                # No record for this hour - assume OFFLINE
                hourly_data.append({
                    "hour_start": (day_start + timedelta(hours=hour)).strftime("%Y-%m-%d %H:00:00"),
                    "hour_end": (day_start + timedelta(hours=hour)).replace(minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S"),
                    "hour_label": f"{hour:02d}:00-{hour+1:02d}:59",
                    "status": "OFFLINE",
                    "online_minutes": 0,
                    "offline_minutes": 60,
                    "data_points": 0,
                })
        
        return HourlyStatusResponse(
            device_id=device_id,
            device_name=device.name or f"Device {device.device_code}",
            date=date,
            hourly_data=hourly_data,
        )
    
    except HTTPException:
         raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching hourly status: {str(e)}")


@router.get("/devices/hourly-status")
async def get_all_devices_hourly_status(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    device_id: Optional[int] = Query(None, description="Filter by specific device ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get hourly online/offline status for all devices within a date range.
    
    Query Parameters:
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 7 days ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    - device_id: Filter by specific device ID (optional)
    
    Returns aggregated hourly status data grouped by device and hour.
    """
    try:
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse dates
        try:
            query_start = datetime.strptime(start_date, "%Y-%m-%d")
            query_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Import DeviceHourlyStatus model
        from app.models.device_status import DeviceHourlyStatus
        
        # Build query
        query = (
            select(DeviceHourlyStatus, Device)
            .join(Device, DeviceHourlyStatus.device_id == Device.id)
            .where(DeviceHourlyStatus.hour_start >= query_start)
            .where(DeviceHourlyStatus.hour_end <= query_end)
        )
        
        # Add device filter if specified
        if device_id is not None:
            query = query.where(DeviceHourlyStatus.device_id == device_id)
        
        # Order by hour and device
        query = query.order_by(DeviceHourlyStatus.hour_start.asc(), Device.id.asc())
        
        # Execute query
        result = await db.execute(query)
        records = result.all()
        
        # Format response data
        data = []
        for record, device in records:
            data.append({
                "device_id": record.device_id,
                "device_code": device.device_code,
                "hour_start": record.hour_start.isoformat(),
                "status": record.status,
                "online_minutes": record.online_minutes,
                "offline_minutes": record.offline_minutes,
                "data_points": record.data_points,
            })
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_records": len(data),
            "data": data,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching hourly status: {str(e)}")


# Snapshot Status Response Models
class SnapshotStatusResponse(BaseModel):
    device_id: int
    device_code: str
    device_name: Optional[str]
    snapshot_time: str
    status: str
    last_seen_at: Optional[str]
    data_received: bool
    null_values_count: int


class AllSnapshotsResponse(BaseModel):
    start_date: str
    end_date: str
    total_records: int
    data: List[SnapshotStatusResponse]


@router.get("/devices/{device_id}/snapshots", response_model=AllSnapshotsResponse)
async def get_device_snapshots(
    device_id: int,
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get 10-minute snapshot status for a specific device within a date range.
    
    Query Parameters:
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 24 hours ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to now)
    
    Returns 10-minute interval snapshot data showing device online/offline status
    with null value detection.
    """
    try:
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse dates
        try:
            query_start = datetime.strptime(start_date, "%Y-%m-%d")
            query_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Import DeviceStatusSnapshot model
        from app.models.device_status import DeviceStatusSnapshot
        
        # Check if device exists
        device_stmt = select(Device).where(Device.id == device_id)
        device_result = await db.execute(device_stmt)
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found")
        
        # Build query for snapshots
        stmt = (
            select(DeviceStatusSnapshot)
            .where(DeviceStatusSnapshot.device_id == device_id)
            .where(DeviceStatusSnapshot.snapshot_time >= query_start)
            .where(DeviceStatusSnapshot.snapshot_time <= query_end)
            .order_by(DeviceStatusSnapshot.snapshot_time.asc())
        )
        
        # Execute query
        result = await db.execute(stmt)
        snapshots = result.scalars().all()
        
        # Format response data
        snapshot_data = []
        for snapshot in snapshots:
            snapshot_data.append(
                SnapshotStatusResponse(
                    device_id=snapshot.device_id,
                    device_code=device.device_code,
                    device_name=device.name,
                    snapshot_time=snapshot.snapshot_time.isoformat(),
                    status=snapshot.status,
                    last_seen_at=snapshot.last_seen_at.isoformat() if snapshot.last_seen_at else None,
                    data_received=bool(snapshot.data_received),
                    null_values_count=snapshot.null_values_count,
                )
            )
        
        return AllSnapshotsResponse(
            start_date=start_date,
            end_date=end_date,
            total_records=len(snapshot_data),
            data=snapshot_data,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching snapshots: {str(e)}")


@router.get("/devices/snapshots", response_model=AllSnapshotsResponse)
async def get_all_devices_snapshots(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    device_id: Optional[int] = Query(None, description="Filter by specific device ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get 10-minute snapshot status for all devices within a date range.
    
    Query Parameters:
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 24 hours ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to now)
    - device_id: Filter by specific device ID (optional)
    
    Returns 10-minute interval snapshot data showing device online/offline status
    with null value detection for all devices.
    """
    try:
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Parse dates
        try:
            query_start = datetime.strptime(start_date, "%Y-%m-%d")
            query_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Import DeviceStatusSnapshot model
        from app.models.device_status import DeviceStatusSnapshot
        
        # Build query
        query = (
            select(DeviceStatusSnapshot, Device)
            .join(Device, DeviceStatusSnapshot.device_id == Device.id)
            .where(DeviceStatusSnapshot.snapshot_time >= query_start)
            .where(DeviceStatusSnapshot.snapshot_time <= query_end)
        )
        
        # Add device filter if specified
        if device_id is not None:
            query = query.where(DeviceStatusSnapshot.device_id == device_id)
        
        # Order by snapshot time and device
        query = query.order_by(DeviceStatusSnapshot.snapshot_time.asc(), Device.id.asc())
        
        # Execute query
        result = await db.execute(query)
        records = result.all()
        
        # Format response data
        snapshot_data = []
        for snapshot, device in records:
            snapshot_data.append(
                SnapshotStatusResponse(
                    device_id=snapshot.device_id,
                    device_code=device.device_code,
                    device_name=device.name,
                    snapshot_time=snapshot.snapshot_time.isoformat(),
                    status=snapshot.status,
                    last_seen_at=snapshot.last_seen_at.isoformat() if snapshot.last_seen_at else None,
                    data_received=bool(snapshot.data_received),
                    null_values_count=snapshot.null_values_count,
                )
            )
        
        return AllSnapshotsResponse(
            start_date=start_date,
            end_date=end_date,
            total_records=len(snapshot_data),
            data=snapshot_data,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching snapshots: {str(e)}")
