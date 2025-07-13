import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base

# Import FastAPI app and models
from app.main import app
from app.models.db_models import Document, User

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Setup test database
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test client
client = TestClient(app)

# Test user data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword"


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create a test user
    db = TestingSessionLocal()
    user = User(
        id=str(uuid.uuid4()),
        email=TEST_USER_EMAIL,
        hashed_password=get_password_hash(TEST_USER_PASSWORD),
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()

    yield db

    # Clean up
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    return test_db.query(User).filter(User.email == TEST_USER_EMAIL).first()


@pytest.fixture
def test_token(test_user):
    return create_access_token({"sub": test_user.email})


@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}


def test_unauthorized_documents():
    # Test without authentication
    response = client.get("/api/v1/documents")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_list_documents(test_db, auth_headers):
    # Create test documents
    user = test_db.query(User).filter(User.email == TEST_USER_EMAIL).first()

    document = Document(
        id=str(uuid.uuid4()),
        user_id=user.id,
        file_name="test_document.txt",
        file_path="/test/path/test_document.txt",
        file_size=1024,
        file_type="text/plain",
        status="uploaded",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(document)
    test_db.commit()

    # Test listing documents
    response = client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    documents = response.json()
    assert isinstance(documents, list)
    assert len(documents) > 0
    assert documents[0]["file_name"] == "test_document.txt"


def test_upload_document(auth_headers):
    # Test document upload
    test_file = ("test_file.txt", b"Test file content", "text/plain")
    files = {"file": test_file}
    data = {"file_name": "test_upload.txt"}

    response = client.post(
        "/api/v1/documents/upload", headers=auth_headers, files=files, data=data
    )

    assert response.status_code == 200
    result = response.json()
    assert result["file_name"] == "test_upload.txt"
    assert result["status"] == "uploaded"
