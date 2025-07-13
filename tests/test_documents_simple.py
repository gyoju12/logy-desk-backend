import os
import tempfile
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.password_utils import get_password_hash
from app.core.security import create_access_token
from app.db.base import Base
from app.db.database import get_db
from app.main import API_PREFIX, app
from app.models.db_models import DocumentChunk, UploadedFile, User

# Create async test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

# Test data
TEST_DOCUMENT = {
    "file_name": "test.txt",
    "file_path": "/uploads/test.txt",
    "file_size": 1024,
    "file_type": "text/plain",
}


# Fixtures
@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_db():
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="module")
async def test_user():
    async with TestingSessionLocal() as db:
        email = f"test-{uuid4()}@example.com"
        user = User(
            email=email,
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user, email


@pytest.fixture(scope="module")
def auth_headers(test_user):
    _, email = test_user
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    # Override the get_db dependency
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up
    app.dependency_overrides.clear()


# Tests
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
                headers=auth_headers,
            )

        assert (
            response.status_code == status.HTTP_200_OK
        ), f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert data["file_name"] == "test.txt"
        assert data["file_type"] == "text/plain"
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
