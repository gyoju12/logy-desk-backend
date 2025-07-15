import os
import tempfile
from datetime import timedelta
from typing import Any, AsyncGenerator, Dict, Tuple
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base, SessionManager
from app.db.session import get_db
from app.main import API_PREFIX, app
from app.models.db_models import User

# Create async test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
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
async def setup_db() -> AsyncGenerator[None, None]:
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="module")
async def test_user() -> Tuple[User, str]:
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
async def auth_headers(test_user: Tuple[User, str]) -> Dict[str, str]:
    _, email = test_user
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # Override the get_db dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionManager(TestingSessionLocal()) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Tests
@pytest.mark.asyncio
async def test_upload_document(
    async_client: AsyncClient,
    test_user: Tuple[User, str],
    auth_headers: Dict[str, str],
    setup_db: Any,
) -> None:
    """Test uploading a document."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await async_client.post(
                f"{API_PREFIX}/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Document"
        assert data["filename"] == "test.txt"
        assert data["content_type"] == "text/plain"
        assert data["size"] > 0

    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_list_documents(
    async_client: AsyncClient,
    test_user: Tuple[User, str],
    auth_headers: Dict[str, str],
    setup_db: Any,
) -> None:
    """Test listing documents."""
    response = await async_client.get(f"{API_PREFIX}/documents", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) > 0
    doc = documents[0]
    assert "id" in doc
    assert "title" in doc
    assert "filename" in doc


@pytest.mark.asyncio
async def test_get_document(
    async_client: AsyncClient,
    test_user: Tuple[User, str],
    auth_headers: Dict[str, str],
    setup_db: Any,
) -> None:
    """Test getting a document."""
    # First create a document
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await async_client.post(
                f"{API_PREFIX}/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        doc_id = data["id"]

        # Now get the document
        response = await async_client.get(
            f"{API_PREFIX}/documents/{doc_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        doc = response.json()
        assert doc["id"] == doc_id
        assert doc["title"] == "Test Document"
        assert doc["filename"] == "test.txt"

    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_delete_document(
    async_client: AsyncClient,
    test_user: Tuple[User, str],
    auth_headers: Dict[str, str],
    setup_db: Any,
) -> None:
    """Test deleting a document."""
    # First create a document
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await async_client.post(
                f"{API_PREFIX}/documents/upload",
                headers=auth_headers,
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        doc_id = data["id"]

        # Now delete the document
        response = await async_client.delete(
            f"{API_PREFIX}/documents/{doc_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's gone
        response = await async_client.get(
            f"{API_PREFIX}/documents/{doc_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
