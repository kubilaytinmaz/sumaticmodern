#!/usr/bin/env python3
"""Test script to verify JWT token contains jti claim."""
import sys
sys.path.insert(0, '.')

from app.core.security import create_access_token
from app.config import get_settings
from jose import jwt

settings = get_settings()

# Create a test token
token = create_access_token('test_user', 'admin', 3600)

# Decode without verification to see payload
payload = jwt.get_unverified_claims(token)

print("Token payload:")
for key, value in payload.items():
    print(f"  {key}: {value}")

print(f"\nHas jti: {'jti' in payload}")
if 'jti' in payload:
    print(f"jti value: {payload['jti']}")
