import asyncio
import os

import httpx

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_FILE = "test_document.txt"

# Create a test file if it doesn't exist
if not os.path.exists(TEST_FILE):
    with open(TEST_FILE, "w") as f:
        f.write("This is a test document for the Logy-Desk API.")


async def test_upload() -> None:
    # First, log in to get a token
    async with httpx.AsyncClient() as client:
        # Replace with your test user credentials
        login_data = {"username": "test@example.com", "password": "testpassword"}

        try:
            # Try to log in
            login_response = await client.post(
                f"{BASE_URL}/auth/login",
                data={
                    "username": login_data["username"],
                    "password": login_data["password"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            login_response.raise_for_status()
            token = login_response.json()["access_token"]
            print("Successfully logged in")

            # Prepare the file for upload
            with open(TEST_FILE, "rb") as f:
                files = {"file": (os.path.basename(TEST_FILE), f, "text/plain")}
                data = {"title": "Test Document"}

                # Make the upload request with the token
                headers = {"Authorization": f"Bearer {token}"}
                upload_response = await client.post(
                    f"{BASE_URL}/documents/upload",
                    files=files,
                    data=data,
                    headers=headers,
                )

                upload_response.raise_for_status()
                print("\nUpload successful!")
                print("Response:", upload_response.json())

                # List all documents
                list_response = await client.get(
                    f"{BASE_URL}/documents", headers=headers
                )
                list_response.raise_for_status()
                print("\nDocuments:", list_response.json())

        except httpx.HTTPStatusError as e:
            print(f"\nError: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_upload())
