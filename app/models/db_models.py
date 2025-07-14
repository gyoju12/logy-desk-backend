from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    types,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AgentType(str, Enum):
    """Enum for agent types."""

    MAIN = "MAIN"
    SUB = "SUB"


class AgentTypeDB(types.TypeDecorator):
    """Custom type to handle case-insensitive enum values.

    Maps between Python's AgentType enum and database's lowercase values.
    """

    impl = postgresql.ENUM("main", "sub", name="agenttype")
    cache_ok = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._enum_type = AgentType

    def process_bind_param(self, value: Any, dialect) -> str:
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower()
        return value.value.lower()

    def process_result_value(self, value: str, dialect) -> AgentType:
        if value is None:
            return None
        return self._enum_type(value.upper())


class Agent(Base):
    """Agent model for AI agents."""

    __tablename__ = "agents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    name = Column(String(100), nullable=False)
    agent_type = Column(AgentTypeDB, nullable=False, default=AgentType.SUB)
    model = Column(String(50), nullable=False)
    temperature = Column(Float, default=0.7)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="agents")

    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.agent_type}')>"


class User(Base):
    """User model for storing user accounts and authentication data."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email = Column(String(255), unique=True, nullable=False, index=True)

    # Relationships
    agents = relationship("Agent", back_populates="user")
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)

    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user")

    def __init__(
        self,
        email: str,
        hashed_password: str,
        is_active: bool = True,
        is_superuser: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_superuser = is_superuser

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Document(Base):
    """Document model for storing document metadata."""

    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(
        String(20), nullable=False, default="processing"
    )  # Status can be: 'processing', 'processed', 'error'
    error_message = Column(Text, nullable=True)
    document_metadata = Column(
        "metadata", JSONB, nullable=True
    )  # Renamed from metadata to document_metadata,
    # but keeping 'metadata' as the actual column name

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document")

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, file_name={self.file_name}, status={self.status}>"
        )


class DocumentChunk(Base):
    """Document chunks for RAG processing."""

    __tablename__ = "document_chunks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    vector_id = Column(String(100), nullable=True)  # Reference to vector in ChromaDB

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, "
            f"document_id={self.document_id}, "
            f"index={self.chunk_index})>"
        )


class ChatSession(Base):
    """Chat session model for grouping related chat messages."""

    __tablename__ = "chat_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        user_id: UUID,
        title: Optional[str] = None,
        is_active: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.title = title
        self.is_active = is_active

    def __repr__(self) -> str:
        return (
            f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
        )


class ChatMessage(Base):
    """Individual chat messages within a session."""

    __tablename__ = "chat_messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    message_metadata = Column(
        "metadata", JSONB, nullable=True
    )  # Renamed from metadata to message_metadata,
    # but keeping 'metadata' as the actual column name
    # Additional metadata as JSON

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"
