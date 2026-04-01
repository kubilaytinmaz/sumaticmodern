"""
Sumatic Modern IoT - Device Month Cycle Model
Cihaz aylık döngü takibi için model
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeviceMonthCycle(Base):
    """
    Cihaz aylık döngü modeli.
    Her cihazın her ay için sayaç sıfırlamalarına dayalı döngü kaydını tutar.
    """

    __tablename__ = "device_month_cycles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    cycle_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    cycle_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    start_counter_19l: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_counter_5l: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    end_counter_19l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_counter_5l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    total_revenue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
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
        return f"<DeviceMonthCycle(device_id={self.device_id}, year={self.year}, month={self.month}, revenue={self.total_revenue}, is_closed={self.is_closed})>"
