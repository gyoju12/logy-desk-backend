import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async database engine
DATABASE_URL = str(settings.DATABASE_URI)

# Create async engine with thread safety
async_engine = create_async_engine(
    DATABASE_URL,
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
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,  # SQLAlchemy 2.0 future compatibility
)

# Create sync session factory
sync_session_maker = sessionmaker(
    bind=async_engine.sync_engine,
    class_=Session,
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


# Dependency to get sync DB session
def get_sync_session() -> Session:
    """
    Dependency function that returns a synchronous database session.
    """
    return sync_session_maker()


# Initialize database
async def init_db() -> None:
    """Initialize the database with base data."""
    from app.db.base import Base
    from app.models.db_models import User  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        from app.crud.crud_user import user as user_crud
        from app.schemas.user import UserCreate

        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD

        async with async_session_maker() as db:
            db_user = await user_crud.get_by_email(db, email=admin_email)
            if not db_user:
                user_in = UserCreate(
                    email=admin_email,
                    password=admin_password,
                    is_superuser=True,
                    is_active=True,
                )
                await user_crud.create(db, obj_in=user_in)
                logger.info("Created default admin user")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        raise
