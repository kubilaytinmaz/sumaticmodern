"""
Sumatic Modern IoT - Devices Endpoints
CRUD endpoints for device management.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PaginationParams
from app.database import get_db
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    DeviceStatusResponse,
)
from app.services.device_service import DeviceService
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    pagination: PaginationParams = Depends(),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    is_pending: Optional[bool] = Query(None, description="Filter by pending status"),
    modem_id: Optional[str] = Query(None, description="Filter by modem ID"),
    search: Optional[str] = Query(None, description="Search in code, name, location"),
    db: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """
    List all devices with pagination and filtering.
    
    Args:
        pagination: Pagination parameters
        is_enabled: Filter by enabled status
        is_pending: Filter by pending status
        modem_id: Filter by modem ID
        search: Search text
        db: Database session
        
    Returns:
        Paginated device list
    """
    devices, total = await DeviceService.list_devices(
        db=db,
        skip=pagination.offset,
        limit=pagination.limit,
        is_enabled=is_enabled,
        is_pending=is_pending,
        modem_id=modem_id,
        search=search,
    )
    
    # Convert SQLAlchemy models to Pydantic schemas with computed status
    settings = get_settings()
    device_responses = []
    for d in devices:
        device_dict = d.__dict__.copy()
        # Compute status field
        if d.is_pending:
            status = "PENDING"
        elif d.last_seen_at:
            now_utc = datetime.now(timezone.utc)
            last_seen_utc = d.last_seen_at
            if hasattr(last_seen_utc, 'tzinfo') and last_seen_utc.tzinfo is not None:
                if last_seen_utc.tzinfo != timezone.utc:
                    last_seen_utc = last_seen_utc.astimezone(timezone.utc)
            else:
                last_seen_utc = last_seen_utc.replace(tzinfo=timezone.utc)
            
            if (now_utc - last_seen_utc).total_seconds() < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS:
                status = "ONLINE"
            else:
                status = "OFFLINE"
        else:
            status = "OFFLINE"
        
        device_dict['status'] = status
        device_responses.append(DeviceResponse.model_validate(device_dict))
    
    return DeviceListResponse(
        items=device_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total > 0 else 0,
    )


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """
    Create a new device. Admin only.
    
    Args:
        device_data: Device creation data
        db: Database session
        
    Returns:
        Created device
    """
    device = await DeviceService.create_device(db=db, device_data=device_data)
    logger.info(f"Device created: {device.device_code}")
    
    # Compute status field
    settings = get_settings()
    device_dict = device.__dict__.copy()
    if device.is_pending:
        status = "PENDING"
    elif device.last_seen_at:
        now_utc = datetime.now(timezone.utc)
        last_seen_utc = device.last_seen_at
        if hasattr(last_seen_utc, 'tzinfo') and last_seen_utc.tzinfo is not None:
            if last_seen_utc.tzinfo != timezone.utc:
                last_seen_utc = last_seen_utc.astimezone(timezone.utc)
        else:
            last_seen_utc = last_seen_utc.replace(tzinfo=timezone.utc)
        
        if (now_utc - last_seen_utc).total_seconds() < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS:
            status = "ONLINE"
        else:
            status = "OFFLINE"
    else:
        status = "OFFLINE"
    
    device_dict['status'] = status
    return DeviceResponse.model_validate(device_dict)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """
    Get device details by ID.
    
    Args:
        device_id: Device ID
        db: Database session
        
    Returns:
        Device details
    """
    device = await DeviceService.get_device_by_id(db=db, device_id=device_id)
    
    # Compute status field
    settings = get_settings()
    device_dict = device.__dict__.copy()
    if device.is_pending:
        status = "PENDING"
    elif device.last_seen_at:
        now_utc = datetime.now(timezone.utc)
        last_seen_utc = device.last_seen_at
        if hasattr(last_seen_utc, 'tzinfo') and last_seen_utc.tzinfo is not None:
            if last_seen_utc.tzinfo != timezone.utc:
                last_seen_utc = last_seen_utc.astimezone(timezone.utc)
        else:
            last_seen_utc = last_seen_utc.replace(tzinfo=timezone.utc)
        
        if (now_utc - last_seen_utc).total_seconds() < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS:
            status = "ONLINE"
        else:
            status = "OFFLINE"
    else:
        status = "OFFLINE"
    
    device_dict['status'] = status
    return DeviceResponse.model_validate(device_dict)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    """
    Update device. Admin only.
    
    Args:
        device_id: Device ID
        device_data: Device update data
        db: Database session
        
    Returns:
        Updated device
    """
    device = await DeviceService.update_device(
        db=db, device_id=device_id, device_data=device_data
    )
    logger.info(f"Device updated: {device.device_code}")
    
    # Compute status field
    settings = get_settings()
    device_dict = device.__dict__.copy()
    if device.is_pending:
        status = "PENDING"
    elif device.last_seen_at:
        now_utc = datetime.now(timezone.utc)
        last_seen_utc = device.last_seen_at
        if hasattr(last_seen_utc, 'tzinfo') and last_seen_utc.tzinfo is not None:
            if last_seen_utc.tzinfo != timezone.utc:
                last_seen_utc = last_seen_utc.astimezone(timezone.utc)
        else:
            last_seen_utc = last_seen_utc.replace(tzinfo=timezone.utc)
        
        if (now_utc - last_seen_utc).total_seconds() < settings.DEVICE_OFFLINE_THRESHOLD_SECONDS:
            status = "ONLINE"
        else:
            status = "OFFLINE"
    else:
        status = "OFFLINE"
    
    device_dict['status'] = status
    return DeviceResponse.model_validate(device_dict)


@router.delete("/{device_id}")
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete device (soft delete). Admin only.
    
    Args:
        device_id: Device ID
        db: Database session
        
    Returns:
        Success message
    """
    await DeviceService.delete_device(db=db, device_id=device_id)
    logger.info(f"Device deleted (soft): id={device_id}")
    return {"message": f"Device {device_id} has been disabled"}


@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(
    device_id: int,
    db: AsyncSession = Depends(get_db),
) -> DeviceStatusResponse:
    """
    Get device online/offline status.
    
    Args:
        device_id: Device ID
        db: Database session
        
    Returns:
        Device status information
    """
    return await DeviceService.get_device_status(db=db, device_id=device_id)
