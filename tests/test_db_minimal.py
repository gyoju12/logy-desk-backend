import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import models
from app.db.base import Base
from app.models.db_models import User, Document

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_db_connection(db_session):
    # Simple test to verify database connection works
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_create_document(db_session):
    # Create a test user
    user = User(
        id=str(uuid.uuid4()),
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
        id=str(uuid.uuid4()),
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
