"""
Insertion Log Service
In-memory storage for recent database insertions (decoupled from API layer).
This module avoids circular imports by keeping insertion log state separate.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class InsertionLogEntry(BaseModel):
    """Single DB insertion log entry."""
    id: int
    device_id: int
    device_code: str
    timestamp: str
    counter_19l: Optional[int] = None
    counter_5l: Optional[int] = None
    status: str
    created_at: str


# In-memory log storage (last 100 entries)
_insertion_logs: List[InsertionLogEntry] = []
_max_entries = 100
_counter = 0


def add_insertion_log(
    device_id: int,
    device_code: str,
    timestamp: datetime,
    counter_19l: Optional[int],
    counter_5l: Optional[int],
    status: str
) -> None:
    """Add a database insertion log entry to in-memory storage."""
    global _counter
    _counter += 1

    entry = InsertionLogEntry(
        id=_counter,
        device_id=device_id,
        device_code=device_code,
        timestamp=timestamp.isoformat(),
        counter_19l=counter_19l,
        counter_5l=counter_5l,
        status=status,
        created_at=datetime.utcnow().isoformat()
    )
    _insertion_logs.append(entry)
    if len(_insertion_logs) > _max_entries:
        _insertion_logs.pop(0)


def get_recent_insertions(limit: int = 50) -> List[InsertionLogEntry]:
    """Get recent DB insertion log entries."""
    return list(reversed(_insertion_logs[-limit:]))
