import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import FastAPI app
from app.main import app
from app.db.base import Base

# Setup test database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test client
client = TestClient(app)

def test_health_check():
    # Test basic health check endpoint
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_unauthorized_documents():
    # Test documents endpoint without authentication
    response = client.get("/api/v1/documents")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

if __name__ == "__main__":
    # Create tables before running tests
    Base.metadata.create_all(bind=engine)
    
    # Run tests
    pytest.main(["-v", __file__])
    
    # Clean up
    Base.metadata.drop_all(bind=engine)
