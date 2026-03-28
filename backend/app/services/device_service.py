"""
Sumatic Modern IoT - Device Service
Business logic for device management operations.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.reading import DeviceReading
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceStatusResponse
from app.core.exceptions import NotFoundException, ConflictException
from app.config import get_settings
from app.redis_client import cache_delete_pattern

settings = get_settings()


class DeviceService:
    """Service for device-related operations."""

    @staticmethod
    async def create_device(db: AsyncSession, device_data: DeviceCreate) -> Device:
        """
        Create a new device.
        
        Args:
            db: Database session
            device_data: Device creation data
            
        Returns:
            Created device
            
        Raises:
            ConflictException: If device_code or (modem_id, device_addr) already exists
        """
        # Check for duplicate device_code
        result = await db.execute(
            select(Device).where(Device.device_code == device_data.device_code)
        )
        if result.scalar_one_or_none():
            raise ConflictException(
                f"Device with code '{device_data.device_code}' already exists"
            )
        
        # Check for duplicate modem_id + device_addr
        result = await db.execute(
            select(Device).where(
                and_(
                    Device.modem_id == device_data.modem_id,
                    Device.device_addr == device_data.device_addr,
                )
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException(
                f"Device with modem_id '{device_data.modem_id}' "
                f"and address {device_data.device_addr} already exists"
            )
        
        # Create device
        device = Device(**device_data.model_dump())
        db.add(device)
        await db.flush()
        await db.refresh(device)
        
        # Clear device cache
        await cache_delete_pattern("device:*")
        
        return device

    @staticmethod
    async def get_device_by_id(db: AsyncSession, device_id: int) -> Device:
        """
        Get device by ID.
        
        Args:
            db: Database session
            device_id: Device ID
            
        Returns:
            Device instance
            
        Raises:
            NotFoundException: If device not found
        """
        result = await db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        
        if not device:
            raise NotFoundException(f"Device with id {device_id} not found")
        
        return device

    @staticmethod
    async def get_device_by_code(db: AsyncSession, device_code: str) -> Optional[Device]:
        """Get device by device_code."""
        result = await db.execute(
            select(Device).where(Device.device_code == device_code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_devices(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        is_enabled: Optional[bool] = None,
        is_pending: Optional[bool] = None,
        modem_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Device], int]:
        """
        List devices with filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_enabled: Filter by enabled status
            is_pending: Filter by pending status
            modem_id: Filter by modem_id
            search: Search in device_code, name, or location
            
        Returns:
            Tuple of (devices list, total count)
        """
        query = select(Device)
        count_query = select(func.count()).select_from(Device)
        
        # Build filters
        filters = []
        
        if is_enabled is not None:
            filters.append(Device.is_enabled == is_enabled)
        
        if is_pending is not None:
            filters.append(Device.is_pending == is_pending)
        
        if modem_id:
            filters.append(Device.modem_id == modem_id)
        
        if search:
            search_filter = or_(
                Device.device_code.ilike(f"%{search}%"),
                Device.name.ilike(f"%{search}%"),
                Device.location.ilike(f"%{search}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total = await db.scalar(count_query)
        
        # Get paginated results
        query = query.order_by(desc(Device.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        devices = result.scalars().all()
        
        return list(devices), total or 0

    @staticmethod
    async def update_device(
        db: AsyncSession, device_id: int, device_data: DeviceUpdate
    ) -> Device:
        """
        Update device.
        
        Args:
            db: Database session
            device_id: Device ID
            device_data: Device update data
            
        Returns:
            Updated device
            
        Raises:
            NotFoundException: If device not found
            ConflictException: If update causes conflict
        """
        device = await DeviceService.get_device_by_id(db, device_id)
        
        # Check for conflicts if updating device_code
        if device_data.device_code and device_data.device_code != device.device_code:
            result = await db.execute(
                select(Device).where(Device.device_code == device_data.device_code)
            )
            if result.scalar_one_or_none():
                raise ConflictException(
                    f"Device with code '{device_data.device_code}' already exists"
                )
        
        # Check for conflicts if updating modem_id or device_addr
        if device_data.modem_id or device_data.device_addr:
            new_modem_id = device_data.modem_id or device.modem_id
            new_addr = device_data.device_addr or device.device_addr
            
            if new_modem_id != device.modem_id or new_addr != device.device_addr:
                result = await db.execute(
                    select(Device).where(
                        and_(
                            Device.modem_id == new_modem_id,
                            Device.device_addr == new_addr,
                            Device.id != device_id,
                        )
                    )
                )
                if result.scalar_one_or_none():
                    raise ConflictException(
                        f"Device with modem_id '{new_modem_id}' "
                        f"and address {new_addr} already exists"
                    )
        
        # Update fields
        for field, value in device_data.model_dump(exclude_unset=True).items():
            setattr(device, field, value)
        
        device.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(device)
        
        # Clear device cache
        await cache_delete_pattern(f"device:*:{device_id}")
        
        return device

    @staticmethod
    async def delete_device(db: AsyncSession, device_id: int) -> None:
        """
        Delete device (soft delete by disabling).
        
        Args:
            db: Database session
            device_id: Device ID
            
        Raises:
            NotFoundException: If device not found
        """
        device = await DeviceService.get_device_by_id(db, device_id)
        device.is_enabled = False
        device.updated_at = datetime.now(timezone.utc)
        await db.flush()
        
        # Clear device cache
        await cache_delete_pattern(f"device:*:{device_id}")

    @staticmethod
    async def get_device_status(
        db: AsyncSession, device_id: int
    ) -> DeviceStatusResponse:
        """
        Get device online/offline status.
        
        Args:
            db: Database session
            device_id: Device ID
            
        Returns:
            Device status information
        """
        device = await DeviceService.get_device_by_id(db, device_id)
        
        # Check if device has been seen
        if not device.last_seen_at:
            return DeviceStatusResponse(
                device_id=device_id,
                status="PENDING" if device.is_pending else "OFFLINE",
                last_seen_at=None,
                offline_since=None,
                offline_duration_seconds=None,
            )
        
        # Calculate offline threshold using UTC timezone
        now_utc = datetime.now(timezone.utc)
        threshold = now_utc - timedelta(
            seconds=settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
        )
        
        # Convert last_seen_at to UTC for comparison
        last_seen_utc = device.last_seen_at
        if last_seen_utc:
            if hasattr(last_seen_utc, 'tzinfo') and last_seen_utc.tzinfo is not None:
                # Timezone-aware: convert to UTC
                if last_seen_utc.tzinfo != timezone.utc:
                    last_seen_utc = last_seen_utc.astimezone(timezone.utc)
            else:
                # Naive datetime: assume it's UTC
                last_seen_utc = last_seen_utc.replace(tzinfo=timezone.utc)
        
        if last_seen_utc and last_seen_utc >= threshold:
            # Device is ONLINE
            return DeviceStatusResponse(
                device_id=device_id,
                status="ONLINE",
                last_seen_at=device.last_seen_at,
                offline_since=None,
                offline_duration_seconds=None,
            )
        
        # Device is OFFLINE
        offline_duration = int((now_utc - last_seen_utc).total_seconds()) if last_seen_utc else 0
        
        return DeviceStatusResponse(
            device_id=device_id,
            status="OFFLINE",
            last_seen_at=device.last_seen_at,
            offline_since=device.last_seen_at,
            offline_duration_seconds=offline_duration,
        )

    @staticmethod
    async def update_last_seen(
        db: AsyncSession, device_id: int, timestamp: Optional[datetime] = None
    ) -> None:
        """
        Update device last_seen_at timestamp.
        
        Args:
            db: Database session
            device_id: Device ID
            timestamp: Timestamp (default: now)
        """
        device = await DeviceService.get_device_by_id(db, device_id)
        device.last_seen_at = timestamp or datetime.now(timezone.utc)
        device.is_pending = False
        await db.flush()

    @staticmethod
    async def get_online_devices(db: AsyncSession) -> List[Device]:
        """Get list of currently online devices."""
        threshold = datetime.now(timezone.utc) - timedelta(
            seconds=settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
        )
        
        result = await db.execute(
            select(Device).where(
                and_(
                    Device.is_enabled == True,
                    Device.last_seen_at >= threshold,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_offline_devices(db: AsyncSession) -> List[Device]:
        """Get list of currently offline devices."""
        threshold = datetime.now(timezone.utc) - timedelta(
            seconds=settings.DEVICE_OFFLINE_THRESHOLD_SECONDS
        )
        
        result = await db.execute(
            select(Device).where(
                and_(
                    Device.is_enabled == True,
                    or_(
                        Device.last_seen_at < threshold,
                        Device.last_seen_at.is_(None),
                    ),
                )
            )
        )
        return list(result.scalars().all())

