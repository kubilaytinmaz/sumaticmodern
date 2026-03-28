"""
Sumatic Modern IoT - SQLAlchemy Models
"""
from app.models.user import User
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.device_status import DeviceHourlyStatus, DeviceStatusSnapshot
from app.models.register_definition import RegisterDefinition

__all__ = [
    "User",
    "Device",
    "DeviceReading",
    "DeviceHourlyStatus",
    "DeviceStatusSnapshot",
    "RegisterDefinition",
]
