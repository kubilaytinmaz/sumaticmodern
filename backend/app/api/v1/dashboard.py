"""
Sumatic Modern IoT - Dashboard Endpoints
Dashboard overview and quick stats endpoints.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.services.device_service import DeviceService
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _is_device_online(last_seen_at, threshold_seconds: int) -> bool:
    """Check if device is online based on last_seen_at with proper timezone handling."""
    if not last_seen_at:
        return False
    now_utc = datetime.now(timezone.utc)
    # Convert last_seen_at to UTC if timezone-aware, or treat as UTC if naive
    if hasattr(last_seen_at, 'tzinfo') and last_seen_at.tzinfo is not None:
        last_seen_utc = last_seen_at.astimezone(timezone.utc)
    else:
        last_seen_utc = last_seen_at.replace(tzinfo=timezone.utc)
    return (now_utc - last_seen_utc).total_seconds() < threshold_seconds


@router.get("/overview")
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get dashboard overview with key stats.
    
    Args:
        db: Database session
        
    Returns:
        Dashboard overview data
    """
    # Get summary stats (last 24 hours)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    summary = await AnalyticsService.get_summary_stats(
        db=db, start_time=start_time, end_time=end_time
    )
    
    # Get device counts with proper timezone-aware comparison
    devices = await DeviceService.list_devices(db=db, skip=0, limit=1000)
    total_devices = len(devices[0])
    online_devices = sum(
        1 for d in devices[0]
        if _is_device_online(d.last_seen_at, settings.DEVICE_OFFLINE_THRESHOLD_SECONDS)
    )
    
    return {
        "summary": summary,
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": total_devices - online_devices,
    }


@router.get("/alerts")
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get active alerts for the dashboard.
    
    Args:
        db: Database session
        
    Returns:
        List of active alerts
    """
    # Placeholder - implement alert logic
    return {
        "alerts": [],
        "count": 0,
    }


@router.get("/stats/hourly")
async def get_hourly_stats(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get hourly statistics for charts.
    
    Args:
        hours: Number of hours to look back
        db: Database session
        
    Returns:
        Hourly statistics
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    revenue_data = await AnalyticsService.get_revenue_analytics(
        db=db,
        start_time=start_time,
        end_time=end_time,
        granularity="hour",
    )
    
    return {
        "revenue": revenue_data,
        "period": f"last_{hours}_hours",
    }


@router.get("/stats/daily")
async def get_daily_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get daily statistics for charts.
    
    Args:
        days: Number of days to look back
        db: Database session
        
    Returns:
        Daily statistics
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    revenue_data = await AnalyticsService.get_revenue_analytics(
        db=db,
        start_time=start_time,
        end_time=end_time,
        granularity="day",
    )
    
    return {
        "revenue": revenue_data,
        "period": f"last_{days}_days",
    }
