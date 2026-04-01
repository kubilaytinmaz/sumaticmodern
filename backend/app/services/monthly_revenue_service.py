"""
Sumatic Modern IoT - Monthly Revenue Service
Aylık ciro takip ve yönetim servisi
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.device_month_cycle import DeviceMonthCycle
from app.models.monthly_revenue import MonthlyRevenueRecord
from app.core.exceptions import NotFoundException


class MonthlyRevenueService:
    """Aylık ciro yönetim servisi"""
    
    # Sıfırlama algılama eşik değerleri
    RESET_THRESHOLD = 5  # Sayaç değeri bu değerden azsa sıfırlama sayılır
    MIN_DAYS_BETWEEN_RESETS = 15  # Ard arda sıfırlamalar arası minimum gün
    RESET_DROP_PERCENTAGE = 0.9  # Önceki değerin %90'ından fazla düşüş sıfırlama sayılır
    
    @staticmethod
    async def detect_counter_reset(
        db: AsyncSession,
        device_id: int,
        counter_19l: int,
        counter_5l: int,
        timestamp: datetime
    ) -> bool:
        """
        Sayaç sıfırlamasını algıla
        
        Args:
            db: Veritabanı oturumu
            device_id: Cihaz ID
            counter_19l: 19L sayacı değeri
            counter_5l: 5L sayacı değeri
            timestamp: Okuma zamanı
            
        Returns:
            True if reset detected, False otherwise
        """
        # Her iki sayaç da 0'a yakın mı?
        if counter_19l > MonthlyRevenueService.RESET_THRESHOLD or counter_5l > MonthlyRevenueService.RESET_THRESHOLD:
            return False
        
        # Son okumayı getir
        last_reading_result = await db.execute(
            select(DeviceReading)
            .where(DeviceReading.device_id == device_id)
            .where(DeviceReading.counter_19l.isnot(None))
            .where(DeviceReading.counter_5l.isnot(None))
            .order_by(DeviceReading.timestamp.desc())
            .limit(1)
        )
        last_reading = last_reading_result.scalar_one_or_none()
        
        if not last_reading:
            # İlk okuma - sıfırlama değil, ilk döngü başlangıcı
            await MonthlyRevenueService._create_first_cycle(db, device_id, timestamp)
            return False
        
        # Son sıfırlamadan ne kadar zaman geçti?
        last_reset_result = await db.execute(
            select(DeviceMonthCycle)
            .where(DeviceMonthCycle.device_id == device_id)
            .where(DeviceMonthCycle.is_closed == True)
            .order_by(DeviceMonthCycle.cycle_end_date.desc())
            .limit(1)
        )
        last_reset = last_reset_result.scalar_one_or_none()
        
        if last_reset and last_reset.cycle_end_date:
            days_since_reset = (timestamp - last_reset.cycle_end_date).days
            if days_since_reset < MonthlyRevenueService.MIN_DAYS_BETWEEN_RESETS:
                # Çok kısa sürede ikinci sıfırlama - ignore et
                return False
        
        # Önceki değerlerden belirgin düşüş var mı?
        prev_19l = last_reading.counter_19l or 0
        prev_5l = last_reading.counter_5l or 0
        
        if prev_19l > 0:
            drop_19l = (prev_19l - counter_19l) / prev_19l
        else:
            drop_19l = 1.0
            
        if prev_5l > 0:
            drop_5l = (prev_5l - counter_5l) / prev_5l
        else:
            drop_5l = 1.0
        
        # Her iki sayaçta da belirgin düşüş var mı?
        if drop_19l >= MonthlyRevenueService.RESET_DROP_PERCENTAGE and drop_5l >= MonthlyRevenueService.RESET_DROP_PERCENTAGE:
            # Sıfırlama algılandı - ayı kapat
            await MonthlyRevenueService.close_month_cycle(
                db, device_id, prev_19l, prev_5l, timestamp
            )
            return True
        
        return False
    
    @staticmethod
    async def _create_first_cycle(
        db: AsyncSession,
        device_id: int,
        timestamp: datetime
    ):
        """İlk döngüyü oluştur"""
        cycle = DeviceMonthCycle(
            device_id=device_id,
            cycle_start_date=timestamp,
            start_counter_19l=0,
            start_counter_5l=0,
            year=timestamp.year,
            month=timestamp.month,
            is_closed=False
        )
        db.add(cycle)
        await db.commit()
    
    @staticmethod
    async def close_month_cycle(
        db: AsyncSession,
        device_id: int,
        closing_counter_19l: int,
        closing_counter_5l: int,
        timestamp: datetime
    ):
        """
        Aktif aylık döngüyü kapat ve ciroyu kaydet
        
        Args:
            db: Veritabanı oturumu
            device_id: Cihaz ID
            closing_counter_19l: Kapanış 19L değeri
            closing_counter_5l: Kapanış 5L değeri
            timestamp: Kapanış zamanı
        """
        # Aktif döngüyü bul
        active_cycle_result = await db.execute(
            select(DeviceMonthCycle)
            .where(DeviceMonthCycle.device_id == device_id)
            .where(DeviceMonthCycle.is_closed == False)
            .order_by(DeviceMonthCycle.cycle_start_date.desc())
            .limit(1)
        )
        active_cycle = active_cycle_result.scalar_one_or_none()
        
        if not active_cycle:
            # Aktif döngü yok - yeni oluştur
            await MonthlyRevenueService._create_first_cycle(db, device_id, timestamp)
            return
        
        # Döngüyü kapat
        active_cycle.cycle_end_date = timestamp
        active_cycle.end_counter_19l = closing_counter_19l
        active_cycle.end_counter_5l = closing_counter_5l
        active_cycle.total_revenue = closing_counter_19l + closing_counter_5l
        active_cycle.is_closed = True
        active_cycle.updated_at = datetime.utcnow()
        
        # Aylık ciro kaydı oluştur veya güncelle
        await MonthlyRevenueService._create_or_update_monthly_record(
            db, device_id, active_cycle.year, active_cycle.month,
            active_cycle.cycle_start_date, timestamp,
            closing_counter_19l, closing_counter_5l,
            active_cycle.total_revenue
        )
        
        # Yeni döngüyü başlat
        new_cycle = DeviceMonthCycle(
            device_id=device_id,
            cycle_start_date=timestamp,
            start_counter_19l=0,
            start_counter_5l=0,
            year=timestamp.year,
            month=timestamp.month,
            is_closed=False
        )
        db.add(new_cycle)
        
        await db.commit()
    
    @staticmethod
    async def _create_or_update_monthly_record(
        db: AsyncSession,
        device_id: int,
        year: int,
        month: int,
        month_start: datetime,
        month_end: datetime,
        counter_19l: int,
        counter_5l: int,
        total_revenue: int
    ):
        """Aylık ciro kaydı oluştur veya güncelle"""
        # Mevcut kaydı kontrol et
        existing_result = await db.execute(
            select(MonthlyRevenueRecord)
            .where(MonthlyRevenueRecord.device_id == device_id)
            .where(MonthlyRevenueRecord.year == year)
            .where(MonthlyRevenueRecord.month == month)
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Güncelle
            existing.month_end_date = month_end
            existing.closing_counter_19l = counter_19l
            existing.closing_counter_5l = counter_5l
            existing.total_revenue = total_revenue
            existing.is_closed = True
            existing.updated_at = datetime.utcnow()
        else:
            # Yeni kayıt
            record = MonthlyRevenueRecord(
                device_id=device_id,
                year=year,
                month=month,
                month_start_date=month_start,
                month_end_date=month_end,
                closing_counter_19l=counter_19l,
                closing_counter_5l=counter_5l,
                total_revenue=total_revenue,
                is_closed=True
            )
            db.add(record)
    
    @staticmethod
    async def get_current_month_revenue(
        db: AsyncSession,
        device_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Mevcut ayın cirosunu getir
        
        Args:
            db: Veritabanı oturumu
            device_id: Opsiyonel cihaz filtresi
            
        Returns:
            Mevcut ay ciro listesi
        """
        now = datetime.utcnow()
        year = now.year
        month = now.month
        
        query = select(MonthlyRevenueRecord).where(
            MonthlyRevenueRecord.year == year
        ).where(
            MonthlyRevenueRecord.month == month
        )
        
        if device_id:
            query = query.where(MonthlyRevenueRecord.device_id == device_id)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            {
                "device_id": r.device_id,
                "year": r.year,
                "month": r.month,
                "total_revenue": r.total_revenue,
                "closing_counter_19l": r.closing_counter_19l,
                "closing_counter_5l": r.closing_counter_5l,
                "is_closed": r.is_closed,
            }
            for r in records
        ]
    
    @staticmethod
    async def get_monthly_revenue_summary(
        db: AsyncSession,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        """
        Aylık ciro özeti getir
        
        Args:
            db: Veritabanı oturumu
            year: Yıl
            month: Ay
            
        Returns:
            Aylık özet
        """
        # Tüm cihazların o ay cirosu
        result = await db.execute(
            select(MonthlyRevenueRecord).where(
                MonthlyRevenueRecord.year == year
            ).where(
                MonthlyRevenueRecord.month == month
            )
        )
        records = result.scalars().all()
        
        total_revenue = sum(r.total_revenue for r in records)
        total_19l = sum(r.closing_counter_19l or 0 for r in records)
        total_5l = sum(r.closing_counter_5l or 0 for r in records)
        
        return {
            "year": year,
            "month": month,
            "total_revenue": total_revenue,
            "total_19l": total_19l,
            "total_5l": total_5l,
            "device_count": len(records),
            "closed_count": sum(1 for r in records if r.is_closed),
        }
    
    @staticmethod
    async def get_device_month_cycles(
        db: AsyncSession,
        device_id: int,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Cihazın aylık döngülerini getir
        
        Args:
            db: Veritabanı oturumu
            device_id: Cihaz ID
            limit: Maksimum kayıt sayısı
            
        Returns:
            Döngü listesi
        """
        result = await db.execute(
            select(DeviceMonthCycle)
            .where(DeviceMonthCycle.device_id == device_id)
            .order_by(DeviceMonthCycle.cycle_start_date.desc())
            .limit(limit)
        )
        cycles = result.scalars().all()
        
        return [
            {
                "cycle_start_date": c.cycle_start_date.isoformat(),
                "cycle_end_date": c.cycle_end_date.isoformat() if c.cycle_end_date else None,
                "start_counter_19l": c.start_counter_19l,
                "start_counter_5l": c.start_counter_5l,
                "end_counter_19l": c.end_counter_19l,
                "end_counter_5l": c.end_counter_5l,
                "total_revenue": c.total_revenue,
                "year": c.year,
                "month": c.month,
                "is_closed": c.is_closed,
            }
            for c in cycles
        ]
    
    @staticmethod
    async def get_monthly_revenue_history(
        db: AsyncSession,
        year: Optional[int] = None,
        month: Optional[int] = None,
        device_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Aylık ciro geçmişini getir
        
        Args:
            db: Veritabanı oturumu
            year: Opsiyonel yıl filtresi
            month: Opsiyonel ay filtresi
            device_id: Opsiyonel cihaz filtresi
            limit: Maksimum kayıt sayısı
            
        Returns:
            Ciro kayıtları listesi
        """
        query = select(MonthlyRevenueRecord)
        
        if year:
            query = query.where(MonthlyRevenueRecord.year == year)
        if month:
            query = query.where(MonthlyRevenueRecord.month == month)
        if device_id:
            query = query.where(MonthlyRevenueRecord.device_id == device_id)
        
        query = query.order_by(
            MonthlyRevenueRecord.year.desc(),
            MonthlyRevenueRecord.month.desc(),
            MonthlyRevenueRecord.device_id.asc()
        ).limit(limit)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        return [
            {
                "id": r.id,
                "device_id": r.device_id,
                "year": r.year,
                "month": r.month,
                "month_start_date": r.month_start_date.isoformat(),
                "month_end_date": r.month_end_date.isoformat() if r.month_end_date else None,
                "closing_counter_19l": r.closing_counter_19l,
                "closing_counter_5l": r.closing_counter_5l,
                "total_revenue": r.total_revenue,
                "is_closed": r.is_closed,
            }
            for r in records
        ]
    
    @staticmethod
    async def get_active_cycle_revenue(
        db: AsyncSession,
        device_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Aktif döngünün mevcut cirosunu getir
        
        Args:
            db: Veritabanı oturumu
            device_id: Opsiyonel cihaz filtresi
            
        Returns:
            Aktif döngü ciroları
        """
        query = select(DeviceMonthCycle, Device).join(
            Device, DeviceMonthCycle.device_id == Device.id
        ).where(
            DeviceMonthCycle.is_closed == False
        )
        
        if device_id:
            query = query.where(DeviceMonthCycle.device_id == device_id)
        
        result = await db.execute(query)
        cycles = result.all()
        
        revenue_list = []
        for cycle, device in cycles:
            # Son okumayı getir
            last_reading_result = await db.execute(
                select(DeviceReading)
                .where(DeviceReading.device_id == device.id)
                .where(DeviceReading.timestamp >= cycle.cycle_start_date)
                .where(DeviceReading.counter_19l.isnot(None))
                .where(DeviceReading.counter_5l.isnot(None))
                .order_by(DeviceReading.timestamp.desc())
                .limit(1)
            )
            last_reading = last_reading_result.scalar_one_or_none()
            
            current_19l = last_reading.counter_19l if last_reading else 0
            current_5l = last_reading.counter_5l if last_reading else 0
            current_revenue = current_19l + current_5l
            
            revenue_list.append({
                "device_id": device.id,
                "device_code": device.device_code,
                "device_name": device.name,
                "cycle_start_date": cycle.cycle_start_date.isoformat(),
                "current_counter_19l": current_19l,
                "current_counter_5l": current_5l,
                "current_revenue": current_revenue,
                "year": cycle.year,
                "month": cycle.month,
            })
        
        return revenue_list
