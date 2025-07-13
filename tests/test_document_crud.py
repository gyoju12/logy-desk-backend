import os
import tempfile

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.models import Document

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
def client():
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Override get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_document():
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


def test_upload_document(client):
    """Test uploading a document"""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
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


def test_list_documents(client, test_document):
    """Test listing all documents"""
    response = client.get("/documents")
    assert response.status_code == status.HTTP_200_OK

    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) == 1
    assert documents[0]["id"] == str(test_document.id)
    assert documents[0]["title"] == test_document.title


def test_get_document(client, test_document):
    """Test getting a document by ID"""
    response = client.get(f"/documents/{test_document.id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == str(test_document.id)
    assert data["title"] == test_document.title
    assert data["filename"] == test_document.filename


def test_delete_document(client, test_document):
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
