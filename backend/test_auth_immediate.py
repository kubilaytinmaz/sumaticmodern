"""
Test auth endpoints immediately
"""
import requests
import time

# Login
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'username': 'admin', 'password': 'admin123'}
)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    data = login_response.json()
    token = data['access_token']
    print(f"Token received")

    # Get user info IMMEDIATELY
    me_response = requests.get(
        'http://localhost:8000/api/v1/auth/me',
        headers={'Authorization': f'Bearer {token}'}
    )
    print(f"/me status (immediate): {me_response.status_code}")
    if me_response.status_code == 200:
        print(f"/me response: {me_response.json()}")
    else:
        print(f"/me error: {me_response.text}")

    # Check token expiration
    from jose import jwt
    from app.config import get_settings
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        print(f"Token payload: {payload}")
    except Exception as e:
        print(f"Token decode error: {e}")
