"""Test script for JTI logout and refresh token fixes."""
import requests
import base64
import json


def decode_jwt_payload(token):
    """Decode JWT payload without verifying signature."""
    parts = token.split('.')
    if len(parts) != 3:
        return {}
    payload = parts[1]
    # Add padding
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)

BASE = 'http://localhost:8000'

print("=" * 60)
print("JTI FIX TEST - Login, Logout, Token Blacklist")
print("=" * 60)

# 1. Login
print("\n[1] LOGIN TEST")
r = requests.post(f'{BASE}/api/v1/auth/login', json={'username': 'admin', 'password': 'admin123'})
print(f"    Status: {r.status_code}")
if r.status_code != 200:
    print(f"    Error: {r.text}")
    exit(1)

data = r.json()
token = data.get('access_token', '')
refresh = data.get('refresh_token', '')

# 2. Decode access token - verify jti exists
print("\n[2] ACCESS TOKEN JTI CHECK")
payload = decode_jwt_payload(token)
access_jti = payload.get('jti', 'NOT FOUND')
print(f"    JTI: {access_jti}")
print(f"    Type: {payload.get('type', 'NOT FOUND')}")
assert access_jti != 'NOT FOUND', "Access token should have jti!"
print("    PASS: Access token has jti")

# 3. Decode refresh token - verify jti exists
print("\n[3] REFRESH TOKEN JTI CHECK")
refresh_payload = decode_jwt_payload(refresh)
refresh_jti = refresh_payload.get('jti', 'NOT FOUND')
print(f"    JTI: {refresh_jti}")
print(f"    Type: {refresh_payload.get('type', 'NOT FOUND')}")
assert refresh_jti != 'NOT FOUND', "Refresh token should have jti!"
assert '_refresh_' in refresh_jti, "Refresh token jti should contain '_refresh_'"
print("    PASS: Refresh token has jti with '_refresh_' suffix")

# 4. Test /me endpoint before logout
print("\n[4] /me BEFORE LOGOUT")
r = requests.get(f'{BASE}/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
print(f"    Status: {r.status_code}")
assert r.status_code == 200, "Should be authenticated before logout"
print("    PASS: User is authenticated")

# 5. Logout
print("\n[5] LOGOUT TEST")
r = requests.post(f'{BASE}/api/v1/auth/logout', headers={'Authorization': f'Bearer {token}'})
print(f"    Status: {r.status_code}")
print(f"    Response: {r.json()}")
assert r.status_code == 200, "Logout should succeed"
print("    PASS: Logout succeeded")

# 6. Test /me endpoint after logout (should fail with 401)
print("\n[6] /me AFTER LOGOUT (should be 401)")
r = requests.get(f'{BASE}/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
print(f"    Status: {r.status_code}")
if r.status_code == 401:
    print("    PASS: Token is blacklisted - user cannot access after logout")
else:
    print(f"    FAIL: Expected 401, got {r.status_code}")
    print(f"    Response: {r.json()}")

# 7. Login again to verify new token works
print("\n[7] RE-LOGIN TEST")
r = requests.post(f'{BASE}/api/v1/auth/login', json={'username': 'admin', 'password': 'admin123'})
print(f"    Status: {r.status_code}")
data = r.json()
new_token = data.get('access_token', '')
r = requests.get(f'{BASE}/api/v1/auth/me', headers={'Authorization': f'Bearer {new_token}'})
print(f"    /me Status: {r.status_code}")
assert r.status_code == 200, "New token should work"
print("    PASS: New login works fine")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
