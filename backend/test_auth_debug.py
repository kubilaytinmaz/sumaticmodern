"""Test auth endpoint with detailed logging."""
import requests
import json
import base64

# Test login
print("=== Testing Login ===")
r = requests.post('http://localhost:8000/api/v1/auth/login', json={'username':'admin','password':'admin123'})
print(f"Login Status: {r.status_code}")
print(f"Login Response: {r.text[:200]}")

if r.status_code == 200:
    data = r.json()
    token = data['access_token']
    print(f"\nToken: {token[:50]}...")
    
    # Decode token payload
    parts = token.split('.')
    payload = parts[1]
    padded = payload + '=' * (4 - len(payload) % 4)
    decoded = base64.b64decode(padded)
    payload_data = json.loads(decoded)
    print(f"\nToken Payload: {json.dumps(payload_data, indent=2)}")
    
    # Test /me endpoint
    print("\n=== Testing /me endpoint ===")
    r2 = requests.get('http://localhost:8000/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    print(f"/me Status: {r2.status_code}")
    print(f"/me Response: {r2.text}")
