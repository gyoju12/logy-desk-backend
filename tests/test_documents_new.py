import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, API_PREFIX
from app.db.base import Base
from app.db.database import SQLALCHEMY_DATABASE_URL

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
app.dependency_overrides[SQLALCHEMY_DATABASE_URL] = lambda: TEST_DATABASE_URL

# Create engine and session for testing
test_engine = create_engine(TEST_DATABASE_URL)
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
    app.dependency_overrides[app.dependency_overrides[SQLALCHEMY_DATABASE_URL]] = override_get_db
    with TestClient(app) as c:
        yield c
    # Clean up
    app.dependency_overrides.clear()

def test_documents_endpoint_unauthorized(client):
    """Test the documents endpoint returns a 401 when not authenticated"""
    response = client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 401  # Unauthorized
