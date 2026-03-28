"""
Sumatic Modern IoT - Auth Schemas
Pydantic schemas for authentication tokens.
"""
from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator


def sanitize_username(value: str) -> str:
    """
    Username'i sanitize eder - XSS ve injection saldırılarına karşı koruma.
    Sadece alfanumerik karakterlere izin verir.
    """
    if not value:
        return value
    # Sadece alfanumerik, underscore ve dash karakterlerine izin ver
    value = re.sub(r'[^\w\-]', '', value)
    # Fazla boşlukları kaldır
    value = ' '.join(value.split())
    return value.strip()


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # user_id
    username: str
    role: str
    exp: datetime
    iat: datetime
    jti: Optional[str] = None  # JWT ID for blacklisting


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator('username')
    @classmethod
    def sanitize_and_validate_username(cls, v: str) -> str:
        """Username'i sanitize et ve validate et."""
        v = sanitize_username(v)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username sadece harf, rakam, underscore ve dash içerebilir')
        return v.lower()


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    role: str


class RefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., min_length=1)


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Şifre güçlülüğünü kontrol et."""
        if len(v) < 8:
            raise ValueError('Şifre en az 8 karakter olmalıdır')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Şifre en az bir büyük harf içermelidir')
        if not re.search(r'[a-z]', v):
            raise ValueError('Şifre en az bir küçük harf içermelidir')
        if not re.search(r'\d', v):
            raise ValueError('Şifre en az bir rakam içermelidir')
        return v
