"""
Sumatic Modern IoT - Pydantic Schemas
"""
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
)
from app.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
)
from app.schemas.reading import (
    ReadingResponse,
    ReadingQuery,
    ReadingListResponse,
)
from app.schemas.auth import (
    Token,
    TokenPayload,
    LoginRequest,
    LoginResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    # Device schemas
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceListResponse",
    # Reading schemas
    "ReadingResponse",
    "ReadingQuery",
    "ReadingListResponse",
    # Auth schemas
    "Token",
    "TokenPayload",
    "LoginRequest",
    "LoginResponse",
]
