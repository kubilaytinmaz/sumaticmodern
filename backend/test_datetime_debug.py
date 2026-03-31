"""Debug datetime timezone issue"""
from datetime import datetime, timezone
import time

# Test different datetime methods
print("=== DateTime Debug ===")
print()

# Method 1: datetime.now(timezone.utc)
now_utc = datetime.now(timezone.utc)
print(f"datetime.now(timezone.utc): {now_utc}")
print(f"  timestamp: {now_utc.timestamp()}")
print()

# Method 2: datetime.utcnow()
try:
    now_utc2 = datetime.utcnow()
    print(f"datetime.utcnow(): {now_utc2}")
    print(f"  timestamp: {now_utc2.timestamp()}")
    print()
except Exception as e:
    print(f"datetime.utcnow() error: {e}")
    print()

# Method 3: time.time()
now_time = time.time()
print(f"time.time(): {now_time}")
print(f"  from datetime: {datetime.fromtimestamp(now_time, tz=timezone.utc)}")
print()

# Method 4: datetime.now() without timezone
now_local = datetime.now()
print(f"datetime.now() (local): {now_local}")
print(f"  timestamp: {now_local.timestamp()}")
print()

# Test token creation simulation
print("=== Token Creation Simulation ===")
print()

# Simulate token creation
now = datetime.now(timezone.utc)
from datetime import timedelta
expire = now + timedelta(minutes=1440)

print(f"Now: {now}")
print(f"Now timestamp: {now.timestamp()}")
print(f"Expire: {expire}")
print(f"Expire timestamp: {expire.timestamp()}")
print(f"Time until expiry (seconds): {expire.timestamp() - now.timestamp()}")
print(f"Time until expiry (minutes): {(expire.timestamp() - now.timestamp()) / 60}")
print()

# Check if there's a timezone issue
print("=== System Timezone Info ===")
print(f"Local timezone: {time.tzname}")
print(f"UTC offset: {time.timezone / 3600} hours")
print(f"Daylight saving: {time.daylight}")
