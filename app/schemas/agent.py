from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    name: str = Field(..., description="Name of the agent")
    agent_type: str = Field(..., description="Type of the agent (e.g., 'main', 'sub')")
    model: str = Field(..., description="Model used by the agent")
    temperature: float = Field(
        0.7, description="Temperature setting for the agent's responses"
    )
    system_prompt: Optional[str] = Field(
        None, description="System prompt for the agent"
    )


class AgentCreate(AgentBase):
    user_id: Optional[UUID] = Field(None, description="ID of the user who owns this agent")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="New name for the agent")
    agent_type: Optional[str] = Field(None, description="New type for the agent")
    model: Optional[str] = Field(None, description="New model for the agent")
    temperature: Optional[float] = Field(
        None, description="New temperature for the agent"
    )
    system_prompt: Optional[str] = Field(
        None, description="New system prompt for the agent"
    )


class AgentInDBBase(AgentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Agent(AgentInDBBase):
    pass


class AgentList(BaseModel):
    items: list[Agent]
    total: int
    skip: int
    limit: int
