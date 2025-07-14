from app.db.base import Base, async_engine


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


def test_connection() -> bool:
    """Test the database connection and print the result."""
    db_url = get_db_url()
    print(f"Testing connection to: {db_url}")

    try:
        engine = create_engine(db_url)
        with engine.connect():
            print("✅ Successfully connected to the database!")
            return True
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False


def create_tables() -> None:
    """Create all database tables."""
    from app.db.base import Base

    print("
Creating database tables...")
    try:
        Base.metadata.create_all(bind=async_engine)
        print("✅ Tables created successfully!")

        # List all tables
        inspector = inspect(async_engine)
        tables = inspector.get_table_names()
        print("
Tables in the database:")
        for table in tables:
            print(f"- {table}")

    except Exception as e:
        print(f"❌ Failed to create tables: {e}")


def main() -> None:
    print("=== Database Setup Utility ===
")


    # Test connection first
    if not test_connection():
        print(
            (
                "\nPlease check your database credentials and make sure "
                "PostgreSQL is running."
            )
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
