#!/usr/bin/env python3
"""
Test script for document management endpoints.

This script tests the following endpoints:
- POST /api/v1/documents/upload
- GET /api/v1/documents
- GET /api/v1/documents/{document_id}
- DELETE /api/v1/documents/{document_id}
"""
import os
import sys
import asyncio
import httpx
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_FILE_PATH = os.path.join(os.path.dirname(__file__), "test_document.txt")

# Create a test document if it doesn't exist
if not os.path.exists(TEST_FILE_PATH):
    with open(TEST_FILE_PATH, "w") as f:
        f.write("This is a test document for the Logy-Desk API.")

class DocumentTestClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.token: Optional[str] = None
    
    async def login(self, email: str, password: str) -> bool:
        """Login and store the access token."""
        try:
            response = await self.client.post(
                f"{self.base_url}/auth/login",
                data={
                    "username": email,
                    "password": password,
                    "grant_type": "password"
                }
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            return True
        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return False
    
    async def upload_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Upload a document."""
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "text/plain")}
                response = await self.client.post(
                    f"{self.base_url}/documents/upload",
                    files=files
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Upload failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return None
    
    async def list_documents(self) -> Optional[Dict[str, Any]]:
        """List all documents."""
        try:
            response = await self.client.get(f"{self.base_url}/documents")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ List documents failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return None
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        try:
            response = await self.client.get(f"{self.base_url}/documents/{document_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Get document failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return None
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID."""
        try:
            response = await self.client.delete(f"{self.base_url}/documents/{document_id}")
            response.raise_for_status()
            print(f"✅ Document {document_id} deleted successfully")
            return True
        except Exception as e:
            print(f"❌ Delete document failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return False

async def main():
    print("🚀 Starting document management tests...")
    
    # Create test client
    client = DocumentTestClient(BASE_URL)
    
    # Step 1: Login
    print("\n1. Logging in...")
    if not await client.login(TEST_EMAIL, TEST_PASSWORD):
        print("❌ Login failed. Please check your credentials and try again.")
        return
    print("✅ Login successful")
    
    # Step 2: Upload a document
    print(f"\n2. Uploading test document: {TEST_FILE_PATH}")
    upload_result = await client.upload_document(TEST_FILE_PATH)
    if not upload_result:
        print("❌ Document upload failed. Aborting tests.")
        return
    
    document_id = upload_result.get("document_id")
    print(f"✅ Document uploaded successfully. ID: {document_id}")
    
    # Step 3: List documents
    print("\n3. Listing all documents...")
    documents = await client.list_documents()
    if documents:
        print(f"✅ Found {len(documents.get('documents', []))} documents")
        for doc in documents.get('documents', []):
            print(f"   - {doc['filename']} (ID: {doc['id']})")
    
    # Step 4: Get document details
    print(f"\n4. Getting document details for ID: {document_id}")
    document = await client.get_document(document_id)
    if document:
        print(f"✅ Document details:")
        print(f"   - Filename: {document.get('filename')}")
        print(f"   - Uploaded at: {document.get('uploaded_at')}")
    
    # Step 5: Delete the document
    print(f"\n5. Deleting document ID: {document_id}")
    await client.delete_document(document_id)
    
    # Verify deletion
    print("\n6. Verifying document deletion...")
    deleted_doc = await client.get_document(document_id)
    if deleted_doc is None:
        print("✅ Document deletion verified")
    else:
        print("❌ Document still exists after deletion")
    
    print("\n🎉 Document management tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
