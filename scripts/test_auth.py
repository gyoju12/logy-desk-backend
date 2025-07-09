import sys
import os
import asyncio
from typing import Dict, Any
import httpx
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

# Test user data
TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword123"
}

class TestClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user."""
        url = f"{self.base_url}/auth/register"
        try:
            print(f"\n🔍 Attempting to register user at URL: {url}")
            payload = {
                "email": user_data["email"],
                "password": user_data["password"],
                "is_active": True,
                "is_superuser": False
            }
            print(f"📤 Payload: {payload}")
            
            response = await self.client.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"📥 Response data: {response_data}")
            except Exception as json_err:
                print(f"❌ Could not parse JSON response: {json_err}")
                print(f"📥 Raw response text: {response.text[:500]}")
                response_data = {"detail": "Invalid JSON response"}
            
            return {
                "status_code": response.status_code,
                "data": response_data if response.status_code < 400 
                         else {"detail": response_data.get("detail", "Unknown error")}
            }
        except Exception as e:
            print(f"❌ Exception during registration: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status_code": 500,
                "data": {"detail": str(e)}
            }
    
    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user and get JWT token."""
        url = f"{self.base_url}/auth/login"
        try:
            print(f"\n🔍 Attempting to login at URL: {url}")
            form_data = {
                "username": email,
                "password": password,
                "grant_type": "password"
            }
            print(f"📤 Form data: {form_data}")
            
            # Create a copy of headers and update for form data
            headers = self.headers.copy()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            response = await self.client.post(
                url,
                data=form_data,
                headers=headers,
                timeout=30.0
            )
            
            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"📥 Response data: {response_data}")
            except Exception as json_err:
                print(f"❌ Could not parse JSON response: {json_err}")
                print(f"📥 Raw response text: {response.text[:500]}")
                response_data = {"detail": "Invalid JSON response"}
            
            if response.status_code == 200:
                self.token = response_data.get("access_token")
                if self.token:
                    self.headers["Authorization"] = f"Bearer {self.token}"
            
            return {
                "status_code": response.status_code,
                "data": response_data if response.status_code < 400 
                         else {"detail": response_data.get("detail", "Login failed")}
            }
            
        except Exception as e:
            print(f"❌ Exception during login: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status_code": 500,
                "data": {"detail": str(e)}
            }
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information."""
        if not self.token:
            return {"status_code": 401, "data": {"detail": "Not authenticated"}}
            
        url = f"{self.base_url}/auth/me"
        headers = {
            "Authorization": f"Bearer {self.token}",
            **self.headers
        }
        
        try:
            response = await self.client.get(url, headers=headers)
            response_data = response.json() if response.status_code < 400 else {"detail": response.text}
            return {
                "status_code": response.status_code,
                "data": response_data
            }
        except Exception as e:
            return {
                "status_code": 500,
                "data": {"detail": f"Error getting current user: {str(e)}"}
            }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def run_tests():
    """Run authentication tests."""
    client = TestClient()
    
    try:
        print("🚀 Starting authentication tests...\n")
        
        # Test 1: Register a new user
        print("1. Testing user registration...")
        result = await client.register_user(TEST_USER)
        if result["status_code"] == 201:
            print(f"✅ User registered successfully: {result['data']['email']}")
        elif result["status_code"] == 400 and "already registered" in result["data"]["detail"]:
            print("ℹ️  User already exists, continuing with login...")
        else:
            print(f"❌ Registration failed: {result['data']}")
            return
        
        # Test 2: Login with the registered user
        print("\n2. Testing user login...")
        result = await client.login_user(TEST_USER["email"], TEST_USER["password"])
        if result["status_code"] == 200:
            print(f"✅ Login successful. Token: {result['data']['access_token'][:30]}...")
        else:
            print(f"❌ Login failed: {result['data']}")
            return
        
        # Test 3: Get current user info
        print("\n3. Testing current user endpoint...")
        result = await client.get_current_user()
        if result["status_code"] == 200:
            print(f"✅ Current user: {result['data']['email']}")
            print(f"   User ID: {result['data']['id']}")
            print(f"   Is active: {result['data']['is_active']}")
            print(f"   Is superuser: {result['data']['is_superuser']}")
        else:
            print(f"❌ Failed to get current user: {result['data']}")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
