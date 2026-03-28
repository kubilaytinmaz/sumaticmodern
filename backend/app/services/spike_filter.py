"""
Sumatic Modern IoT - Spike Filter
Detects and filters spike values in device readings.
Ported from original program.py spike detection logic.
"""
from collections import deque
from datetime import datetime
from typing import Dict, Tuple, Optional
from pytz import timezone

from app.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Istanbul timezone
IST_TIMEZONE = timezone("Europe/Istanbul")


# Maximum jump thresholds by column name (from original program.py)
MAX_JUMP_BY_COL = {
    "Program 1 Para Adedi": 200,
    "Program 2 Para Adedi": 200,
    "Cikis-3 : Giris 1 Ortak Zaman": 200,
    "Cikis-3 : Giris 2 Ortak Zaman": 200,
    "Sayac 1": 10000,
    "Sayac 2": 10000,
    "Cikis-1 Durum": 10000,
    "Cikis-2 Durum": 10000,
    "Acil Ariza Durumu": 1,
    # English equivalents
    "counter_19l": 10000,
    "counter_5l": 10000,
    "output_1_status": 10000,
    "output_2_status": 10000,
    "fault_status": 1,
    "program_1_coin_count": 200,
    "program_2_coin_count": 200,
    "output3_input1_time": 200,
    "output3_input2_time": 200,
}


