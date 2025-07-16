import os
import sys

from dotenv import load_dotenv
from sqlalchemy_utils import create_database, database_exists, drop_database

from alembic import command
from alembic.config import Config

# Load environment variables
load_dotenv()


def reset_and_migrate() -> None:
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("Error: DATABASE_URL not found in environment variables")
        sys.exit(1)

    print(f"Database URL: {db_url}")

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
