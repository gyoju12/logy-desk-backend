import os
import tempfile
from datetime import timedelta
from typing import Any, AsyncGenerator, Dict, Tuple
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine # Changed import
from sqlalchemy.orm import sessionmaker # Keep sessionmaker for sync operations

from app.core.config import settings
from app.core.security import get_password_hash, create_access_token # Changed import
from app.db.base import Base
from app.db.session import get_db
from app.main import API_PREFIX, app
from app.models.db_models import User

# Create async test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker( # Changed to async_sessionmaker
    bind=test_engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False
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
def event_loop() -> Any:
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_db() -> AsyncGenerator[None, None]: # Added return type
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="module")
async def test_user() -> Tuple[User, str]: # Added return type
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
def auth_headers(test_user: Tuple[User, str]) -> Dict[str, str]: # Added return type
    _, email = test_user
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client() -> TestClient: # Added return type
    # Override the get_db dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]: # Added return type
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up
    app.dependency_overrides.clear()


# Tests
def test_upload_document(client: TestClient, test_user: Tuple[User, str], auth_headers: Dict[str, str], setup_db: Any) -> None: # Added return type
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