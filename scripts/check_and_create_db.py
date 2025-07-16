import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists


def ensure_database() -> None:
    # Load environment variables
    load_dotenv()

    # Get database configuration
    db_config = {
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "host": os.getenv("POSTGRES_SERVER", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "db": os.getenv("POSTGRES_DB", "logydesk"),
    }

    # Create base URL without database name
    base_url = (
        f"postgresql://{db_config['user']}:"
        f"{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}"
    )
    db_url = f"{base_url}/{db_config['db']}"

    print(f"Checking database: {db_url}")

    # Check if database exists
    if not database_exists(db_url):
        print(f"Database {db_config['db']} does not exist. Creating...")
        create_database(db_url)
        print(f"Database {db_config['db']} created successfully.")
    else:
        print(f"Database {db_config['db']} already exists.")

    # Check if we can connect
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("✅ Successfully connected to the database.")

            # Check if tables exist
            tables = engine.dialect.get_table_names(conn)
            if tables:
                print("\nTables in the database:")
                for table in tables:
                    print(f"- {table}")
            else:
                print("\nNo tables found in the database.")

    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    ensure_database()
