import os
import tempfile
from typing import Any, Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db # Changed import
from app.main import app
from app.models.db_models import Document

# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create test client with overridden database session
@pytest.fixture(scope="module")
def client() -> Generator[TestClient, Any, Any]: # Added return type
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Override get_db dependency
    def override_get_db() -> Generator[Session, Any, Any]: # Added return type
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Store original dependency
    original_get_db = app.dependency_overrides.get(get_db, None)

    # Apply override
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        try:
            yield c
        finally:
            # Clean up
            app.dependency_overrides.clear()
            if original_get_db is not None:
                app.dependency_overrides[get_db] = original_get_db


# Clean up database between tests
@pytest.fixture(autouse=True)
def cleanup() -> Generator[None, None, None]: # Added return type
    yield
    # Clean up database after each test
    db = TestingSessionLocal()
    try:
        db.execute(text("DELETE FROM chat_messages"))
        db.execute(text("DELETE FROM chat_sessions"))
        db.execute(text("DELETE FROM documents"))
        db.execute(text("DELETE FROM agents"))
        db.commit()
    finally:
        db.close()


# Fixture for creating a test document
@pytest.fixture
def test_document() -> Generator[Document, Any, Any]: # Added return type
    """Create a test document in the database"""
    db = TestingSessionLocal()

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
        db.commit()
        db.refresh(db_document)

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
        db.query(Document).delete()
        db.commit()
        db.close()


def test_upload_document(client: TestClient, tmp_path: Any) -> None: # Added return type
    """Test uploading a document"""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test document content")

    with open(test_file, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("test.txt", f, "text/plain")},
            data={"title": "Test Upload"},
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Upload"
    assert data["filename"].endswith(".txt")
    assert data["content_type"] == "text/plain"
    assert data["size"] > 0

    # Clean up
    doc_id = data["id"]
    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_list_documents(client: TestClient, test_document: Document) -> None: # Added return type
    """Test listing all documents"""
    response = client.get("/documents")
    assert response.status_code == status.HTTP_200_OK

    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) == 1
    assert documents[0]["id"] == str(test_document.id)
    assert documents[0]["title"] == test_document.title


def test_get_document(client: TestClient, test_document: Document) -> None: # Added return type
    """Test getting a document by ID"""
    response = client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(test_document.id)
    assert data["title"] == test_document.title
    assert data["filename"] == test_document.filename


def test_delete_document(client: TestClient, test_document: Document) -> None: # Added return type
    """Test deleting a document"""
    # First verify the document exists
    response = client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_200_OK

    # Delete the document
    response = client.delete(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's gone
    response = client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND