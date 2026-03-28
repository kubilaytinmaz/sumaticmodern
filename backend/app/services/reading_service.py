"""
Sumatic Modern IoT - Reading Service
Business logic for device reading operations.
Counter-Only Optimization: Only counter_19l and counter_5l are stored.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.models.reading import DeviceReading
from app.models.device import Device
from app.schemas.reading import ReadingQuery, ReadingSummary
from app.core.exceptions import NotFoundException
from app.config import get_settings
from app.redis_client import cache_device_reading, get_cached_device_reading

settings = get_settings()


class ReadingService:
    """Service for device reading operations."""

    @staticmethod
    async def create_reading(
        db: AsyncSession,
        device_id: int,
        timestamp: datetime,
        counter_19l: Optional[int] = None,
        counter_5l: Optional[int] = None,
    ) -> DeviceReading:
        """
        Create a new device reading - COUNTER ONLY.
        
        Args:
            db: Database session
            device_id: Device ID
            timestamp: Reading timestamp
            counter_19l: 19L counter value
            counter_5l: 5L counter value
            
        Returns:
            Created reading
        """
        reading = DeviceReading(
            device_id=device_id,
            timestamp=timestamp,
            counter_19l=counter_19l,
            counter_5l=counter_5l,
        )
        db.add(reading)
        await db.flush()
        await db.refresh(reading)
        
        # Cache latest reading
        await cache_device_reading(device_id, {
            "id": reading.id,
            "device_id": reading.device_id,
            "timestamp": reading.timestamp.isoformat(),
            "counter_19l": reading.counter_19l,
            "counter_5l": reading.counter_5l,
        })
        
        return reading

    @staticmethod
    async def get_readings(
        db: AsyncSession,
        query: ReadingQuery,
    ) -> tuple[List[DeviceReading], int]:
        """
        Query readings with filtering and pagination.
        
        Args:
            db: Database session
            query: Reading query parameters
            
        Returns:
            Tuple of (readings list, total count)
        """
        base_query = select(DeviceReading)
        count_query = select(func.count()).select_from(DeviceReading)
        
        # Build filters
        filters = []
        
        # Device ID filter
        if query.device_id:
            filters.append(DeviceReading.device_id == query.device_id)
        
        # Multiple device IDs filter
        if query.device_ids:
            filters.append(DeviceReading.device_id.in_(query.device_ids))
        
        # Time range filter
        if query.start_time:
            filters.append(DeviceReading.timestamp >= query.start_time)
        
        if query.end_time:
            filters.append(DeviceReading.timestamp <= query.end_time)
        
        if filters:
            base_query = base_query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total = await db.scalar(count_query)
        
        # Get paginated results
        offset = (query.page - 1) * query.page_size
        base_query = (
            base_query
            .order_by(desc(DeviceReading.timestamp))
            .offset(offset)
            .limit(query.page_size)
        )
        
        result = await db.execute(base_query)
        readings = result.scalars().all()
        
        return list(readings), total or 0

    @staticmethod
    async def get_latest_readings(
        db: AsyncSession,
        device_ids: Optional[List[int]] = None,
        use_cache: bool = True,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get latest reading for each device.
        
        Args:
            db: Database session
            device_ids: Optional list of device IDs to filter
            use_cache: Whether to use Redis cache
            
        Returns:
            Dict mapping device_id to latest reading
        """
        result = {}
        
        # If specific devices requested, try cache first
        if device_ids and use_cache:
            for device_id in device_ids:
                cached = await get_cached_device_reading(device_id)
                if cached:
                    result[device_id] = cached
        
        # Get devices not in cache or if no specific devices
        devices_to_query = []
        if device_ids:
            devices_to_query = [d for d in device_ids if d not in result]
        else:
            # Get all enabled devices
            devices_result = await db.execute(
                select(Device.id).where(Device.is_enabled == True)
            )
            devices_to_query = list(devices_result.scalars().all())
        
        if devices_to_query:
            # Use subquery to get latest reading per device
            subquery = (
                select(
                    DeviceReading.device_id,
                    func.max(DeviceReading.timestamp).label("max_timestamp")
                )
                .group_by(DeviceReading.device_id)
            )
            
            if devices_to_query:
                subquery = subquery.where(
                    DeviceReading.device_id.in_(devices_to_query)
                )
            
            subquery = subquery.subquery()
            
            # Join with main table to get full reading data
            query = (
                select(DeviceReading)
                .join(
                    subquery,
                    and_(
                        DeviceReading.device_id == subquery.c.device_id,
                        DeviceReading.timestamp == subquery.c.max_timestamp,
                    )
                )
            )
            
            db_result = await db.execute(query)
            readings = db_result.scalars().all()
            
            for reading in readings:
                reading_dict = {
                    "id": reading.id,
                    "device_id": reading.device_id,
                    "timestamp": reading.timestamp.isoformat(),
                    "counter_19l": reading.counter_19l,
                    "counter_5l": reading.counter_5l,
                }
                result[reading.device_id] = reading_dict
                
                # Update cache
                if use_cache:
                    await cache_device_reading(reading.device_id, reading_dict)
        
        return result

    @staticmethod
    async def get_device_readings(
        db: AsyncSession,
        device_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DeviceReading]:
        """
        Get readings for a specific device.
        
        Args:
            db: Database session
            device_id: Device ID
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of readings
            
        Returns:
            List of readings
        """
        query = select(DeviceReading).where(DeviceReading.device_id == device_id)
        
        if start_time:
            query = query.where(DeviceReading.timestamp >= start_time)
        
        if end_time:
            query = query.where(DeviceReading.timestamp <= end_time)
        
        query = query.order_by(desc(DeviceReading.timestamp)).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_reading_summary(
        db: AsyncSession,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> ReadingSummary:
        """
        Get reading summary for a device in a time range.
        
        Args:
            db: Database session
            device_id: Device ID
            start_time: Start time
            end_time: End time
            
        Returns:
            Reading summary with deltas
        """
        # Get first and last readings in range
        query = (
            select(DeviceReading)
            .where(
                and_(
                    DeviceReading.device_id == device_id,
                    DeviceReading.timestamp >= start_time,
                    DeviceReading.timestamp <= end_time,
                )
            )
            .order_by(asc(DeviceReading.timestamp))
        )
        
        result = await db.execute(query)
        readings = result.scalars().all()
        
        if not readings:
            return ReadingSummary(
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                reading_count=0,
            )
        
        first = readings[0]
        last = readings[-1]
        
        # Calculate deltas
        counter_19l_delta = None
        if first.counter_19l is not None and last.counter_19l is not None:
            counter_19l_delta = last.counter_19l - first.counter_19l
        
        counter_5l_delta = None
        if first.counter_5l is not None and last.counter_5l is not None:
            counter_5l_delta = last.counter_5l - first.counter_5l
        
        return ReadingSummary(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            counter_19l_start=first.counter_19l,
            counter_19l_end=last.counter_19l,
            counter_19l_delta=counter_19l_delta,
            counter_5l_start=first.counter_5l,
            counter_5l_end=last.counter_5l,
            counter_5l_delta=counter_5l_delta,
            reading_count=len(readings),
        )

    @staticmethod
    async def get_readings_by_timerange(
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        device_ids: Optional[List[int]] = None,
        interval_minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated readings by time interval.
        Useful for charts and time-series visualization.
        
        Args:
            db: Database session
            start_time: Start time
            end_time: End time
            device_ids: Optional device IDs filter
            interval_minutes: Aggregation interval
            
        Returns:
            List of aggregated readings
        """
        # SQLite-compatible time bucket aggregation
        query = text("""
            SELECT 
                device_id,
                strftime('%Y-%m-%dT%H:', timestamp) || 
                    printf('%02d', (CAST(strftime('%M', timestamp) AS INTEGER) / :interval) * :interval) || ':00' as time_bucket,
                MAX(counter_19l) as counter_19l,
                MAX(counter_5l) as counter_5l,
                COUNT(*) as reading_count
            FROM device_readings
            WHERE timestamp >= :start_time
                AND timestamp <= :end_time
            GROUP BY device_id, time_bucket
            ORDER BY time_bucket ASC, device_id ASC
        """)
        
        result = await db.execute(
            query,
            {
                "start_time": start_time,
                "end_time": end_time,
                "interval": interval_minutes,
            }
        )
        
        return [
            {
                "device_id": row.device_id,
                "time_bucket": row.time_bucket,
                "counter_19l": row.counter_19l,
                "counter_5l": row.counter_5l,
                "reading_count": row.reading_count,
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def delete_old_readings(
        db: AsyncSession,
        older_than_days: int = 365,
    ) -> int:
        """
        Delete readings older than specified days.
        Used for data retention/cleanup.
        
        Args:
            db: Database session
            older_than_days: Delete readings older than this many days
            
        Returns:
            Number of deleted readings
        """
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = await db.execute(
            select(func.count()).select_from(DeviceReading).where(
                DeviceReading.timestamp < cutoff
            )
        )
        count = result.scalar() or 0
        
        if count > 0:
            await db.execute(
                text("DELETE FROM device_readings WHERE timestamp < :cutoff"),
                {"cutoff": cutoff.isoformat()}
            )
            await db.flush()
        
        return count
