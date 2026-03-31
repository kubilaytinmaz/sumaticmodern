"""
Test token payload without expiration check
"""
import requests
from jose import jwt
from app.config import get_settings

settings = get_settings()

# Login
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'username': 'admin', 'password': 'admin123'}
)

if login_response.status_code == 200:
    data = login_response.json()
    token = data['access_token']

    # Decode without verification to see payload
    import base64
    import json
    parts = token.split('.')
    payload = parts[1]
    # Add padding if needed
    payload += '=' * (4 - len(payload) % 4)
    decoded = base64.b64decode(payload)
    payload_data = json.loads(decoded)
    print(f"Token payload (no verification): {payload_data}")

    import time
    now = time.time()
    print(f"Current timestamp: {now}")
    print(f"Token exp timestamp: {payload_data['exp']}")
    print(f"Time diff: {payload_data['exp'] - now} seconds")
    print(f"Token expired: {payload_data['exp'] < now}")
