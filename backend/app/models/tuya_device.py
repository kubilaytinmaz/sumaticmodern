"""
Sumatic Modern IoT - Tuya Device Model
Smart plug and IoT device management for Tuya Cloud integration.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TuyaDevice(Base):
    """Tuya smart device model for cloud-connected IoT devices."""

    __tablename__ = "tuya_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), default="plug", nullable=False)
    local_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Device state
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    power_state: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # on/off
    
    # Monitoring
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    last_control_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Additional metadata
    product_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<TuyaDevice(id={self.id}, device_id='{self.device_id}', name='{self.name}', online={self.is_online})>"
