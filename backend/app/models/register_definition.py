"""
Sumatic Modern IoT - Register Definition Model
Modbus register definitions and metadata.
"""
from typing import Optional

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RegisterDefinition(Base):
    """
    Register definition model for Modbus register metadata.
    Defines function code, register number, name, and data type.
    """

    __tablename__ = "register_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fc: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Function code (3=Holding, 4=Input)
    reg: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Register number
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # uint16, int16, uint32, etc.
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # TL, saat, adet
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<RegisterDefinition(fc={self.fc}, reg={self.reg}, name='{self.name}')>"
