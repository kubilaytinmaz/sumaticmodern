"""
Sumatic Modern IoT - Tuya Device Control Log Model
Tracks all control actions (on/off/toggle) performed on Tuya devices.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TuyaDeviceControlLog(Base):
    """Audit log for Tuya device control actions."""

    __tablename__ = "tuya_device_control_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tuya_device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tuya_devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # turn_on, turn_off, toggle
    previous_state: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_state: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship
    device = relationship("TuyaDevice", backref="control_logs")

    def __repr__(self) -> str:
        return f"<TuyaDeviceControlLog(id={self.id}, device_id={self.tuya_device_id}, action='{self.action}', success={self.success})>"
