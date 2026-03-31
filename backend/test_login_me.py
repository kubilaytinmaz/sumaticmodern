#!/usr/bin/env python3
"""Test script to verify login and /me endpoint work correctly."""
import asyncio
import sys
sys.path.insert(0, '.')

import httpx
from jose import jwt

BASE_URL = "http://localhost:8000"

async def test_login_and_me():
    """Test login and then access /me endpoint."""
    async with httpx.AsyncClient() as client:
        # Step 1: Login
        print("Step 1: Testing login...")
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.text}")
            return
        
        login_data = login_response.json()
        access_token = login_data.get("access_token")
        
        print(f"Login successful!")
        print(f"Token preview: {access_token[:50]}...")
        
        # Decode token to check jti
        payload = jwt.get_unverified_claims(access_token)
        print(f"\nToken payload:")
        for key, value in payload.items():
            print(f"  {key}: {value}")
        print(f"\nHas jti: {'jti' in payload}")
        
        # Step 2: Access /me endpoint
        print("\nStep 2: Testing /me endpoint...")
        me_response = await client.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"/me status: {me_response.status_code}")
        
        if me_response.status_code == 200:
            me_data = me_response.json()
            print(f"/me successful! User: {me_data}")
        else:
            print(f"/me failed: {me_response.text}")

if __name__ == "__main__":
    asyncio.run(test_login_and_me())
