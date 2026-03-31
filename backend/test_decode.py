"""
Test token decode
"""
from jose import jwt
from app.config import get_settings

settings = get_settings()

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3NDkyOTA5Mi43MzY2MDcsInR5cGUiOiJhY2Nlc3MifQ.E5VRp4qh0erK75op9F51sBA4fSWLWMfwGlzHUHN6GjU"

try:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    print(f"Decoded payload: {payload}")
    print(f"Type: {payload.get('type')}")
except Exception as e:
    print(f"Error: {e}")
