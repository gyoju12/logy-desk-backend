from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.db_models import DocumentProcessingStatus, DocumentType


class DocumentBase(BaseModel):
    """Base schema for document operations."""

    file_name: str = Field(..., description="Original filename")
    processing_status: DocumentProcessingStatus = Field(
        DocumentProcessingStatus.PENDING, description="Processing status of the document"
    )
    summary: Optional[str] = Field(None, description="AI-generated summary of the document")
    doc_type: Optional[DocumentType] = Field(None, description="Classification type of the document")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    user_id: UUID = Field(..., description="ID of the user who owns this document")


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""

    processing_status: Optional[DocumentProcessingStatus] = Field(
        None, description="Updated processing status"
    )
    summary: Optional[str] = Field(None, description="Updated AI-generated summary")
    doc_type: Optional[DocumentType] = Field(None, description="Updated classification type")


class DocumentInDBBase(DocumentBase):
    """Base schema for documents stored in the database."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    """Schema for returning a document."""
    pass


class DocumentInDB(DocumentInDBBase):
    """Schema for documents retrieved from the database."""
    pass


class DocumentChunkBase(BaseModel):
    """Base schema for document chunk operations."""
    document_id: UUID = Field(..., description="ID of the parent document")
    content: str = Field(..., description="Content of the document chunk")
    embedding_status: DocumentProcessingStatus = Field(
        DocumentProcessingStatus.PENDING, description="Embedding status of the chunk"
    )
    num_tokens: int = Field(..., description="Number of tokens in the chunk")


class DocumentChunkCreate(DocumentChunkBase):
    """Schema for creating a new document chunk."""
    pass


class DocumentChunkUpdate(BaseModel):
    """Schema for updating an existing document chunk."""
    embedding_status: Optional[DocumentProcessingStatus] = Field(
        None, description="Updated embedding status"
    )


class DocumentChunkInDBBase(DocumentChunkBase):
    """Base schema for document chunks stored in the database."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunk(DocumentChunkInDBBase):
    """Schema for returning a document chunk."""
    pass


class DocumentChunkInDB(DocumentChunkInDBBase):
    """Schema for document chunks retrieved from the database."""
    pass


class DocumentList(BaseModel):
    """Schema for a list of documents with pagination info."""
    
    items: List[Document] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    skip: int = Field(0, description="Number of documents skipped")
    limit: int = Field(100, description="Maximum number of documents returned")