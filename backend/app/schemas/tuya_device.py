"""
Tuya Device Schemas - Pydantic models for validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


def sanitize_string(value: str) -> str:
    """Remove potential SQL injection characters and XSS patterns."""
    if not value:
        return value
    # Remove common SQL injection patterns
    dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_", "exec", "execute", "drop", "delete", "insert", "update", "script", "<", ">"]
    sanitized = value
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "")
    return sanitized.strip()


class TuyaDeviceBase(BaseModel):
    """Base Tuya device schema with common fields."""
    name: str
    device_id: str
    device_type: str = "SMART_PLUG"
    local_key: Optional[str] = None
    ip_address: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    is_enabled: bool = True
    
    @field_validator('name')
    def sanitize_name(cls, v: str) -> str:
        return sanitize_string(v)
    
    @field_validator('device_id')
    def sanitize_device_id(cls, v: str) -> str:
        return sanitize_string(v)


class TuyaDeviceCreate(TuyaDeviceBase):
    """Schema for creating a new Tuya device."""
    pass


class TuyaDeviceUpdate(BaseModel):
    """Schema for updating an existing Tuya device."""
    name: Optional[str] = None
    device_type: Optional[str] = None
    local_key: Optional[str] = None
    ip_address: Optional[str] = None
    is_enabled: Optional[bool] = None


class TuyaDeviceResponse(TuyaDeviceBase):
    """Schema for Tuya device response."""
    id: int
    is_online: bool
    power_state: bool
    last_seen_at: Optional[datetime] = None
    last_control_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TuyaDeviceListResponse(BaseModel):
    """Schema for list of Tuya devices."""
    items: List[TuyaDeviceResponse]
    total: int


class TuyaDeviceStatusResponse(BaseModel):
    """Schema for device status response."""
    id: int
    device_id: str
    name: str
    is_online: bool
    power_state: bool
    last_seen_at: Optional[datetime] = None
    dps: dict = {}


class TuyaDeviceControlRequest(BaseModel):
    """Schema for device control request."""
    action: str  # 'turn_on', 'turn_off', 'toggle', 'restart'


class TuyaDeviceControlResponse(BaseModel):
    """Schema for device control response."""
    success: bool
    power_state: bool
    message: str
    action: Optional[str] = None
    strategy: Optional[str] = None  # 'countdown', 'relay_status', 'sequential'
    delay_seconds: Optional[int] = None
    turn_on_failed: Optional[bool] = None  # True if sequential restart failed to turn device back on


class TuyaConfigRequest(BaseModel):
    """Schema for Tuya Cloud configuration."""
    access_id: str
    access_secret: str
    api_region: str = "eu"  # us, eu, cn, in


class TuyaConfigResponse(BaseModel):
    """Schema for Tuya Cloud configuration response."""
    access_id: str
    api_region: str
    has_access_secret: bool
    is_configured: bool


class TuyaDeviceControlLogBase(BaseModel):
    """Base schema for device control log."""
    tuya_device_id: int
    action: str
    previous_state: bool
    new_state: Optional[bool] = None
    success: bool
    error_message: Optional[str] = None
    performed_by: Optional[str] = None


class TuyaDeviceControlLogCreate(TuyaDeviceControlLogBase):
    """Schema for creating a control log entry."""
    pass


class TuyaDeviceControlLogResponse(TuyaDeviceControlLogBase):
    """Schema for control log response."""
    id: int
    performed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TuyaDeviceControlHistoryResponse(BaseModel):
    """Schema for paginated control history."""
    items: List[TuyaDeviceControlLogResponse]
    total: int
    page: int = 1
    page_size: int = 50


class TuyaDeviceDetailsResponse(TuyaDeviceResponse):
    """Schema for device details with recent control logs."""
    recent_controls: List[TuyaDeviceControlLogResponse] = []
    total_controls: int = 0
    successful_controls: int = 0
    failed_controls: int = 0
