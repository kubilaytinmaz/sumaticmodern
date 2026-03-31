"""Test authentication after jti fix"""
import requests
from datetime import datetime, timezone
from jose import jwt
from app.config import get_settings

settings = get_settings()

print("=== Testing Authentication ===")
print()

# Login ve token al
print("1. Logging in...")
r = requests.post('http://localhost:8000/api/v1/auth/login', json={'username':'admin','password':'admin123'})
print(f"   Status: {r.status_code}")
token = r.json()['access_token']
print(f"   Token: {token[:50]}...")
print()

# Token payload'ı incele
print("2. Analyzing token payload...")
payload = jwt.decode(token, '', options={'verify_signature': False, 'verify_exp': False})
print(f"   sub: {payload['sub']}")
print(f"   username: {payload['username']}")
print(f"   role: {payload['role']}")
print(f"   type: {payload['type']}")
print(f"   jti: {payload['jti']}")
print(f"   exp (timestamp): {payload['exp']}")
print(f"   exp (datetime): {datetime.fromtimestamp(payload['exp'], tz=timezone.utc).isoformat()}")
print()

# Şu anki zaman
now_utc = datetime.now(timezone.utc)
print(f"3. Current time check...")
print(f"   Current UTC: {now_utc.isoformat()}")
print(f"   Current timestamp: {now_utc.timestamp()}")
print(f"   Time until expiry: {payload['exp'] - now_utc.timestamp():.0f} seconds")
print(f"   Time until expiry: {(payload['exp'] - now_utc.timestamp()) / 60:.0f} minutes")
print()

# Token'ı normal şekilde decode et
print("4. Validating token signature...")
try:
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    print(f"   SUCCESS! Token is valid.")
    print(f"   Decoded: {decoded}")
except Exception as e:
    print(f"   FAILED: {e}")
print()

# /me endpoint'ini test et
print("5. Testing /me endpoint...")
r2 = requests.get('http://localhost:8000/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
print(f"   Status: {r2.status_code}")
if r2.status_code == 200:
    print(f"   Response: {r2.json()}")
else:
    print(f"   Error: {r2.text}")
