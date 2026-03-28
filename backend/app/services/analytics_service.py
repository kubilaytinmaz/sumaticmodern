"""
Sumatic Modern IoT - Analytics Service
Business logic for analytics and reporting operations.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Literal
from sqlalchemy import select, func, and_, or_, desc, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text

from app.models.reading import DeviceReading
from app.models.device import Device
from app.core.exceptions import NotFoundException


class AnalyticsService:
    """Service for analytics and reporting operations."""

    @staticmethod
    async def get_summary_stats(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get summary statistics for dashboard.
        
        Args:
            db: Database session
            start_time: Start time for stats (default: 24 hours ago)
            end_time: End time for stats (default: now)
            
        Returns:
            Summary statistics dict
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Total devices
        total_devices = await db.scalar(
            select(func.count()).select_from(Device).where(Device.is_enabled == True)
        )
        
        # Online devices (seen in last 10 minutes)
        online_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        online_devices = await db.scalar(
            select(func.count()).select_from(Device).where(
                and_(
                    Device.is_enabled == True,
                    Device.last_seen_at >= online_threshold,
                )
            )
        )
        
        # Offline devices
        offline_devices = (total_devices or 0) - (online_devices or 0)
        
        # Total readings in period (no is_spike column - counter-only model)
        total_readings = await db.scalar(
            select(func.count()).select_from(DeviceReading).where(
                and_(
                    DeviceReading.timestamp >= start_time,
                    DeviceReading.timestamp <= end_time,
                )
            )
        )
        
        # Total counter deltas (revenue proxy) - SQLite compatible, no is_spike column
        counter_query = text("""
            SELECT
                COALESCE(SUM(counter_19l_delta), 0) as total_19l,
                COALESCE(SUM(counter_5l_delta), 0) as total_5l
            FROM (
                SELECT
                    device_id,
                    MAX(counter_19l) - MIN(counter_19l) as counter_19l_delta,
                    MAX(counter_5l) - MIN(counter_5l) as counter_5l_delta
                FROM device_readings
                WHERE timestamp >= :start_time
                    AND timestamp <= :end_time
                    AND counter_19l IS NOT NULL
                GROUP BY device_id
            ) deltas
        """)
        
        result = await db.execute(
            counter_query,
            {"start_time": start_time, "end_time": end_time}
        )
        row = result.fetchone()
        
        return {
            "total_devices": total_devices or 0,
            "online_devices": online_devices or 0,
            "offline_devices": offline_devices or 0,
            "total_readings": total_readings or 0,
            "fault_count": 0,
            "total_19l_delta": row.total_19l if row else 0,
            "total_5l_delta": row.total_5l if row else 0,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

    @staticmethod
    async def get_revenue_analytics(
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        granularity: Literal["hour", "day", "week", "month"] = "day",
        device_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get revenue analytics by time period.
        
        Args:
            db: Database session
            start_time: Start time
            end_time: End time
            granularity: Time granularity (hour, day, week, month)
            device_ids: Optional device IDs filter
            
        Returns:
            List of revenue data points
        """
        # Determine time bucket function based on granularity
        time_bucket_map = {
            "hour": "date_trunc('hour', timestamp)",
            "day": "date_trunc('day', timestamp)",
            "week": "date_trunc('week', timestamp)",
            "month": "date_trunc('month', timestamp)",
        }
        
        time_bucket = time_bucket_map.get(granularity, "date_trunc('day', timestamp)")
        
        # SQLite compatible - no is_spike column, no ANY() operator
        if device_ids:
            device_ids_str = ",".join(str(d) for d in device_ids)
            device_filter = f"AND device_id IN ({device_ids_str})"
        else:
            device_filter = ""
        
        # SQLite strftime for time bucketing
        sqlite_bucket_map = {
            "hour": "strftime('%Y-%m-%d %H:00:00', timestamp)",
            "day": "strftime('%Y-%m-%d 00:00:00', timestamp)",
            "week": "strftime('%Y-%W', timestamp)",
            "month": "strftime('%Y-%m-01 00:00:00', timestamp)",
        }
        sqlite_bucket = sqlite_bucket_map.get(granularity, "strftime('%Y-%m-%d 00:00:00', timestamp)")
        
        query = text(f"""
            SELECT
                {sqlite_bucket} as time_period,
                device_id,
                MAX(counter_19l) - MIN(counter_19l) as counter_19l_delta,
                MAX(counter_5l) - MIN(counter_5l) as counter_5l_delta,
                COUNT(*) as reading_count,
                0 as fault_count
            FROM device_readings
            WHERE timestamp >= :start_time
                AND timestamp <= :end_time
                {device_filter}
            GROUP BY time_period, device_id
            ORDER BY time_period ASC, device_id ASC
        """)
        
        result = await db.execute(
            query,
            {
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        
        return [
            {
                "time_period": row.time_period.isoformat(),
                "device_id": row.device_id,
                "counter_19l_delta": row.counter_19l_delta or 0,
                "counter_5l_delta": row.counter_5l_delta or 0,
                "reading_count": row.reading_count,
                "fault_count": row.fault_count or 0,
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_device_comparison(
        db: AsyncSession,
        device_ids: List[int],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple devices over a time period.
        
        Args:
            db: Database session
            device_ids: List of device IDs to compare
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)
            
        Returns:
            List of device comparison data
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Get device info
        devices_result = await db.execute(
            select(Device).where(Device.id.in_(device_ids))
        )
        devices = {d.id: d for d in devices_result.scalars().all()}
        
        # Get stats per device
        # SQLite compatible - no is_spike, no ANY() operator
        if device_ids:
            device_ids_str = ",".join(str(d) for d in device_ids)
        else:
            device_ids_str = "0"  # Fallback - no devices
        
        query = text(f"""
            SELECT
                device_id,
                MAX(counter_19l) - MIN(counter_19l) as counter_19l_delta,
                MAX(counter_5l) - MIN(counter_5l) as counter_5l_delta,
                COUNT(*) as reading_count,
                0 as fault_count,
                MAX(timestamp) as last_reading_time,
                MIN(timestamp) as first_reading_time
            FROM device_readings
            WHERE device_id IN ({device_ids_str})
                AND timestamp >= :start_time
                AND timestamp <= :end_time
            GROUP BY device_id
        """)
        
        result = await db.execute(
            query,
            {
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        
        comparison = []
        for row in result.fetchall():
            device = devices.get(row.device_id)
            if not device:
                continue
            
            comparison.append({
                "device_id": row.device_id,
                "device_code": device.device_code,
                "device_name": device.name,
                "location": device.location,
                "counter_19l_delta": row.counter_19l_delta or 0,
                "counter_5l_delta": row.counter_5l_delta or 0,
                "reading_count": row.reading_count,
                "fault_count": row.fault_count or 0,
                "last_reading_time": row.last_reading_time.isoformat() if row.last_reading_time else None,
                "first_reading_time": row.first_reading_time.isoformat() if row.first_reading_time else None,
                "uptime_percentage": 100.0 - (row.fault_count * 100.0 / row.reading_count) if row.reading_count > 0 else 0,
            })
        
        return comparison

    @staticmethod
    async def get_downtime_report(
        db: AsyncSession,
        device_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get downtime report for a device.
        
        Args:
            db: Database session
            device_id: Device ID
            start_time: Start time (default: 7 days ago)
            end_time: End time (default: now)
            
        Returns:
            Downtime report
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        # Verify device exists
        device_result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = device_result.scalar_one_or_none()
        if not device:
            raise NotFoundException(f"Device with id {device_id} not found")
        
        # Get status changes in period
        query = text("""
            SELECT 
                status,
                started_at,
                ended_at,
                duration_seconds,
                reason
            FROM device_status
            WHERE device_id = :device_id
                AND started_at >= :start_time
                AND (ended_at IS NULL OR ended_at <= :end_time)
            ORDER BY started_at ASC
        """)
        
        result = await db.execute(
            query,
            {"device_id": device_id, "start_time": start_time, "end_time": end_time}
        )
        statuses = result.fetchall()
        
        # Calculate totals
        total_offline_seconds = sum(
            s.duration_seconds or 0
            for s in statuses
            if s.status == "OFFLINE"
        )
        total_period_seconds = (end_time - start_time).total_seconds()
        
        offline_count = sum(1 for s in statuses if s.status == "OFFLINE")
        online_count = sum(1 for s in statuses if s.status == "ONLINE")
        
        # Get current status
        current_status = "UNKNOWN"
        if device.last_seen_at:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
            current_status = "ONLINE" if device.last_seen_at >= threshold else "OFFLINE"
        
        return {
            "device_id": device_id,
            "device_code": device.device_code,
            "device_name": device.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_period_seconds": total_period_seconds,
            "total_offline_seconds": total_offline_seconds,
            "total_online_seconds": total_period_seconds - total_offline_seconds,
            "offline_percentage": (total_offline_seconds / total_period_seconds * 100) if total_period_seconds > 0 else 0,
            "online_percentage": ((total_period_seconds - total_offline_seconds) / total_period_seconds * 100) if total_period_seconds > 0 else 0,
            "offline_count": offline_count,
            "online_count": online_count,
            "current_status": current_status,
            "status_history": [
                {
                    "status": s.status,
                    "started_at": s.started_at.isoformat(),
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "duration_seconds": s.duration_seconds,
                    "reason": s.reason,
                }
                for s in statuses
            ],
        }

    @staticmethod
    async def get_top_devices(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric: Literal["19l", "5l", "readings"] = "19l",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing devices by metric.
        
        Args:
            db: Database session
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)
            metric: Metric to rank by (19l, 5l, readings)
            limit: Maximum number of devices
            
        Returns:
            List of top devices
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Determine column based on metric
        column_map = {
            "19l": "counter_19l",
            "5l": "counter_5l",
            "readings": "reading_count",
        }
        
        if metric == "readings":
            query = text("""
                SELECT
                    device_id,
                    COUNT(*) as reading_count
                FROM device_readings
                WHERE timestamp >= :start_time
                    AND timestamp <= :end_time
                GROUP BY device_id
                ORDER BY reading_count DESC
                LIMIT :limit
            """)
        else:
            column = column_map[metric]
            query = text(f"""
                SELECT
                    device_id,
                    MAX({column}) - MIN({column}) as delta
                FROM device_readings
                WHERE timestamp >= :start_time
                    AND timestamp <= :end_time
                    AND {column} IS NOT NULL
                GROUP BY device_id
                ORDER BY delta DESC
                LIMIT :limit
            """)
        
        result = await db.execute(
            query,
            {"start_time": start_time, "end_time": end_time, "limit": limit}
        )
        
        device_ids = [row.device_id for row in result.fetchall()]
        
        if not device_ids:
            return []
        
        # Get device details
        devices_result = await db.execute(
            select(Device).where(Device.id.in_(device_ids))
        )
        devices = {d.id: d for d in devices_result.scalars().all()}
        
        # Re-run query to get full results with device info
        result = await db.execute(
            query,
            {"start_time": start_time, "end_time": end_time, "limit": limit}
        )
        
        return [
            {
                "device_id": row.device_id,
                "device_code": devices[row.device_id].device_code if row.device_id in devices else None,
                "device_name": devices[row.device_id].name if row.device_id in devices else None,
                "metric_value": row.delta if metric != "readings" else row.reading_count,
            }
            for row in result.fetchall()
        ]

    @staticmethod
    async def get_fault_report(
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        device_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get fault report for devices.
        
        Note: Counter-only model doesn't have fault_status or raw_data columns.
        This method returns empty list for compatibility.
        
        Args:
            db: Database session
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)
            device_id: Optional device ID filter
            
        Returns:
            Empty list (no fault data in counter-only model)
        """
        return []
