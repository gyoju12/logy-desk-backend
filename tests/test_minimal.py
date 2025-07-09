import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_minimal():
    """A minimal test to verify the test setup works."""
    assert True

@pytest.mark.asyncio
async def test_async_minimal():
    """A minimal async test to verify async test setup works."""
    assert True

class TestClientClass:
    def test_client(self):
        """Test that the FastAPI test client works."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code in [200, 404]  # 200 if / exists, 404 otherwise
