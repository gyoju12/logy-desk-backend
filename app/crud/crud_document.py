from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document
from app.schemas.document import DocumentCreate, DocumentUpdate

from .base import CRUDBase


class CRUDDocument(CRUDBase[Document, DocumentCreate, DocumentUpdate]):
    def __init__(self) -> None:
        super().__init__(Document)

    async def get_by_filename(
        self, db: AsyncSession, *, filename: str
    ) -> Optional[Document]:
        result = await db.execute(
            select(self.model).filter(self.model.file_name == filename)
        )
        return result.scalars().first()

    async def get_multi_by_owner(
        self, db: AsyncSession, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Document]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_multi_by_type(
        self, db: AsyncSession, *, file_type: str, skip: int = 0, limit: int = 100
    ) -> List[Document]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.file_type.like(f"{file_type}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self,
        db: AsyncSession,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        result = await db.execute(
            select(self.model)
            .filter(
                self.model.file_name.ilike(f"%{query}%")
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


# Create singleton instance
document = CRUDDocument()
