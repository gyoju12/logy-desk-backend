import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_document
from app.db.session import get_db
from app.models.schemas import DocumentCreate, Document as DocumentSchema # Import DocumentSchema

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000") # Changed to UUID object

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# File upload directory configuration
UPLOAD_DIR = "uploads"
# Ensure upload directory exists and is writable
try:
    upload_path = Path(UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    # Test if directory is writable
    test_file = upload_path / ".test"
    test_file.touch()
    test_file.unlink()
    logger.info(f"Upload directory is ready at: {upload_path.absolute()}")
except Exception as e:
    logger.error(f"Failed to initialize upload directory: {str(e)}")
    raise RuntimeError(f"Failed to initialize upload directory: {str(e)}")


async def _save_uploaded_file(
    file: UploadFile, upload_path: Path
) -> Tuple[bytes, Path]:
    """Save the uploaded file to disk and return its contents and path."""
    file_extension = os.path.splitext(file.filename or "")[1]
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_extension}"
    file_path = upload_path / filename

    logger.info(f"Starting file upload: {file.filename} (saving as {filename})")

    try:
        contents = await file.read()
        logger.info(f"Read {len(contents)} bytes from uploaded file")

        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        logger.info(f"File saved to {file_path}")

        return contents, file_path
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        error_type = "reading" if "read" in str(e).lower() else "saving"
        error_msg = f"Failed to {error_type} uploaded file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
                if error_type == "saving"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=error_msg,
        )


async def _save_document_to_db(
    db: AsyncSession, user_id: UUID, file: UploadFile, file_path: Path, file_size: int
) -> DocumentSchema: # Changed return type to DocumentSchema
    """Save document metadata to the database and return the created document."""
    document_data = DocumentCreate( # Changed to DocumentCreate instance
        filename=file.filename or "unknown", # Ensure filename is not None
        title=file.filename or "Untitled Document", # Added title
        content_type=file.content_type or "application/octet-stream", # Ensure content_type is not None
        size=file_size,
    )

    logger.debug(f"Document metadata: {document_data.model_dump_json()}") # Use model_dump_json
    logger.info("Saving document to database...")

    try:
        db_document = await crud_document.document.create(db=db, obj_in=document_data)
        await db.commit()
        await db.refresh(db_document)
        logger.info(f"Document saved to database with ID: {db_document.id}")
        return DocumentSchema.model_validate(db_document) # Return DocumentSchema instance
    except Exception as e:
        await db.rollback()
        error_msg = f"Database error while saving document: {str(e)}"\
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


def _cleanup_file(file_path: Path) -> None:
    """Clean up the uploaded file if it exists."""
    if file_path and file_path.exists():
        try:
            file_path.unlink()
            logger.info(f"Cleaned up file: {file_path}")
        except Exception as cleanup_error:
            logger.error(f"Error during file cleanup: {str(cleanup_error)}")


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
) -> Dict[str, str]: # Added return type
    """
    Upload a document to the knowledge base (Development only - no auth).

    - **file**: The file to upload (required)
    """
    user_id = DEFAULT_USER_ID  # In production, verify the user exists
    logger.info(f"Starting document upload for user {user_id}")

    if not file.filename:
        logger.error("No file provided in the request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided"
        )

    # Ensure upload directory exists
    upload_path = Path(UPLOAD_DIR)
    try:
        upload_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using upload directory: {upload_path.absolute()}")
    except Exception as e:
        error_msg = f"Failed to create upload directory: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    file_path: Optional[Path] = None # Added type hint
    try:
        # Save the uploaded file and get its contents
        contents, file_path = await _save_uploaded_file(file, upload_path)

        # Save document metadata to database
        db_document = await _save_document_to_db(
            db=db,
            user_id=user_id,
            file=file,
            file_path=file_path,
            file_size=len(contents),
        )

        # Prepare success response
        response_data = {
            "message": "File uploaded and processed successfully",
            "filename": file.filename,
            "document_id": str(db_document.id),
        }

        logger.info(f"Upload completed successfully for document ID: {db_document.id}")
        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        error_msg = f"Unexpected error during document upload: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    finally:
        # Clean up if there was an error after file was saved but before DB commit
        if file_path and "db_document" not in locals() and file_path.exists():
            _cleanup_file(file_path)

        # Ensure the uploaded file is properly closed
        if not file.file.closed:
            await file.close()
            logger.debug("Uploaded file handle closed")


