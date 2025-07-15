from typing import Any, AsyncGenerator
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, SessionManager
from app.db.session import get_db
from app.main import app
from tests.test_utils import patch_models_for_sqlite

# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async test database engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,  # Enable SQL logging for debugging
)
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Patch models for SQLite compatibility before creating tables
patch_models_for_sqlite()


# Create test database tables
async def create_test_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Override the get_db dependency for testing
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionManager(TestingSessionLocal()) as session:
        yield session


# Create async test client fixture
@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Apply the override
app.dependency_overrides[get_db] = override_get_db


# Create test client
@pytest.fixture(scope="module")
async def client() -> AsyncGenerator[TestClient, None]:
    await create_test_tables()
    with TestClient(app) as c:
        yield c
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Database session fixture
@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


# Fixture to create a test agent
@pytest.fixture
async def test_agent(db_session: AsyncSession) -> Any:
    from app.crud import crud_agent
    from app.schemas.agent import AgentCreate

    agent_data = AgentCreate(
        user_id=UUID(
            "00000000-0000-0000-0000-000000000000"
        ),  # Default user ID for testing
        name="Test Agent",
        agent_type="MAIN",
        model="gpt-4",
        temperature=0.7,
        system_prompt="Test system prompt",
    )
    return await crud_agent.agent.create(db=db_session, obj_in=agent_data)


# Fixture to create a test chat session
@pytest.fixture
async def test_chat_session(db_session: AsyncSession, test_agent: Any) -> Any:
    from app.crud import crud_chat
    from app.schemas.chat import ChatSessionCreate

    session_data = ChatSessionCreate(
        user_id=UUID(
            "00000000-0000-0000-0000-000000000000"
        ),  # Default user ID for testing
        title="Test Chat",
    )
    return await crud_chat.chat_session.create(db=db_session, obj_in=session_data)
