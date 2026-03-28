"""
Sumatic Modern IoT - Device Schemas
Pydantic schemas for device validation and serialization.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
import re

from pydantic import BaseModel, Field, field_validator


def sanitize_string(value: str) -> str:
    """
    String değerini sanitize eder - XSS ve injection saldırılarına karşı koruma.
    - HTML tag'lerini temizler
    - Kontrol karakterlerini temizler
    - Fazla boşlukları kaldırır
    """
    if not value:
        return value
    # HTML tag'lerini temizle
    value = re.sub(r'<[^>]*>', '', value)
    # Kontrol karakterlerini temizle (yeni satır hariç)
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    # Fazla boşlukları kaldır
    value = ' '.join(value.split())
    return value.strip()


def validate_device_code(value: str) -> str:
    """Device code validation - sadece alfanumerik ve belirli karakterlere izin verir."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', value):
        raise ValueError('Device code sadece harf, rakam, underscore ve dash içerebilir')
    return value.upper()


def validate_modem_id(value: str) -> str:
    """Modem ID validation - hexadecimal format kontrolü."""
    if not re.match(r'^[0-9a-fA-F]+$', value):
        raise ValueError('Modem ID hexadecimal formatında olmalıdır')
    return value.upper()


class DeviceBase(BaseModel):
    """Base device schema with common fields."""

    device_code: str = Field(..., min_length=1, max_length=50)
    modem_id: str = Field(..., min_length=1, max_length=8)
    device_addr: int = Field(..., ge=1, le=247)
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    method_no: int = Field(default=0, ge=0)

    @field_validator('device_code')
    @classmethod
    def sanitize_device_code(cls, v: str) -> str:
        """Device code'u sanitize et ve validate et."""
        v = sanitize_string(v)
        return validate_device_code(v)

    @field_validator('modem_id')
    @classmethod
    def sanitize_modem_id(cls, v: str) -> str:
        """Modem ID'yi sanitize et ve validate et."""
        v = sanitize_string(v)
        return validate_modem_id(v)

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Device name'i sanitize et."""
        return sanitize_string(v)

    @field_validator('location')
    @classmethod
    def sanitize_location(cls, v: Optional[str]) -> Optional[str]:
        """Location bilgisini sanitize et."""
        if v is None:
            return v
        return sanitize_string(v)


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""

    reg_offset_json: Dict[str, Any] = Field(default_factory=dict)
    alias_json: Dict[str, Any] = Field(default_factory=dict)
    skip_raw_json: List[int] = Field(default_factory=list)
    is_enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceUpdate(BaseModel):
    """Schema for updating an existing device."""

    device_code: Optional[str] = Field(None, min_length=1, max_length=50)
    modem_id: Optional[str] = Field(None, min_length=1, max_length=8)
    device_addr: Optional[int] = Field(None, ge=1, le=247)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    method_no: Optional[int] = Field(None, ge=0)
    reg_offset_json: Optional[Dict[str, Any]] = None
    alias_json: Optional[Dict[str, Any]] = None
    skip_raw_json: Optional[List[int]] = None
    is_enabled: Optional[bool] = None
    is_pending: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class DeviceResponse(DeviceBase):
    """Schema for device response."""

    id: int
    reg_offset_json: Dict[str, Any]
    alias_json: Dict[str, Any]
    skip_raw_json: List[Any]
    is_enabled: bool
    is_pending: bool
    last_seen_at: Optional[datetime]
    device_meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    status: Optional[str] = None  # ONLINE, OFFLINE, PENDING - computed field

    model_config = {
        "from_attributes": True,
        "exclude": {"metadata"}
    }


class DeviceListResponse(BaseModel):
    """Schema for paginated device list response."""

    items: List[DeviceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DeviceStatusResponse(BaseModel):
    """Schema for device status response."""

    device_id: int
    status: str  # ONLINE, OFFLINE, PENDING
    last_seen_at: Optional[datetime]
    offline_since: Optional[datetime]
    offline_duration_seconds: Optional[int]
