from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

# Common types
AgentType = Literal["main", "sub"]
MessageRole = Literal["user", "assistant"]

# Base schemas
class AgentBase(BaseModel):
    """Base schema for Agent with common fields."""
    name: str = Field(..., description="Name of the agent")
    agent_type: AgentType = Field(..., description="Type of agent (main or sub)")
    model: str = Field(..., description="Model identifier used by the agent")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)")
    system_prompt: str = Field(..., description="System prompt defining the agent's role and behavior")

class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    pass

class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""
    name: Optional[str] = Field(None, description="Updated name of the agent")
    model: Optional[str] = Field(None, description="Updated model identifier")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Updated sampling temperature")
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")

class Agent(AgentBase):
    """Complete agent schema including database fields."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the agent")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat()
        }

# Document schemas
class Document(BaseModel):
    """Schema for document metadata in the knowledge base."""
    id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Original filename of the uploaded document")
    uploaded_at: datetime = Field(..., description="Timestamp when the document was uploaded")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Chat session schemas
class ChatMessage(BaseModel):
    """Schema for a single chat message."""
    role: MessageRole = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Content of the message")

class ChatSessionBase(BaseModel):
    """Base schema for chat session."""
    title: str = Field(..., description="Title or summary of the chat session")

class ChatSession(ChatSessionBase):
    """Schema for chat session metadata."""
    id: str = Field(..., description="Unique identifier for the chat session")
    created_at: datetime = Field(..., description="Creation timestamp of the session")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ChatSessionDetail(ChatSession):
    """Schema for chat session including all messages."""
    messages: List[ChatMessage] = Field(..., description="List of messages in the session")

# Chat request/response schemas
class ChatRequest(BaseModel):
    """Schema for chat request payload."""
    user_message: str = Field(..., description="The message content from the user")
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for continuing a conversation. If not provided, a new session will be created."
    )

class ChatResponse(BaseModel):
    """Schema for chat response."""
    session_id: str = Field(..., description="ID of the chat session")
    response: str = Field(..., description="The assistant's response message")
    metadata: Optional[dict] = Field(
        None,
        description="Additional metadata about the response, such as which agents were used"
    )

# Response models for API endpoints
class ListResponse(BaseModel):
    """Generic list response wrapper."""
    items: List[BaseModel]

class AgentListResponse(BaseModel):
    """Response model for listing agents."""
    agents: List[Agent]

class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[Document]

class ChatSessionListResponse(BaseModel):
    """Response model for listing chat sessions."""
    sessions: List[ChatSession]
