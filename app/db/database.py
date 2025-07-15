from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.db_models import Agent, Base


def get_async_db_url(sync_url: str) -> str:
    """Convert a synchronous PostgreSQL URL to an async one."""
    url_str = str(sync_url)  # Convert URL object to string first
    if url_str.startswith("postgresql://"):
        return url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url_str


# Create async engine and sessionmaker
db_url = str(settings.DATABASE_URI) if settings.DATABASE_URI else ""
async_engine = create_async_engine(
    get_async_db_url(db_url), echo=settings.DEBUG, future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync engine for initialization
# Use psycopg2 for synchronous operations
sync_engine = create_engine(
    str(settings.DATABASE_URI).replace("+asyncpg", ""), pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


# For FastAPI dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()



