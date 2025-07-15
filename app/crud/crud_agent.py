from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Agent
from app.schemas.agent import AgentCreate, AgentUpdate

from .base import CRUDBase


class CRUDAgent(CRUDBase[Agent, AgentCreate, AgentUpdate]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Agent]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalars().first()

    async def get_multi_by_type(
        self, db: AsyncSession, *, agent_type: str, skip: int = 0, limit: int = 100
    ) -> List[Agent]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.agent_type == agent_type)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


agent = CRUDAgent(Agent)
