import logging
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker as create_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async database engine
DATABASE_URL = str(settings.DATABASE_URI)

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    poolclass=NullPool if settings.TESTING else None,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Dependency to get DB session
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
            logger.error(f"Database error: {str(e)}")
            raise


def get_sync_session():
    engine = create_engine(
        str(settings.DATABASE_URI).replace("+asyncpg", ""),
        pool_pre_ping=True,
    )
    return create_sessionmaker(autocommit=False, autoflush=False, bind=engine)()


# Initialize database
async def init_db() -> None:
    """Initialize the database with base data."""
    # Import models to ensure they are registered with SQLAlchemy
    from app.db.base import Base
    from app.models.db_models import User  # noqa: F401

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user if not exists
    try:
        from app.crud.crud_user import create_user, get_user_by_email
        from app.schemas.user import UserCreate

        admin_email = "admin@example.com"
        admin_password = "admin123"

        async with async_session_maker() as db:
            admin = await get_user_by_email(db, email=admin_email)
            if not admin:
                user_in = UserCreate(
                    email=admin_email,
                    password=admin_password,
                    is_superuser=True,
                    is_active=True,
                )
                await create_user(db, user_in=user_in)
                print("Created default admin user")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        raise
