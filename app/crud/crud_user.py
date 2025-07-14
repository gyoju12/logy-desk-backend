from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

from .base import CRUDBase


class UserBase(BaseModel):
    email: str
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()


# Create a singleton instance
user = CRUDUser(User)

# For backward compatibility with existing imports
get_user_by_email = user.get_by_email
