from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import AsyncGenerator, Generator
from app.db.base import Base
from app.models.models import Agent
from app.core.config import settings

def get_async_db_url(sync_url) -> str:
    """Convert a synchronous PostgreSQL URL to an async one."""
    url_str = str(sync_url)  # Convert URL object to string first
    if url_str.startswith('postgresql://'):
        return url_str.replace('postgresql://', 'postgresql+asyncpg://', 1)
    return url_str

# Create async engine and sessionmaker
async_engine = create_async_engine(
    get_async_db_url(settings.DATABASE_URI),
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync engine for initialization
# Use psycopg2 for synchronous operations
sync_engine = create_engine(
    str(settings.DATABASE_URI).replace('+asyncpg', ''),
    pool_pre_ping=True
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

def init_db():
    """Initialize the database (synchronously)."""
    # Create all tables
    Base.metadata.create_all(bind=sync_engine)
    
    # Create a new session
    db = SessionLocal()
    
    try:
        # Create default main agent if it doesn't exist
        if not db.query(Agent).filter(Agent.id == "agent_001").first():
            default_agent = Agent(
                id="agent_001",
                name="기본 에이전트",
                agent_type="main",
                model="gpt-4",
                temperature=7,
                system_prompt="당신은 도움이 되는 AI 어시스턴트입니다."
            )
            db.add(default_agent)
            db.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()
