from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class DocumentBase(BaseModel):
    """Base schema for document metadata."""

    title: str = Field(..., description="Title of the document")
    filename: str = Field(..., description="Original filename of the uploaded document")
    content_type: Optional[str] = Field(None, description="MIME type of the document")
    size: Optional[int] = Field(None, ge=0, description="Size of the document in bytes")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    @validator("title")
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @validator("filename")
    def filename_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Filename cannot be empty")
        return v.strip()


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""

    title: Optional[str] = Field(None, description="New title for the document")
    filename: Optional[str] = Field(None, description="New filename for the document")
    content_type: Optional[str] = Field(
        None, description="New MIME type for the document"
    )
    size: Optional[int] = Field(
        None, ge=0, description="New size of the document in bytes"
    )


class Document(DocumentBase):
    """Schema for document metadata in the knowledge base."""

    id: str = Field(..., description="Unique identifier for the document")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the document was uploaded"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}
