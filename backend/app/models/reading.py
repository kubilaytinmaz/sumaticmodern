"""
Sumatic Modern IoT - Device Reading Model (Counter-Only Optimized)
Time-series device readings model - ONLY 19L and 5L counters.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeviceReading(Base):
    """
    Device reading model for time-series data - COUNTER ONLY.
    Optimized to store only 19L and 5L counter values.
    Compatible with both SQLite and PostgreSQL.
    """

    __tablename__ = "device_readings"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key to devices
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Reading timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Counter metrics - ONLY THESE TWO FIELDS
    counter_19l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    counter_5l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Device status for this reading - ONLINE, OFFLINE, or PARTIAL
    # ONLINE: Both counters have valid values
    # OFFLINE: Both counters are NULL (device didn't send data)
    # PARTIAL: Only one counter has a value
    status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    def __repr__(self) -> str:
        return f"<DeviceReading(device_id={self.device_id}, timestamp='{self.timestamp}', 19L={self.counter_19l}, 5L={self.counter_5l}, status={self.status})>"
