import uuid
from datetime import datetime
from typing import Any, Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Import models
from app.db.base import Base
from app.models.db_models import Document, User

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine() -> Generator[Engine, None, None]:
    """Create a new in-memory SQLite database for each test function."""
    db_url = "sqlite:///:memory:"
    _engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield _engine
    _engine.dispose()


@pytest.fixture(scope="function")
def tables(engine: Engine) -> Generator[None, None, None]:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine: Engine, tables: Any) -> Generator[Session, None, None]:
    """Create a new database session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_db_connection(db_session: Session) -> None:
    # Simple test to verify database connection works
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_create_document(db_session: Session) -> None:
    # Create a test user
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()

    # Create a test document
    document = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="test_document.txt",
        file_path="/test/path/test_document.txt",
        file_size=1024,
        file_type="text/plain",
        status="uploaded",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(document)
    db_session.commit()

    # Verify the document was created
    db_document = db_session.query(Document).filter(Document.id == document.id).first()
    assert db_document is not None
    assert db_document.file_name == "test_document.txt"
    assert db_document.user_id == user.id
    assert db_document.status == "uploaded"
