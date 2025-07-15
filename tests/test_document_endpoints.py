import os
import tempfile
from typing import Any, Generator
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base, SessionManager
from app.db.session import get_db
from app.main import app
from app.models.db_models import Document

# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test database engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,
)
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Create test client with overridden database session
@pytest.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Override get_db dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionManager(TestingSessionLocal()) as session:
            yield session

    # Store original dependency
    original_get_db = app.dependency_overrides.get(get_db, None)

    # Apply override
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        try:
            yield client
        finally:
            # Clean up
            app.dependency_overrides.clear()
            if original_get_db is not None:
                app.dependency_overrides[get_db] = original_get_db


# Clean up database between tests
@pytest.fixture(autouse=True)
async def cleanup() -> AsyncGenerator[None, None]:
    yield
    # Clean up database after each test
    async with SessionManager(TestingSessionLocal()) as db:
        try:
            await db.execute(text("DELETE FROM chat_messages"))
            await db.execute(text("DELETE FROM chat_sessions"))
            await db.execute(text("DELETE FROM documents"))
            await db.execute(text("DELETE FROM agents"))
            await db.commit()
        finally:
            await db.close()


# Fixture for creating a test document
@pytest.fixture
async def test_document() -> AsyncGenerator[Document, None]:
    """Create a test document in the database"""
    async with SessionManager(TestingSessionLocal()) as db:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp.write(b"Test document content")
            tmp_path = tmp.name

        try:
            # Create document in database
            db_document = Document(
                title="Test Document",
                filename=os.path.basename(tmp_path),
                content_type="text/plain",
                size=os.path.getsize(tmp_path),
            )
            db.add(db_document)
            await db.commit()
            await db.refresh(db_document)

            # Create uploads directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)

            # Move the temp file to uploads
            import shutil

            dest_path = os.path.join("uploads", os.path.basename(tmp_path))
            shutil.move(tmp_path, dest_path)

            yield db_document

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if os.path.exists(dest_path):
                os.unlink(dest_path)

            # Clean up database
            await db.query(Document).delete()
            await db.commit()


@pytest.mark.asyncio
async def test_upload_document(
    async_client: AsyncClient, test_document: Document
) -> None:
    """Test uploading a document"""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await async_client.post(
                "/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Document"
        assert data["filename"] == "test.txt"
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_list_documents(
    async_client: AsyncClient, test_document: Document
) -> None:
    """Test listing all documents"""
    response = await async_client.get("/documents")
    assert response.status_code == status.HTTP_200_OK
    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) > 0
    doc = documents[0]
    assert doc["id"] == str(test_document.id)
    assert doc["title"] == test_document.title
    assert doc["filename"] == test_document.filename


@pytest.mark.asyncio
async def test_get_document(
    async_client: AsyncClient, test_document: Document
) -> None:
    """Test getting a single document"""
    response = await async_client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_200_OK
    doc = response.json()
    assert doc["id"] == str(test_document.id)
    assert doc["title"] == test_document.title
    assert doc["filename"] == test_document.filename


@pytest.mark.asyncio
async def test_delete_document(
    async_client: AsyncClient, test_document: Document
) -> None:
    """Test deleting a document"""
    response = await async_client.delete(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the document is deleted
    response = await async_client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
