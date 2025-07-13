import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy_utils import create_database, database_exists

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()


def get_db_url() -> str:
    """Get the database URL from environment variables."""
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
        f"{os.getenv('POSTGRES_SERVER', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'logydesk')}"
    )


def test_connection():
    """Test the database connection and print the result."""
    db_url = get_db_url()
    print(f"Testing connection to: {db_url}")

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("✅ Successfully connected to the database!")
            return True
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False


def create_tables():
    """Create all database tables."""
    from app.db.base import Base
    from app.db.session import engine

    print("\nCreating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")

        # List all tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("\nTables in the database:")
        for table in tables:
            print(f"- {table}")

    except Exception as e:
        print(f"❌ Failed to create tables: {e}")


def main():
    print("=== Database Setup Utility ===\n")

    # Test connection first
    if not test_connection():
        print(
            "\nPlease check your database credentials and make sure PostgreSQL is running."
        )
        print(
            "You may need to create a .env file with the correct database credentials."
        )
        return

    # Create tables
    create_tables()

    print("\n=== Database setup complete! ===")


if __name__ == "__main__":
    main()
