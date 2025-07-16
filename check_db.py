import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

try:
    from app.core.config import settings
    from app.db.base import async_engine
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Current Python path:", sys.path)
    print("Current working directory:", os.getcwd())
    raise


async def check_db_connection() -> None:
    print("🔍 Checking database connection...")
    print(f"📌 Current working directory: {os.getcwd()}")
    print(f"📌 Python path: {sys.path}")

    try:
        print(f"🔗 Database URL: {settings.DATABASE_URI}")
        print("🔄 Attempting to connect to the database...")

        # Test connection with async engine
        async with async_engine.connect() as conn:
            print("✅ Successfully connected to the database!")
            print("🔍 Running test query...")
            result = await conn.execute(text("SELECT 1"))
            test_result = result.scalar()
            print(f"✅ Test query successful! Result: {test_result}")

            # Get database version
            result = await conn.execute(text("SELECT version()"))
            db_version = result.scalar()
            print(f"📊 Database version: {db_version}")

    except Exception as e:
        print("❌ Database connection failed!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if the database server is running")
        print("2. Verify the database credentials in your .env file")
        print("3. Check if the database exists and is accessible")
        print("4. Ensure the database user has the correct permissions")
        print("5. Check your network connection to the database server")


if __name__ == "__main__":
    print("🚀 Starting database connection test...\n")
    try:
        asyncio.run(check_db_connection())
    except Exception as e:
        print(f"\n❌ Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    print("\n✨ Database check completed!")
