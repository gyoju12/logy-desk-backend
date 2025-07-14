from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base schema for document operations."""

    title: str = Field(..., description="Title of the document")
    file_name: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path where the file is stored")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_type: str = Field(..., description="MIME type of the file")
    status: str = Field("processing", description="Processing status of the document")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    document_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    user_id: UUID = Field(..., description="ID of the user who owns this document")


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""

    title: Optional[str] = Field(None, description="New title for the document")
    status: Optional[str] = Field(None, description="Updated processing status")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    document_metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class DocumentInDBBase(DocumentBase):
    """Base schema for documents stored in the database."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    """Schema for document responses."""

    pass


class DocumentInDB(DocumentInDBBase):
    """Schema for documents retrieved from the database."""

    pass


class DocumentList(BaseModel):
    """Schema for a list of documents with pagination info."""

    items: List[Document] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    skip: int = Field(0, description="Number of documents skipped")
    limit: int = Field(100, description="Maximum number of documents returned")
