"""
Sumatic Modern IoT - Device Status Model
Track device online/offline status history.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeviceHourlyStatus(Base):
    """
    Device hourly status tracking model.
    Records online/offline status for each hour of the day.
    """
    
    __tablename__ = "device_hourly_status"
    
    # Unique constraint: one record per device per hour
    __table_args__ = (
        UniqueConstraint('device_id', 'hour_start', name='uq_device_hour'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    hour_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )  # Hour start time (e.g., 2026-03-27 00:00:00)
    hour_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )  # Hour end time (e.g., 2026-03-27 00:59:59)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # ONLINE, OFFLINE, PARTIAL
    online_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )  # Minutes online during this hour (0-60)
    offline_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )  # Minutes offline during this hour (0-60)
    data_points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )  # Number of data readings received during this hour
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )
    
    def __repr__(self) -> str:
        return f"<DeviceHourlyStatus(device_id={self.device_id}, hour='{self.hour_start}', status='{self.status}')>"


class DeviceStatusSnapshot(Base):
    """
    Device status snapshot model for 10-minute interval tracking.
    Records online/offline status every 10 minutes.
    """
    
    __tablename__ = "device_status_snapshots"
    
    # Unique constraint: one record per device per 10-minute slot
    __table_args__ = (
        UniqueConstraint('device_id', 'snapshot_time', name='uq_device_snapshot'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )  # Snapshot time (e.g., 2026-03-27 12:10:00)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # ONLINE, OFFLINE
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )  # Last time device was seen before this snapshot
    data_received: Mapped[bool] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )  # Whether data was received in this 10-minute window (1=yes, 0=no)
    null_values_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )  # Number of null readings in this window
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now()
    )
    
    def __repr__(self) -> str:
        return f"<DeviceStatusSnapshot(device_id={self.device_id}, time='{self.snapshot_time}', status='{self.status}')>"
