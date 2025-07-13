import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from tests.test_utils import patch_models_for_sqlite

# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,  # Enable SQL logging for debugging
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Patch models for SQLite compatibility before creating tables
patch_models_for_sqlite()

# Create test database tables
Base.metadata.create_all(bind=engine)


# Override the get_db dependency for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply the override
app.dependency_overrides[get_db] = override_get_db


# Create test client
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# Database session fixture
@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Fixture to create a test agent
@pytest.fixture
def test_agent(db_session):
    from app.crud import crud_agent
    from app.models.schemas import AgentCreate

    agent_data = AgentCreate(
        name="Test Agent",
        agent_type="sub",
        model="gpt-4",
        temperature=0.7,  # Fixed: temperature should be between 0 and 2
        system_prompt="Test system prompt",
    )
    return crud_agent.agent.create(db=db_session, obj_in=agent_data)


# Fixture to create a test chat session
@pytest.fixture
def test_chat_session(db_session, test_agent):
    from app.crud import crud_chat
    from app.models.schemas import ChatSessionCreate

    session_data = ChatSessionCreate(title="Test Chat", agent_id=test_agent.id)
    return crud_chat.chat_session.create(db=db_session, obj_in=session_data)
