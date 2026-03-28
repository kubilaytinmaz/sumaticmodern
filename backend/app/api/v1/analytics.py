"""
Sumatic Modern IoT - Analytics Endpoints
Analytics and reporting endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Literal, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.core.logging import get_logger
logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_summary_stats(
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get summary statistics for dashboard.
    
    Args:
        start_time: Start time
        end_time: End time
        db: Database session
        
    Returns:
        Summary statistics
    """
    return await AnalyticsService.get_summary_stats(
        db=db, start_time=start_time, end_time=end_time
    )


@router.get("/revenue")
async def get_revenue_analytics(
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    period: Literal["hour", "day", "week", "month"] = Query(
        "day", description="Time granularity"
    ),
    device_ids: Optional[str] = Query(
        None, description="Comma-separated device IDs (optional)"
    ),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get revenue analytics by time period.
    
    Args:
        start_time: Start time
        end_time: End time
        period: Time period
        device_ids: Optional comma-separated device IDs
        db: Database session
        
    Returns:
        List of revenue data points
    """
    # Parse device_ids if provided
    try:
        ids_list = [int(id.strip()) for id in device_ids.split(",")]
    except ValueError:
        ids_list = None
    
    return await AnalyticsService.get_revenue_analytics(
        db=db, start_time=start_time, end_time=end_time, period=period, device_ids=ids_list
    )


@router.get("/comparison")
async def get_device_comparison(
    device_ids: str = Query(..., description="Comma-separated device IDs"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Compare multiple devices over a time period.
    
    Args:
        device_ids: Comma-separated device IDs
        start_time: Start time
        end_time: End time
        db: Database session
        
    Returns:
        List of device comparison data
    """
    # Parse device_ids
    try:
        ids_list = [int(id.strip()) for id in device_ids.split(",")]
    except ValueError:
        return {"error": "Invalid device IDs format"}
    
    return await AnalyticsService.get_device_comparison(
        db=db, device_ids=ids_list, start_time=start_time, end_time=end_time
    )


@router.get("/downtime/{device_id}")
async def get_downtime_report(
    device_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get downtime report for a device.
    
    Args:
        device_id: Device ID
        start_time: Start time
        end_time: End time
        db: Database session
        
    Returns:
        Downtime report
    """
    return await AnalyticsService.get_downtime_report(
        db=db, device_id=device_id, start_time=start_time, end_time=end_time
    )


@router.get("/top-devices")
async def get_top_devices(
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    limit: int = Query(10, ge=1, le=50, description="Number of devices"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get top performing devices by metric.
    
    Args:
        start_time: Start time
        end_time: End time
        limit: Number of devices to return
        db: Database session
        
    Returns:
        List of top devices
    """
    return await AnalyticsService.get_top_devices(
        db=db, start_time=start_time, end_time=end_time, limit=limit, metric="19l"
    )
@router.get("/faults")
async def get_fault_report(
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get fault report for devices.
    
    Args:
        start_time: Start time
        end_time: End time
        device_id: Optional device ID filter
        db: Database session
        
    Returns:
        List of fault events
    """
    # Parse device_id if provided
    try:
        device_id_int = int(device_id)
    except ValueError:
        device_id = None
    
    return await AnalyticsService.get_fault_report(
        db=db, start_time=start_time, end_time=end_time, device_id=device_id
    )
