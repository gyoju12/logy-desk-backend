import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


def get_async_db_url(sync_url: str) -> str:
    """Convert a synchronous PostgreSQL URL to an async one."""
    url_str = str(sync_url)  # Convert URL object to string first
    if url_str.startswith("postgresql://"):
        return url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url_str.startswith("postgresql+asyncpg://"):
        return f"postgresql+asyncpg://{url_str.split('://')[-1]}"
    return url_str


# Create async engine with thread safety
async_engine = create_async_engine(
    get_async_db_url(str(settings.DATABASE_URI)),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    poolclass=NullPool if settings.TESTING else None,
    connect_args=(
        {"check_same_thread": False} if settings.TESTING else {}
    ),  # SQLite thread safety fix
)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    future=True,  # SQLAlchemy 2.0 future compatibility
)

# Create sync engine for migrations
sync_engine = create_engine(
    str(settings.DATABASE_URI).replace("+asyncpg", ""),
    pool_pre_ping=True,
)

# Create sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Base class for all models
Base = declarative_base()

# SQLAlchemy 2.0 Model Base
Model = DeclarativeBase

# SQLAlchemy 2.0 Session
Session = AsyncSession

# SQLAlchemy 2.0 Session Maker
SessionMaker = async_sessionmaker

# SQLAlchemy 2.0 Engine
Engine = create_async_engine


# SQLAlchemy 2.0 Session Context Manager
class SessionManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()


# Async session dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields database sessions.
    Handles session lifecycle and ensures proper cleanup.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger = logging.getLogger(__name__)
            logger.error(f"Database error: {str(e)}")
            raise


# Sync session for migrations and testing
def get_sync_db() -> Generator[Session, None, None]:
    """
    Synchronous database session for migrations and testing.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger = logging.getLogger(__name__)
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()
