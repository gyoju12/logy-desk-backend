import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.main import app, API_PREFIX
from app.db.base import Base
from app.db.database import get_db
from app.models.db_models import User
from app.core.password_utils import get_password_hash

# Create async test database engine
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

# Override the get_db dependency
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

# Test client fixture with database override
@pytest.fixture(scope="module")
def client():
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # Clean up
    app.dependency_overrides.clear()

# Database setup and teardown
@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Test user fixture
@pytest.fixture(scope="module")
async def test_user():
    async with TestingSessionLocal() as db:
        email = f"test-{uuid4()}@example.com"
        user = User(
            email=email,
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user, email

def test_documents_endpoint(client, test_user):
    """Test the documents endpoint returns a 401 when not authenticated"""
    response = client.get(f"{API_PREFIX}/documents/")
    assert response.status_code == 401  # Unauthorized
