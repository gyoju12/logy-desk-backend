import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings after adding to path
from app.core.config import settings

def reset_database():
    # Create a connection URL to the postgres database
    db_url = URL.create(
        "postgresql",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        database="postgres"  # Connect to the default 'postgres' database
    )
    
    # Create a synchronous engine
    engine = create_engine(db_url, isolation_level="AUTOCOMMIT")
    
    # Drop and recreate the database
    with engine.connect() as conn:
        # Terminate all connections to the target database
        conn.execute(text(
            f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
            f"FROM pg_stat_activity "
            f"WHERE pg_stat_activity.datname = '{settings.POSTGRES_DB}' "
            f"AND pid <> pg_backend_pid();"
        ))
        
        # Drop the database if it exists
        conn.execute(text(f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB}"))
        
        # Create a new database
        conn.execute(text(f"CREATE DATABASE {settings.POSTGRES_DB}"))
    
    print(f"✅ Database '{settings.POSTGRES_DB}' has been reset.")

if __name__ == "__main__":
    reset_database()
