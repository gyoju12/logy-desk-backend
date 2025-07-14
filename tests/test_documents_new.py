import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Any, AsyncGenerator, Generator

from app.db.base import Base
from app.main import API_PREFIX, app
from app.db.session import get_db # Import get_db
from app.core.config import settings # Import settings

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create engine and session for testing
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# Override the get_db dependency
def override_get_db() -> Generator[Any, Any, Any]: # Added return type
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create test database tables
@pytest.fixture(scope="module")
def setup_database() -> Generator[None, None, None]: # Added return type
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after tests
    Base.metadata.drop_all(bind=test_engine)


# Test client with database setup
@pytest.fixture(scope="module")
def client(setup_database: Any) -> Generator[TestClient, Any, Any]: # Added return type
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db # Correctly override get_db
    with TestClient(app) as c:
        yield c
    # Clean up
    app.dependency_overrides.clear()


def test_documents_endpoint_unauthorized(client: TestClient) -> None: # Added return type
    """Test the documents endpoint returns a 401 when not authenticated"""
    response = client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 401  # Unauthorized