from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

# Common types
AgentType = Literal["MAIN", "SUB"]
MessageRole = Literal["system", "user", "assistant"]


# Base schemas
class AgentBase(BaseModel):
    """Base schema for Agent with common fields."""

    name: str = Field(..., description="Name of the agent")
    agent_type: AgentType = Field(..., description="Type of agent (main or sub)")
    model: str = Field(..., description="Model identifier used by the agent")
    temperature: float = Field(
        ..., ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)"
    )
    system_prompt: str = Field(
        ..., description="System prompt defining the agent's role and behavior"
    )


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""

    pass


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""

    name: Optional[str] = Field(None, description="Updated name of the agent")
    model: Optional[str] = Field(None, description="Updated model identifier")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Updated sampling temperature"
    )
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")


class Agent(AgentBase):
    """Complete agent schema including database fields."""

    id: UUID = Field(..., description="Unique identifier for the agent")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    # Override agent_type to use Any to avoid validation issues
    agent_type: Any = Field(..., description="Type of agent (MAIN or SUB)")

    @field_serializer("id")
    def serialize_id(self, id: UUID, _info) -> str:
        return str(id)

    @field_serializer("agent_type")
    def serialize_agent_type(self, agent_type: Any, _info) -> str:
        # Convert enum to string value
        if hasattr(agent_type, "value"):
            return agent_type.value
        # Ensure string is uppercase for consistency
        if isinstance(agent_type, str):
            return agent_type.upper()
        return str(agent_type)

    @field_validator("agent_type", mode="before")
    def validate_agent_type(cls, v):
        # Convert string to uppercase for consistency
        if isinstance(v, str):
            v = v.upper()
        # Convert enum to its value
        if hasattr(v, "value"):
            v = v.value
        # Ensure the value is one of the allowed values
        if v not in ["MAIN", "SUB"]:
            raise ValueError("agent_type must be either 'MAIN' or 'SUB'")
        return v

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


# Document schemas
class DocumentBase(BaseModel):
    """Base schema for document metadata."""

    filename: str = Field(..., description="Original filename of the uploaded document")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""

    filename: Optional[str] = Field(None, description="New filename for the document")


class Document(DocumentBase):
    """Schema for document metadata in the knowledge base."""

    id: UUID = Field(..., description="Unique identifier for the document")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the document was uploaded"
    )

    @field_serializer("id")
    def serialize_id(self, id: UUID, _info) -> str:
        return str(id)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


# Chat session schemas
class ChatMessageBase(BaseModel):
    """Base schema for a chat message."""

    role: MessageRole = Field(
        ..., description="Role of the message sender (user/assistant)"
    )
    content: str = Field(..., description="Content of the message")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message."""

    pass


class ChatMessageUpdate(BaseModel):
    """Schema for updating a chat message."""

    role: Optional[MessageRole] = Field(
        None, description="Updated role of the message sender"
    )
    content: Optional[str] = Field(None, description="Updated content of the message")


class ChatMessage(ChatMessageBase):
    """Schema for a chat message with database fields."""

    id: UUID = Field(..., description="Unique identifier for the message")
    session_id: UUID = Field(
        ..., description="ID of the chat session this message belongs to"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the message was created"
    )

    @field_serializer("id", "session_id")
    def serialize_uuids(self, v: UUID, _info) -> str:
        return str(v)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ChatSessionBase(BaseModel):
    """Base schema for chat session."""

    title: str = Field(..., description="Title or summary of the chat session")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a new chat session."""

    pass


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""

    title: Optional[str] = Field(
        None, description="Updated title or summary of the chat session"
    )


class ChatSession(ChatSessionBase):
    """Schema for chat session metadata."""

    id: UUID = Field(..., description="Unique identifier for the chat session")
    created_at: datetime = Field(..., description="Creation timestamp of the session")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_serializer("id")
    def serialize_id(self, id: UUID, _info) -> str:
        return str(id)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ChatSessionDetail(BaseModel):
    """Schema for chat session including all messages."""

    id: UUID = Field(..., description="Unique identifier for the chat session")
    created_at: datetime = Field(..., description="Creation timestamp of the session")
    updated_at: datetime = Field(..., description="Last update timestamp")
    title: str = Field(..., description="Title or summary of the chat session")
    messages: List[ChatMessage] = Field(
        ..., description="List of messages in the session"
    )

    @field_serializer("id")
    def serialize_id(self, id: UUID, _info) -> str:
        return str(id)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


# Chat request/response schemas
class ChatRequest(BaseModel):
    """Schema for chat request payload."""

    user_message: str = Field(..., description="The message content from the user")
    session_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional session ID for continuing a conversation. "
            "If not provided, a new session will be created."
        ),
    )


class ChatResponse(BaseModel):
    """Schema for chat response."""

    session_id: UUID = Field(..., description="ID of the chat session")
    response: str = Field(..., description="The assistant's response message")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the response, such as which agents were used",
    )


# Response models for API endpoints
class ListResponse(BaseModel):
    """Generic list response wrapper."""

    items: List[BaseModel]


class AgentListResponse(ListResponse):
    """Response model for listing agents."""

    agents: List[Agent]


class DocumentListResponse(ListResponse):
    """Response model for listing documents."""

    documents: List[Document]


class ChatSessionListResponse(ListResponse):
    """Response model for listing chat sessions."""

    sessions: List[ChatSession]
