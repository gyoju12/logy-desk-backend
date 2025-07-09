import os
import sys
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_and_migrate():
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("Error: DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    print(f"Database URL: {db_url}")
    
    # Create SQLAlchemy engine
    engine = create_engine(db_url)
    
    # Drop and recreate the database
    if database_exists(db_url):
        print("Dropping existing database...")
        drop_database(db_url)
    
    print("Creating new database...")
    create_database(db_url)
    
    # Set up Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Mark all migrations as done (since we're starting fresh)
    print("Marking migrations as applied...")
    command.stamp(alembic_cfg, "head")
    
    # Apply all migrations
    print("Applying migrations...")
    command.upgrade(alembic_cfg, "head")
    
    print("\nDatabase reset and migrations applied successfully!")

if __name__ == "__main__":
    reset_and_migrate()