class SpikeFilter:
    """
    Spike detection filter for device readings.
    Implements the same algorithm as the original program.py.
    
    Key features:
    - Rolling window of last 5 good values
    - Spike streak tracking (accept after 5 consecutive same spikes)
    - Month reset handling for counters
    """

    def __init__(
        self,
        window_size: int = 5,
        streak_threshold: int = 5,
    ):
        """
        Initialize spike filter.
        
        Args:
            window_size: Size of rolling window for averaging (default: 5)
            streak_threshold: Number of consecutive spikes to accept (default: 5)
        """
        self.window_size = window_size
        self.streak_threshold = streak_threshold
        
        # Last good value by (device_id, column_name)
        self._last_good: Dict[Tuple[int, str], int] = {}
        
        # Rolling window of last N good values
        self._window: Dict[Tuple[int, str], deque] = {}
        
        # Spike streak tracking: {(device_id, col): (last_spike_val, streak_count)}
        self._spike_streak: Dict[Tuple[int, str], Tuple[int, int]] = {}

    def is_valid(
        self,
        device_id: int,
        column_name: str,
        value: int,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Check if a value is valid (not a spike).
        
        Args:
            device_id: Device ID
            column_name: Column/field name
            value: Value to check
            timestamp: Reading timestamp (default: now)
            
        Returns:
            True if value is valid, False if it's a spike
        """
        if timestamp is None:
            timestamp = datetime.now(IST_TIMEZONE)
        
        key = (device_id, column_name)
        max_jump = MAX_JUMP_BY_COL.get(column_name)
        
        # First value for this device/column - always accept
        if key not in self._last_good:
            self._seed_value(key, value)
            logger.debug(f"SEED: device={device_id} {column_name} = {value}")
            return True
        
        # Month reset handling for counters
        if self._is_month_reset_candidate(column_name, value, timestamp):
            return self._handle_month_reset(key, value)
        
        # No max_jump defined - accept all values
        if max_jump is None:
            self._accept_value(key, value)
            return True
        
        # Initialize window if needed
        if key not in self._window:
            self._window[key] = deque(maxlen=self.window_size)
        
        window = self._window[key]
        
        # Build up window until full
        if len(window) < self.window_size:
            self._accept_value(key, value)
            return True
        
        # Calculate average of window
        avg = sum(window) / len(window)
        
        # Check if value is within acceptable range
        if abs(value - avg) <= max_jump:
            self._accept_value(key, value)
            return True
        
        # Value is a potential spike - check streak
        return self._handle_spike(key, value, column_name)

    def _seed_value(self, key: Tuple[int, str], value: int) -> None:
        """Seed initial value for a device/column."""
        self._last_good[key] = value
        if key not in self._window:
            self._window[key] = deque(maxlen=self.window_size)
        self._window[key].append(value)
        self._spike_streak.pop(key, None)

    def _accept_value(self, key: Tuple[int, str], value: int) -> None:
        """Accept a value as valid."""
        self._last_good[key] = value
        if key in self._window:
            self._window[key].append(value)
        else:
            self._window[key] = deque([value], maxlen=self.window_size)
        self._spike_streak.pop(key, None)

    def _is_month_reset_candidate(
        self,
        column_name: str,
        value: int,
        timestamp: datetime,
    ) -> bool:
        """Check if this could be a month reset for counters."""
        if column_name not in ("Sayac 1", "Sayac 2", "counter_19l", "counter_5l"):
            return False
        
        # Only in first 3 days of month
        if timestamp.day > 3:
            return False
        
        # Only small values after reset
        if value > 10:
            return False
        
        return True

    def _handle_month_reset(self, key: Tuple[int, str], value: int) -> bool:
        """Handle potential month reset for counters."""
        last_val, streak = self._spike_streak.get(key, (None, 0))
        
        if value == last_val:
            streak += 1
        else:
            streak = 1
            last_val = value
        
        self._spike_streak[key] = (last_val, streak)
        
        # Accept after 3 consecutive same values
        if streak >= 3:
            logger.info(f"RESET ACCEPTED: device={key[0]} {key[1]} = {value}")
            self._accept_value(key, value)
            return True
        
        # Not enough confirmation - treat as spike
        return False

    def _handle_spike(
        self,
        key: Tuple[int, str],
        value: int,
        column_name: str,
    ) -> bool:
        """Handle a potential spike value."""
        last_val, streak = self._spike_streak.get(key, (None, 0))
        
        # Increment streak if same or higher spike
        if last_val is not None and value >= last_val:
            streak += 1
        else:
            streak = 1
        
        last_val = value
        self._spike_streak[key] = (last_val, streak)
        
        # Accept after threshold consecutive spikes
        if streak >= self.streak_threshold:
            logger.info(
                f"SPIKE ACCEPTED (streak={streak}): device={key[0]} {column_name} = {value}"
            )
            self._accept_value(key, value)
            return True
        
        # Log rejected spike for counters
        if column_name in ("Sayac 1", "Sayac 2", "counter_19l", "counter_5l"):
            logger.warning(
                f"SPIKE REJECTED: device={key[0]} {column_name} = {value} (streak={streak})"
            )
        
        return False

    def get_last_good(self, device_id: int, column_name: str) -> Optional[int]:
        """Get the last good value for a device/column."""
        return self._last_good.get((device_id, column_name))

    def get_window(self, device_id: int, column_name: str) -> list:
        """Get the rolling window for a device/column."""
        key = (device_id, column_name)
        if key in self._window:
            return list(self._window[key])
        return []

    def reset_device(self, device_id: int) -> None:
        """Reset all filter state for a device."""
        keys_to_remove = [k for k in self._last_good if k[0] == device_id]
        for key in keys_to_remove:
            self._last_good.pop(key, None)
            self._window.pop(key, None)
            self._spike_streak.pop(key, None)
        
        logger.info(f"Spike filter reset for device {device_id}")

    def reset_all(self) -> None:
        """Reset all filter state."""
        self._last_good.clear()
        self._window.clear()
        self._spike_streak.clear()
        logger.info("Spike filter fully reset")

    def get_stats(self) -> Dict[str, int]:
        """Get filter statistics."""
        return {
            "tracked_columns": len(self._last_good),
            "active_windows": len(self._window),
            "active_streaks": len(self._spike_streak),
        }


# Global singleton instance
spike_filter = SpikeFilter(
    window_size=settings.SPIKE_WINDOW_SIZE,
    streak_threshold=settings.SPIKE_STREAK_THRESHOLD,
)


def get_spike_filter() -> SpikeFilter:
    """Get the spike filter singleton."""
    return spike_filter
