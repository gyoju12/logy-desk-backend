from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ===============================================================================
# Chat Message Schemas
# ===============================================================================


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""

    role: str = Field(
        ..., description="The role of the message sender (e.g., 'user', 'assistant')."
    )
    content: str = Field(..., description="The content of the message.")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""

    pass


class ChatMessageUpdate(BaseModel):
    """Schema for updating a chat message."""

    content: Optional[str] = None


class ChatMessageInDBBase(ChatMessageBase):
    """Base schema for chat messages stored in the database."""

    id: UUID
    session_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(ChatMessageInDBBase):
    """Schema for representing a chat message."""

    pass


# ===============================================================================
# Chat Session Schemas
# ===============================================================================


class ChatSessionBase(BaseModel):
    """Base schema for chat sessions."""

    title: str = Field(..., description="The title of the chat session.")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a new chat session."""

    user_id: UUID


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""

    title: Optional[str] = None


class ChatSessionInDBBase(ChatSessionBase):
    """Base schema for chat sessions stored in the database."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSession(ChatSessionInDBBase):
    """Schema for representing a chat session."""

    pass


class ChatSessionDetail(ChatSessionInDBBase):
    """Schema for representing a chat session with all its messages."""

    messages: List[ChatMessage] = Field(
        ..., description="The messages in this session."
    )
