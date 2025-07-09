import os
import pytest
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from uuid import uuid4
from datetime import datetime

from app.main import app, API_PREFIX
from app.db.base import Base
from app.db.database import get_db, SQLALCHEMY_DATABASE_URL
from app.models.db_models import User, Document
from app.core.password_utils import get_password_hash
from app.core.security import create_access_token

# Override the database URL for testing
TEST_DATABASE_URL = "sqlite:///./test.db"
app.dependency_overrides[SQLALCHEMY_DATABASE_URL] = lambda: TEST_DATABASE_URL

# Create engine and session for testing
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override the get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create test database tables
@pytest.fixture(scope="module")
def setup_database():
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after tests
    Base.metadata.drop_all(bind=test_engine)

# Test client with database setup
@pytest.fixture(scope="module")
def client(setup_database):
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # Clean up
    app.dependency_overrides.clear()

# Test user fixture
@pytest.fixture(scope="module")
def test_user():
    db = TestingSessionLocal()
    try:
        # Clean up any existing users
        db.query(User).delete()
        
        # Create a test user
        email = f"test-{uuid4()}@example.com"
        user = User(
            id=str(uuid4()),
            email=email,
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, email
    finally:
        db.close()

def get_auth_headers(email: str):
    """Generate JWT token and return authorization headers"""
    token = create_access_token(data={"sub": email})
    return {"Authorization": f"Bearer {token}"}

def test_documents_endpoint_unauthorized(client):
    """Test the documents endpoint returns a 401 when not authenticated"""
    response = client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 401  # Unauthorized

def test_create_document(client, test_user):
    """Test creating a new document"""
    user, email = test_user
    headers = get_auth_headers(email)
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name
    
    try:
        with open(tmp_path, "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            response = client.post(
                f"{API_PREFIX}/documents/upload",
                headers=headers,
                files=files,
                data={"file_name": "test_document.txt"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test_document.txt"
        assert data["file_type"] == "text/plain"
        assert data["status"] == "uploaded"
        assert data["user_id"] == str(user.id)
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def test_list_documents(client, test_user):
    """Test listing documents"""
    user, email = test_user
    headers = get_auth_headers(email)
    
    # First, create a test document directly in the database
    db = TestingSessionLocal()
    try:
        document = Document(
            id=str(uuid4()),
            user_id=user.id,
            file_name="test_list.txt",
            file_path="/test/path.txt",
            file_size=123,
            file_type="text/plain",
            status="processed"
        )
        db.add(document)
        db.commit()
        
        # Now test the API endpoint
        response = client.get(
            f"{API_PREFIX}/documents/",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any(doc["file_name"] == "test_list.txt" for doc in data)
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_documents_sync.py"])
