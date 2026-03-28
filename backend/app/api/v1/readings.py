"""
Sumatic Modern IoT - Readings Endpoints
Query endpoints for device readings.
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams
from app.database import get_db
from app.schemas.reading import (
    ReadingResponse,
    ReadingListResponse,
    ReadingQuery,
    ReadingSummary,
)
from app.services.reading_service import ReadingService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/readings", tags=["Readings"])


@router.get("", response_model=ReadingListResponse)
async def query_readings(
    pagination: PaginationParams = Depends(),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    include_spikes: bool = Query(False, description="Include spike readings"),
    fault_only: bool = Query(False, description="Only show fault readings"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Query device readings with filtering and pagination.
    
    Args:
        pagination: Pagination parameters
        device_id: Filter by device ID
        start_time: Start time filter
        end_time: End time filter
        include_spikes: Include spike readings
        fault_only: Only show fault readings
        db: Database session
        
    Returns:
        Paginated readings list
    """
    query = ReadingQuery(
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        include_spikes=include_spikes,
        fault_only=fault_only,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    
    readings, total = await ReadingService.get_readings(db=db, query=query)
    
    return pagination.paginate_response(readings, total)


@router.get("/latest")
async def get_latest_readings(
    device_ids: Optional[str] = Query(
        None, 
        description="Comma-separated device IDs (optional, all if not provided)"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get latest reading for each device.
    
    Args:
        device_ids: Optional comma-separated device IDs
        db: Database session
        
    Returns:
        Dict mapping device_id to latest reading
    """
    # Parse device_ids if provided
    ids_list = None
    if device_ids:
        try:
            ids_list = [int(id.strip()) for id in device_ids.split(",")]
        except ValueError:
            ids_list = None
    
    latest = await ReadingService.get_latest_readings(
        db=db, device_ids=ids_list, use_cache=True
    )
    
    return {
        "readings": latest,
        "count": len(latest),
    }


@router.get("/device/{device_id}", response_model=ReadingListResponse)
async def get_device_readings(
    device_id: int,
    pagination: PaginationParams = Depends(),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    include_spikes: bool = Query(False, description="Include spike readings"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get readings for a specific device.
    
    Args:
        device_id: Device ID
        pagination: Pagination parameters
        start_time: Start time filter
        end_time: End time filter
        include_spikes: Include spike readings
        db: Database session
        
    Returns:
        Paginated readings for the device
    """
    # Use a higher limit for device-specific queries
    limit = min(pagination.page_size, 500)
    
    readings = await ReadingService.get_device_readings(
        db=db,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        include_spikes=include_spikes,
    )
    
    return pagination.paginate_response(readings, len(readings))


@router.get("/device/{device_id}/summary", response_model=ReadingSummary)
async def get_device_reading_summary(
    device_id: int,
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    db: AsyncSession = Depends(get_db),
) -> ReadingSummary:
    """
    Get reading summary for a device in a time range.
    
    Args:
        device_id: Device ID
        start_time: Start time
        end_time: End time
        db: Database session
        
    Returns:
        Reading summary with deltas
    """
    return await ReadingService.get_reading_summary(
        db=db,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/timerange")
async def get_readings_by_timerange(
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    device_ids: Optional[str] = Query(
        None, 
        description="Comma-separated device IDs (optional)"
    ),
    interval_minutes: int = Query(10, ge=1, le=60, description="Aggregation interval"),
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get aggregated readings by time interval.
    Useful for charts and time-series visualization.
    
    Args:
        start_time: Start time
        end_time: End time
        device_ids: Optional comma-separated device IDs
        interval_minutes: Aggregation interval in minutes
        db: Database session
        
    Returns:
        List of aggregated readings
    """
    # Parse device_ids if provided
    ids_list = None
    if device_ids:
        try:
            ids_list = [int(id.strip()) for id in device_ids.split(",")]
        except ValueError:
            ids_list = None
    
    readings = await ReadingService.get_readings_by_timerange(
        db=db,
        start_time=start_time,
        end_time=end_time,
        device_ids=ids_list,
        interval_minutes=interval_minutes,
    )
    
    return readings
