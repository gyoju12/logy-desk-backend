from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    types,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._enum_type: Type[AgentType] = AgentType

    def process_bind_param(
        self, value: Optional[AgentType], dialect: Any
    ) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower()
        return value.value.lower()

    def process_result_value(
        self, value: Optional[str], dialect: Any
    ) -> Optional[AgentType]:
        if value is None:
            return None
        return self._enum_type(value.upper())


class Agent(Base):
    """Agent model for AI agents."""

    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(
        AgentTypeDB, nullable=False, default=AgentType.SUB
    )
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="agents")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.agent_type}')>"


class User(Base):
    """User model for storing user accounts and authentication data."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Relationships
    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="user")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False)

    # Relationships
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user"
    )

    def __init__(
        self,
        email: str,
        hashed_password: str,
        is_active: bool = True,
        is_superuser: bool = False,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_superuser = is_superuser

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class DocumentProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    MANUAL = "MANUAL"
    FAQ = "FAQ"
    # Add other types as needed


class Document(Base):
    """Document model for storing document metadata."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        String(20), nullable=False, default=DocumentProcessingStatus.PENDING
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    doc_type: Mapped[Optional[DocumentType]] = mapped_column(
        String(50), nullable=True
    )

    # Relationships
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, file_name='{self.file_name}', status='{self.processing_status}')>"


class DocumentChunk(Base):
    """DocumentChunk model for storing document chunks and their embedding status."""

    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_status: Mapped[DocumentProcessingStatus] = mapped_column(
        String(20), nullable=False, default=DocumentProcessingStatus.PENDING
    )
    num_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks"
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, status='{self.embedding_status}')>"


class ChatSession(Base):
    """Chat session model for grouping related chat messages."""

    __tablename__ = "chat_sessions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        user_id: UUID,
        title: Optional[str] = None,
        is_active: bool = True,
        **kwargs: Any,
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

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'user', 'assistant', 'system', 'tool'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )  # Renamed from metadata to message_metadata,
    # but keeping 'metadata' as the actual column name
    # Additional metadata as JSON

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"
