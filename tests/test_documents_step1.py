import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_minimal():
    """A minimal test that should always pass."""
    assert True
