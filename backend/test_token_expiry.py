"""Test token expiry issue"""
import requests
from datetime import datetime, timezone
from jose import jwt

# Login ve token al
r = requests.post('http://localhost:8000/api/v1/auth/login', json={'username':'admin','password':'admin123'})
token = r.json()['access_token']

# Token'ı decode et (expiration kontrolü olmadan)
payload = jwt.decode(token, '', options={'verify_signature': False, 'verify_exp': False})
print('Token Payload:')
for k, v in payload.items():
    print(f'  {k}: {v}')
print()

now_utc = datetime.now(timezone.utc)
print(f'Current UTC time: {now_utc.isoformat()}')
print(f'Current UTC timestamp: {now_utc.timestamp()}')
print()
print(f'Token exp (timestamp): {payload["exp"]}')
print(f'Token exp (datetime): {datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()}')
print()
print(f'Time until expiry (seconds): {payload["exp"] - now_utc.timestamp()}')
print(f'Time until expiry (minutes): {(payload["exp"] - now_utc.timestamp()) / 60}')
print()

# Şimdi token'ı normal şekilde decode etmeyi dene
try:
    decoded = jwt.decode(token, 'secret-key', algorithms=['HS256'])
    print('Token decoded successfully!')
except Exception as e:
    print(f'Token decode failed: {e}')