@router.get("", response_model=Dict[str, Any]) # Changed response_model to Dict[str, Any]
async def list_documents(
    skip: Optional[int] = 0, limit: Optional[int] = 100, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]: # Added return type
    """
    Get a list of all uploaded documents.

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (for pagination)
    """
    try:
        logger.info(f"Fetching documents (skip={skip}, limit={limit})")

        # Handle Optional[int] for skip and limit
        actual_skip = skip if skip is not None else 0
        actual_limit = limit if limit is not None else 100

        # Get documents from the database using the correct CRUD reference
        documents = await crud_document.document.get_multi(
            db=db, skip=actual_skip, limit=actual_limit
        )

        # Format the response according to the API spec
        formatted_documents = [
            {
                "id": str(doc.id),
                "filename": doc.file_name,
                "title": doc.title, # Added title
                "file_size": doc.file_size,
                "file_type": doc.file_type,
                "status": doc.status,
                "uploaded_at": doc.created_at.isoformat()
                + "Z",  # ISO 8601 format with Z for UTC
            }
            for doc in documents
        ]

        # Get total count using SQLAlchemy directly
        from app.models.db_models import Document # Re-import for func.count()

        count_result = await db.execute(select(func.count()).select_from(Document))
        total_count = count_result.scalar_one() # Use scalar_one() for single result

        return {
            "documents": formatted_documents,
            "pagination": {
                "total": total_count,
                "skip": actual_skip,
                "limit": actual_limit,
                "has_more": (actual_skip + len(formatted_documents)) < total_count,
            },
        }

    except Exception as e:
        error_msg = f"Error listing documents: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


@router.get("/{document_id}", response_model=Dict[str, Any]) # Changed response_model to Dict[str, Any]
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]: # Changed document_id type to UUID
    """
    Get details of a specific document.

    - **document_id**: ID of the document to retrieve (UUID string)
    """
    try:
        logger.info(f"Fetching document with ID: {document_id}")

        # Get the document from the database using the correct CRUD reference
        document = await crud_document.document.get(db=db, id=document_id)

        # Check if document exists
        if not document:
            error_msg = f"Document not found with ID: {document_id}"
            logger.warning(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        # Format the response according to the API spec
        response_data = {
            "id": str(document.id),
            "filename": document.file_name,
            "title": document.title, # Added title
            "file_path": document.file_path,
            "file_size": document.file_size,
            "file_type": document.file_type,
            "status": document.status,
            "uploaded_at": document.created_at.isoformat() + "Z",
            # Convert metadata to dict if it's not already
            "metadata": (
                dict(document.document_metadata) if document.document_metadata else {} # Changed to document.document_metadata
            ),
        }

        logger.info(f"Successfully retrieved document: {document_id}")
        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        error_msg = f"Error retrieving document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, db: AsyncSession = Depends(get_db)) -> None: # Changed document_id type to UUID, added return type
    """
    Delete a document from the knowledge base.

    - **document_id**: ID of the document to delete (UUID string)
    """
    db_document: Optional[DocumentSchema] = None # Added type hint
    try:
        logger.info(f"Deleting document with ID: {document_id}")

        # Get the document from the database first
        db_document = await crud_document.document.get(db=db, id=document_id)

        # Check if document exists
        if not db_document:
            error_msg = f"Document not found with ID: {document_id}"
            logger.warning(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        file_path = Path(db_document.file_path) # Changed to Path object

        # Delete the file from storage if it exists
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"Successfully deleted file: {file_path}")
            except Exception as e:
                # Log the error but continue with DB deletion
                error_msg = f"Warning: Could not delete file {file_path}: {str(e)}"
                logger.warning(error_msg, exc_info=True)

        # Delete the document from the database
        await crud_document.document.remove(db=db, id=document_id)
        await db.commit()

        logger.info(f"Successfully deleted document with ID: {document_id}")
        return None

    except HTTPException:
        # Re-raise HTTP exceptions
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        error_msg = f"Error deleting document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )