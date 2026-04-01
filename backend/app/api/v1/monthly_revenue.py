"""
Sumatic Modern IoT - Monthly Revenue API Endpoints
Aylık ciro API endpoint'leri
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.monthly_revenue_service import MonthlyRevenueService

router = APIRouter()


@router.get("/current")
async def get_current_month_revenue(
    device_id: Optional[int] = Query(None, description="Opsiyonel cihaz filtresi"),
    db: AsyncSession = Depends(get_db),
):
    """
    Mevcut ayın cirosunu getir
    
    Cihazların mevcut aydaki kapanmış cirolarını döndürür.
    """
    return await MonthlyRevenueService.get_current_month_revenue(db, device_id)


@router.get("/active")
async def get_active_cycle_revenue(
    device_id: Optional[int] = Query(None, description="Opsiyonel cihaz filtresi"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aktif döngünün mevcut cirosunu getir
    
    Henüz kapatılmamış aylık döngülerin mevcut cirolarını döndürür.
    """
    return await MonthlyRevenueService.get_active_cycle_revenue(db, device_id)


@router.get("/summary")
async def get_monthly_revenue_summary(
    year: int = Query(..., description="Yıl (örn: 2026)"),
    month: int = Query(..., ge=1, le=12, description="Ay (1-12)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aylık ciro özetini getir
    
    Belirtilen ay için tüm cihazların toplam cirosunu döndürür.
    """
    return await MonthlyRevenueService.get_monthly_revenue_summary(db, year, month)


@router.get("/device/{device_id}/cycles")
async def get_device_month_cycles(
    device_id: int,
    limit: int = Query(12, ge=1, le=100, description="Maksimum kayıt sayısı"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cihazın aylık döngülerini getir
    
    Belirtilen cihazın geçmiş aylık döngülerini döndürür.
    """
    return await MonthlyRevenueService.get_device_month_cycles(db, device_id, limit)


@router.get("/history")
async def get_monthly_revenue_history(
    year: Optional[int] = Query(None, description="Yıl filtresi"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Ay filtresi"),
    device_id: Optional[int] = Query(None, description="Cihaz filtresi"),
    limit: int = Query(100, ge=1, le=500, description="Maksimum kayıt sayısı"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aylık ciro geçmişini getir
    
    Belirtilen filtrelere göre aylık ciro kayıtlarını döndürür.
    """
    return await MonthlyRevenueService.get_monthly_revenue_history(
        db, year, month, device_id, limit
    )


@router.get("/stats/overview")
async def get_revenue_stats_overview(
    db: AsyncSession = Depends(get_db),
):
    """
    Genel ciro istatistikleri
    
    - Mevcut ay aktif döngü ciroları
    - Geçen ay kapanmış cirolar
    - Toplam cihaz sayısı
    """
    now = datetime.utcnow()
    current_year = now.year
    current_month = now.month
    
    # Geçen ayı hesapla
    if current_month == 1:
        prev_year = current_year - 1
        prev_month = 12
    else:
        prev_year = current_year
        prev_month = current_month - 1
    
    # Mevcut ay aktif cirolar
    active_revenue = await MonthlyRevenueService.get_active_cycle_revenue(db)
    
    # Geçen ay kapanmış cirolar
    prev_month_summary = await MonthlyRevenueService.get_monthly_revenue_summary(
        db, prev_year, prev_month
    )
    
    # Mevcut ay kapanmış cirolar
    current_month_summary = await MonthlyRevenueService.get_monthly_revenue_summary(
        db, current_year, current_month
    )
    
    return {
        "current_month": {
            "year": current_year,
            "month": current_month,
            "summary": current_month_summary,
            "active_revenue": active_revenue,
        },
        "previous_month": {
            "year": prev_year,
            "month": prev_month,
            "summary": prev_month_summary,
        },
    }
