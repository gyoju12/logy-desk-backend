import sys
import os
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

def init_db():
    from app.db.base import Base
    from app.db.session import engine
    
    # Database configuration
    db_url = str(engine.url)
    
    print(f"Initializing database at: {db_url}")
    
    # Drop and recreate the database
    if database_exists(db_url):
        print("Dropping existing database...")
        drop_database(db_url)
    
    print("Creating new database...")
    create_database(db_url)
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    print("\n✅ Database initialized successfully!")
    print("The following tables were created:")
    
    # List all tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    for table in tables:
        print(f"- {table}")
    
    print("\nDatabase initialization complete!")

if __name__ == "__main__":
    init_db()
