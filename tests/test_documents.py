import os
import tempfile
import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt
from datetime import datetime, timedelta
from uuid import uuid4

from app.main import app, API_PREFIX
from app.db.base import Base
from app.db.database import get_db, async_engine
from app.models.db_models import Document, User
from app.core.config import settings
from app.core.security import create_access_token
from app.core.password_utils import get_password_hash

# API prefix
API_PREFIX = "/api/v1"

# Create async test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

# Override the get_db dependency for testing
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

# Create a test user
async def create_test_user():
    async with TestingSessionLocal() as db:
        email = f"test-{uuid4()}@example.com"
        user = User(
            email=email,
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user, email

# Create JWT token for testing
def create_test_token(email: str):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": email},
        expires_delta=access_token_expires
    )

# Test data
TEST_DOCUMENT = {
    "file_name": "test.txt",
    "file_path": "/uploads/test.txt",
    "file_size": 1024,
    "file_type": "text/plain"
}

@pytest_asyncio.fixture(scope="module")
async def setup_db():
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="module")
async def test_user():
    return await create_test_user()

@pytest_asyncio.fixture(scope="module")
async def auth_headers(test_user):
    _, email = test_user
    token = create_test_token(email)
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture(scope="module")
async def test_document(test_user):
    """Create a test document"""
    user, _ = test_user
    async with TestingSessionLocal() as db:
        db_document = Document(
            user_id=user.id,
            file_name=TEST_DOCUMENT["file_name"],
            file_path=TEST_DOCUMENT["file_path"],
            file_size=TEST_DOCUMENT["file_size"],
            file_type=TEST_DOCUMENT["file_type"]
        )
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        return db_document

@pytest.fixture(scope="module")
def client():
    # Apply the override
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as c:
        yield c
    
    # Clean up
    app.dependency_overrides.clear()

# Test upload document
def test_upload_document(client, test_user, auth_headers, setup_db):
    """Test uploading a document"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"Test file content")
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, "rb") as f:
            response = client.post(
                f"{API_PREFIX}/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"file_name": "test.txt"},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["file_name"] == "test.txt"
        assert data["file_type"] == "text/plain"
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

# Test list documents
def test_list_documents(client, test_document, auth_headers, setup_db):
    """Test listing all documents"""
    response = client.get(f"{API_PREFIX}/documents/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["file_name"] == TEST_DOCUMENT["file_name"]

# Test get document
def test_get_document(client, test_document, auth_headers, setup_db):
    """Test getting a document by ID"""
    response = client.get(f"{API_PREFIX}/documents/{test_document.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert data["id"] == str(test_document.id)
    assert data["file_name"] == TEST_DOCUMENT["file_name"]

# Test delete document
def test_delete_document(client, test_document, auth_headers, setup_db):
    """Test deleting a document"""
    # First, get the document to ensure it exists
    response = client.get(f"{API_PREFIX}/documents/{test_document.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    # Now delete it
    response = client.delete(f"{API_PREFIX}/documents/{test_document.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    # Verify it's gone
    response = client.get(f"{API_PREFIX}/documents/{test_document.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND, f"Expected 404, got {response.status_code}. Response: {response.text}"
