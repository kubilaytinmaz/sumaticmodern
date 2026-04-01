"""
Sumatic Modern IoT - Monthly Revenue Record Model
Aylık ciro kayıtları için model
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MonthlyRevenueRecord(Base):
    """
    Aylık ciro kayıt modeli.
    Her cihazın her ay için kapanış cirosunu tutar.
    """

    __tablename__ = "monthly_revenue_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    month_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    month_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    closing_counter_19l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    closing_counter_5l: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    total_revenue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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
    
    __table_args__ = (
        UniqueConstraint('device_id', 'year', 'month', name='unique_device_year_month'),
    )

    def __repr__(self) -> str:
        return f"<MonthlyRevenueRecord(device_id={self.device_id}, year={self.year}, month={self.month}, revenue={self.total_revenue}, is_closed={self.is_closed})>"
