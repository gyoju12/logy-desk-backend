import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from sqlalchemy import text

from app.db.session import async_session_maker


async def check_default_user():
    print("🔍 Checking if default user exists...")

    async with async_session_maker() as session:
        try:
            # Check if the default user exists
            result = await session.execute(
                text(
                    "SELECT id, email, is_active, is_superuser FROM users WHERE id = '00000000-0000-0000-0000-000000000000'"
                )
            )
            user = result.first()

            if user:
                print("✅ Default user found:")
                print(f"   ID: {user.id}")
                print(f"   Email: {user.email}")
                print(f"   Is Active: {user.is_active}")
                print(f"   Is Superuser: {user.is_superuser}")
            else:
                print("❌ Default user not found in the database")

            # Count total users
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"\n👥 Total users in database: {count}")

        except Exception as e:
            print(f"❌ Error checking default user: {str(e)}")
            raise


if __name__ == "__main__":
    print("🔍 Starting database check...")
    asyncio.run(check_default_user())
