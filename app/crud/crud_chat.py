from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatSessionCreate,
    ChatSessionUpdate,
)

from .base import CRUDBase


class CRUDChatSession(CRUDBase[ChatSession, ChatSessionCreate, ChatSessionUpdate]):
    async def get_messages(
        self, db: AsyncSession, *, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_title(
        self, db: AsyncSession, *, title: str
    ) -> Optional[ChatSession]:
        result = await db.execute(
            select(self.model).where(self.model.title == title).limit(1)
        )
        return result.scalars().first()


class CRUDChatMessage(CRUDBase[ChatMessage, ChatMessageCreate, ChatMessageUpdate]):
    async def create_with_session(
        self, db: AsyncSession, *, obj_in: ChatMessageCreate, session_id: UUID
    ) -> ChatMessage:
        # Create model - let the database handle the timestamps
        db_obj = ChatMessage(
            **obj_in.dict(exclude={"created_at", "updated_at"}, exclude_unset=True),
            session_id=session_id,
        )

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_by_session(
        self, db: AsyncSession, *, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ChatMessage]:
        """
        특정 세션의 채팅 메시지 목록을 조회합니다.

        Args:
            db: 데이터베이스 세션
            session_id: 조회할 채팅 세션 ID
            skip: 건너뛸 레코드 수
            limit: 반환할 최대 레코드 수

        Returns:
            List[ChatMessage]: 조회된 채팅 메시지 목록
        """
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Create singleton instances
chat_session = CRUDChatSession(ChatSession)
chat_message = CRUDChatMessage(ChatMessage)
