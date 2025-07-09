import pytest
from fastapi.testclient import TestClient
from app.main import app, API_PREFIX

# Test client fixture
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_documents_endpoint(client):
    """Test the documents endpoint returns a 401 when not authenticated"""
    response = client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 401  # Unauthorized
