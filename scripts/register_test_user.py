#!/usr/bin/env python3
"""
Script to register a test user if they don't exist.
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal
from app.models.db_models import User

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    """Create a test user if they don't exist."""
    email = "test@example.com"
    password = "testpassword123"

    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(select(User).filter(User.email == email))
        user = result.scalars().first()

        if user is None:
            # Create new user
            hashed_password = get_password_hash(password)
            user = User(email=email, hashed_password=hashed_password, is_active=True)
            session.add(user)
            await session.commit()
            print(f"✅ Created test user: {email}")
        else:
            print(f"ℹ️ Test user already exists: {email}")


if __name__ == "__main__":
    asyncio.run(main())
