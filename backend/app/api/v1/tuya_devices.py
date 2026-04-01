"""
Sumatic Modern IoT - Tuya Devices Endpoints
API endpoints for managing and controlling Tuya smart devices.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.tuya_device import (
    TuyaDeviceCreate,
    TuyaDeviceUpdate,
    TuyaDeviceResponse,
    TuyaDeviceListResponse,
    TuyaDeviceStatusResponse,
    TuyaDeviceControlRequest,
    TuyaDeviceControlResponse,
    TuyaDeviceControlLogResponse,
    TuyaDeviceControlHistoryResponse,
    TuyaDeviceDetailsResponse,
    TuyaConfigRequest,
    TuyaConfigResponse,
)
from app.services.tuya_service import get_tuya_service, TuyaService, TuyaCloudError
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tuya-devices", tags=["Tuya Devices"])


# Static routes must come BEFORE dynamic routes like /{device_id}
# to avoid path conflicts (e.g., "config" being interpreted as device_id)

@router.get("/discover")
async def discover_tuya_devices():
    """Discover all devices from Tuya Cloud."""
    tuya_service = get_tuya_service()
    try:
        devices = await tuya_service.discover_devices()
        return {"devices": devices, "total": len(devices)}
    except TuyaCloudError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/config", response_model=TuyaConfigResponse)
async def get_tuya_config():
    """Get current Tuya Cloud configuration (without secret)."""
    tuya_service = get_tuya_service()
    status = tuya_service.get_status()
    return TuyaConfigResponse(
        access_id=status.get("access_id", ""),
        api_region=status.get("api_region", "eu"),
        has_access_secret=status.get("has_credentials", False),
        is_configured=status.get("has_credentials", False),
    )


@router.post("/config", response_model=TuyaConfigResponse)
async def update_tuya_config(config: TuyaConfigRequest):
    """Update Tuya Cloud configuration and reinitialize the service."""
    import traceback
    tuya_service = get_tuya_service()
    try:
        await tuya_service.update_config(config.access_id, config.access_secret, config.api_region)
        return TuyaConfigResponse(
            access_id=config.access_id,
            api_region=config.api_region,
            has_access_secret=True,
            is_configured=True,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_tuya_service_status():
    """Get Tuya service connection status."""
    tuya_service = get_tuya_service()
    return tuya_service.get_status()


@router.get("", response_model=TuyaDeviceListResponse)
async def list_tuya_devices(
    db: AsyncSession = Depends(get_db),
):
    """List all Tuya smart devices."""
    tuya_service = get_tuya_service()
    devices = await tuya_service.get_devices(db)
    return TuyaDeviceListResponse(
        items=[TuyaDeviceResponse.model_validate(d.__dict__) for d in devices],
        total=len(devices),
    )


@router.post("", response_model=TuyaDeviceResponse, status_code=201)
async def create_tuya_device(
    device_data: TuyaDeviceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new Tuya device to the system."""
    tuya_service = get_tuya_service()
    
    # Check if device already exists
    existing = await tuya_service.get_device_by_tuya_id(db, device_data.device_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Device with ID '{device_data.device_id}' already exists"
        )
    
    device = await tuya_service.create_device(db, device_data.model_dump())
    return TuyaDeviceResponse.model_validate(device.__dict__)


