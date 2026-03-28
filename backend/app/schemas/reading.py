"""
Sumatic Modern IoT - Reading Schemas (Counter-Only Optimized)
Pydantic schemas for device reading validation - ONLY 19L and 5L counters.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class ReadingBase(BaseModel):
    """Base reading schema - SADECE SAYAÇLAR."""
    counter_19l: Optional[int] = None
    counter_5l: Optional[int] = None


class ReadingResponse(ReadingBase):
    """Schema for reading response - SADECE SAYAÇLAR."""

    id: int
    device_id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class ReadingQuery(BaseModel):
    """Schema for querying readings - COUNTER ONLY."""

    device_id: Optional[int] = None
    device_ids: Optional[List[int]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class ReadingListResponse(BaseModel):
    """Schema for paginated reading list response."""

    items: List[ReadingResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ReadingSummary(BaseModel):
    """Schema for reading summary/aggregation - SADECE SAYAÇLAR."""

    device_id: int
    start_time: datetime
    end_time: datetime
    counter_19l_start: Optional[int] = None
    counter_19l_end: Optional[int] = None
    counter_19l_delta: Optional[int] = None
    counter_5l_start: Optional[int] = None
    counter_5l_end: Optional[int] = None
    counter_5l_delta: Optional[int] = None
    reading_count: int = 0
