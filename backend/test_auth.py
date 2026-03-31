"""
Test auth endpoints
"""
import requests

# Login
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'username': 'admin', 'password': 'admin123'}
)
print(f"Login status: {login_response.status_code}")
print(f"Login response: {login_response.text}")

if login_response.status_code == 200:
    data = login_response.json()
    token = data['access_token']
    print(f"\nToken: {token[:50]}...")

    # Get user info
    me_response = requests.get(
        'http://localhost:8000/api/v1/auth/me',
        headers={'Authorization': f'Bearer {token}'}
    )
    print(f"\n/me status: {me_response.status_code}")
    print(f"/me response: {me_response.text}")