# Dynamic routes with path parameters come AFTER static routes
@router.get("/{device_id}", response_model=TuyaDeviceResponse)
async def get_tuya_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific Tuya device by internal ID."""
    tuya_service = get_tuya_service()
    device = await tuya_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return TuyaDeviceResponse.model_validate(device.__dict__)


@router.put("/{device_id}", response_model=TuyaDeviceResponse)
async def update_tuya_device(
    device_id: int,
    device_data: TuyaDeviceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a Tuya device."""
    tuya_service = get_tuya_service()
    device = await tuya_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_dict = device_data.model_dump(exclude_none=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    device = await tuya_service.update_device(db, device, update_dict)
    return TuyaDeviceResponse.model_validate(device.__dict__)


@router.delete("/{device_id}")
async def delete_tuya_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a Tuya device from the system."""
    tuya_service = get_tuya_service()
    device = await tuya_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await tuya_service.delete_device(db, device)
    return {"message": f"Device '{device.name}' deleted successfully"}


@router.get("/{device_id}/details")
async def get_tuya_device_details(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed device info with recent control history and stats."""
    tuya_service = get_tuya_service()
    
    try:
        details = await tuya_service.get_device_details(db, device_id)
        device = details["device"]
        
        return {
            "id": device.id,
            "device_id": device.device_id,
            "name": device.name,
            "device_type": device.device_type,
            "local_key": device.local_key,
            "ip_address": device.ip_address,
            "is_enabled": device.is_enabled,
            "is_online": device.is_online,
            "power_state": device.power_state,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
            "last_control_at": device.last_control_at.isoformat() if device.last_control_at else None,
            "product_id": device.product_id,
            "product_name": device.product_name,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "updated_at": device.updated_at.isoformat() if device.updated_at else None,
            "recent_controls": [
                {
                    "id": log.id,
                    "tuya_device_id": log.tuya_device_id,
                    "action": log.action,
                    "previous_state": log.previous_state,
                    "new_state": log.new_state,
                    "success": log.success,
                    "error_message": log.error_message,
                    "performed_by": log.performed_by,
                    "performed_at": log.performed_at.isoformat() if log.performed_at else None,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in details["recent_controls"]
            ],
            "total_controls": details["total_controls"],
            "successful_controls": details["successful_controls"],
            "failed_controls": details["failed_controls"],
        }
    except TuyaCloudError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{device_id}/control-history")
async def get_tuya_device_control_history(
    device_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated control history for a device."""
    tuya_service = get_tuya_service()
    
    try:
        history = await tuya_service.get_control_history(db, device_id, page, page_size)
        
        return {
            "items": [
                {
                    "id": log.id,
                    "tuya_device_id": log.tuya_device_id,
                    "action": log.action,
                    "previous_state": log.previous_state,
                    "new_state": log.new_state,
                    "success": log.success,
                    "error_message": log.error_message,
                    "performed_by": log.performed_by,
                    "performed_at": log.performed_at.isoformat() if log.performed_at else None,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in history["items"]
            ],
            "total": history["total"],
            "page": history["page"],
            "page_size": history["page_size"],
        }
    except TuyaCloudError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{device_id}/control", response_model=TuyaDeviceControlResponse)
async def control_tuya_device(
    device_id: int,
    control_request: TuyaDeviceControlRequest,
    db: AsyncSession = Depends(get_db),
):
    """Control a Tuya device (turn on, turn off, or toggle)."""
    tuya_service = get_tuya_service()
    
    try:
        result = await tuya_service.control_device(db, device_id, control_request.action)
        
        # Get updated device for response
        device = await tuya_service.get_device(db, device_id)
        
        return TuyaDeviceControlResponse(
            id=device.id,
            device_id=device.device_id,
            name=device.name,
            action=control_request.action,
            success=result["success"],
            power_state=result["power_state"],
            message=result["message"],
        )
    except TuyaCloudError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{device_id}/status", response_model=TuyaDeviceStatusResponse)
async def get_tuya_device_status(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get real-time status of a Tuya device from cloud."""
    tuya_service = get_tuya_service()
    
    try:
        status = await tuya_service.get_device_status(db, device_id)
        return TuyaDeviceStatusResponse(
            id=status["id"],
            device_id=status["device_id"],
            name=status["name"],
            is_online=status["is_online"],
            power_state=status["power_state"],
            last_seen_at=status.get("last_seen_at"),
            last_control_at=status.get("last_control_at"),
        )
    except TuyaCloudError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/{device_id}/toggle", response_model=TuyaDeviceControlResponse)
async def toggle_tuya_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a Tuya device (shortcut for control with action=toggle)."""
    tuya_service = get_tuya_service()
    
    try:
        result = await tuya_service.control_device(db, device_id, "toggle")
        
        device = await tuya_service.get_device(db, device_id)
        
        return TuyaDeviceControlResponse(
            id=device.id,
            device_id=device.device_id,
            name=device.name,
            action="toggle",
            success=result["success"],
            power_state=result["power_state"],
            message=result["message"],
        )
    except TuyaCloudError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/{device_id}/restart", response_model=TuyaDeviceControlResponse)
async def restart_tuya_device(
    device_id: int,
    delay_seconds: int = Query(5, ge=2, le=30, description="Delay between off and on (seconds)"),
    force: bool = Query(False, description="Force restart even for network-critical devices"),
    db: AsyncSession = Depends(get_db),
):
    """
    Smart restart a Tuya device (turn off, wait, turn on).
    
    Automatically selects the best restart strategy:
    - **Countdown**: If device supports hardware timer (best for modem-connected devices)
    - **Relay Status**: If device supports power-on recovery
    - **Sequential**: Fallback method (turn off → sleep → turn on)
    
    **Warning**: Sequential restart will NOT work for devices that control the modem/router,
    because internet connectivity will be lost after turn_off and turn_on command won't reach the device.
    
    **Parameters**:
    - delay_seconds: Time to wait between off and on (2-30 seconds, default: 5)
    - force: Set to true to bypass network-critical device warnings
    
    **Response includes**:
    - strategy: Which restart method was used (countdown/relay_status/sequential)
    - delay_seconds: Actual delay used
    """
    tuya_service = get_tuya_service()
    
    try:
        result = await tuya_service.restart_device(
            db,
            device_id,
            delay_seconds=delay_seconds,
            force=force
        )
        
        return TuyaDeviceControlResponse(
            action="restart",
            success=result["success"],
            power_state=result["power_state"],
            message=result["message"],
            strategy=result.get("strategy"),
            delay_seconds=result.get("delay_seconds"),
        )
    except TuyaCloudError as e:
        raise HTTPException(status_code=503, detail=str(e))
