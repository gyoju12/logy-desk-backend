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
from app.schemas.document import Document as DocumentSchema, DocumentCreate, DocumentProcessingStatus
from app.core.celery_utils import celery_app
from app.tasks.document_tasks import process_document

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

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
) -> Path:
    """Save the uploaded file to disk and return its path."""
    file_extension = os.path.splitext(file.filename or "")[1]
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{file_extension}"
    file_path = upload_path / filename

    logger.info(f"Starting file upload: {file.filename} (saving as {filename})")

    try:
        with open(file_path, "wb") as buffer:
            while contents := await file.read(1024 * 1024):
                buffer.write(contents)
        logger.info(f"File saved to {file_path}")

        return file_path
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


async def _save_document_metadata_to_db(
    db: AsyncSession, user_id: UUID, file_name: str
) -> DocumentSchema:
    """Save document metadata to the database and return the created document."""
    document_data = DocumentCreate(
        user_id=user_id,
        file_name=file_name,
        processing_status=DocumentProcessingStatus.PENDING,
        summary=None,
        doc_type=None,
    )

    logger.debug(f"Document metadata: {document_data.model_dump_json()}")
    logger.info("Saving document metadata to database...")

    try:
        db_document = await crud_document.document.create(db, obj_in=document_data)
        await db.flush()
        await db.refresh(db_document)
        logger.info(f"Document metadata saved to database with ID: {db_document.id}")
        return DocumentSchema.model_validate(db_document)
    except Exception as e:
        error_msg = f"Database error while saving document metadata: {str(e)}"
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
) -> Dict[str, Any]:
    """
    Upload a document to the knowledge base. The file is saved and processed asynchronously.

    - **file**: The file to upload (required)
    """
    user_id = DEFAULT_USER_ID
    logger.info(f"Starting document upload for user {user_id}")

    if not file.filename:
        logger.error("No file provided in the request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided"
        )

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

    file_path: Optional[Path] = None
    db_document: Optional[DocumentSchema] = None

    try:
        file_path = await _save_uploaded_file(file, upload_path)

        db_document = await _save_document_metadata_to_db(
            db=db,
            user_id=user_id,
            file_name=file.filename,
        )

        # Celery task 실행 및 task_id 저장
        task = process_document.delay(str(db_document.id), str(file_path))
        task_id = task.id
        logger.info(f"Enqueued document processing task {task_id} for document ID: {db_document.id}")

        response_data = {
            "message": "File upload accepted for processing",
            "document": {
                "id": str(db_document.id),
                "filename": db_document.file_name,
                "processing_status": db_document.processing_status,
                "uploaded_at": db_document.created_at.isoformat() + "Z",
                "task_id": task_id,  # 작업 추적을 위한 task ID 추가
            },
        }

        logger.info(f"Upload request completed for document ID: {db_document.id}")
        return response_data

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Unexpected error during document upload: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if file_path and file_path.exists():
            _cleanup_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )

    finally:
        if not file.file.closed:
            await file.close()
            logger.debug("Uploaded file handle closed")


@router.get("/task-status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a document processing task with detailed progress information.
    
    - **task_id**: The Celery task ID returned from upload endpoint
    
    Returns:
    - task_id: The task ID
    - state: Current state (PENDING, PROCESSING, SUCCESS, FAILURE)
    - progress: Progress information (current, total, status message)
    - result: Task result if completed
    - error: Error message if failed
    """
    try:
        # Celery AsyncResult를 사용하여 작업 상태 확인
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=celery_app)
        
        task_info = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }
        
        # 진행 중인 경우 상세 정보 추가
        if result.state == "PROCESSING":
            meta = result.info or {}
            task_info["progress"] = {
                "current": meta.get("current", 0),
                "total": meta.get("total", 100),
                "percentage": meta.get("current", 0),
                "status": meta.get("status", "Processing..."),
                "chunks_processed": meta.get("chunks_processed", 0),
                "total_chunks": meta.get("total_chunks", 0),
            }
        
        # 작업이 완료된 경우 결과 추가
        elif result.ready() and result.successful():
            task_info["result"] = result.result
            task_info["progress"] = {
                "current": 100,
                "total": 100,
                "percentage": 100,
                "status": "Completed",
            }
            if isinstance(result.result, dict):
                task_info["progress"]["chunks_created"] = result.result.get("chunks_created", 0)
        
        # 작업이 실패한 경우 에러 정보 추가
        elif result.failed():
            task_info["error"] = str(result.info)
            task_info["progress"] = {
                "current": 0,
                "total": 100,
                "percentage": 0,
                "status": "Failed",
            }
            
        # PENDING 상태
        else:
            task_info["progress"] = {
                "current": 0,
                "total": 100,
                "percentage": 0,
                "status": "Waiting to start...",
            }
            
        logger.info(f"Task {task_id} status: {result.state}")
        return task_info
    except Exception as e:
        error_msg = f"Error checking task status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


@router.get("", response_model=Dict[str, Any])
async def list_documents(
    skip: Optional[int] = 0,
    limit: Optional[int] = 100,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a list of all uploaded documents.

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (for pagination)
    """
    try:
        logger.info(f"Fetching documents (skip={skip}, limit={limit})")

        actual_skip = skip if skip is not None else 0
        actual_limit = limit if limit is not None else 100

        documents = await crud_document.document.get_multi(
            db=db, skip=actual_skip, limit=actual_limit
        )

        formatted_documents = [
            {
                "id": str(doc.id),
                "filename": doc.file_name,
                "processing_status": doc.processing_status,
                "summary": doc.summary,
                "doc_type": doc.doc_type,
                "uploaded_at": doc.created_at.isoformat()
                + "Z",
            }
            for doc in documents
        ]

        from app.models.db_models import Document

        count_result = await db.execute(select(func.count()).select_from(Document))
        total_count = count_result.scalar_one()

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


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: UUID, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get details of a specific document including its chunks.

    - **document_id**: ID of the document to retrieve (UUID string)
    """
    try:
        logger.info(f"Fetching document with ID: {document_id}")

        document = await crud_document.document.get(db=db, id=document_id)

        if not document:
            error_msg = f"Document not found with ID: {document_id}"
            logger.warning(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        # Chunk 정보 조회
        from sqlalchemy import select
        from app.models.db_models import DocumentChunk
        
        chunks_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.created_at)
        )
        chunks = chunks_result.scalars().all()
        
        # Chunk 정보 포맷팅
        chunk_info = [
            {
                "id": str(chunk.id),
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                "num_tokens": chunk.num_tokens,
                "embedding_status": chunk.embedding_status,
                "created_at": chunk.created_at.isoformat() + "Z",
            }
            for chunk in chunks
        ]

        response_data = {
            "id": str(document.id),
            "filename": document.file_name,
            "processing_status": document.processing_status,
            "summary": document.summary,
            "doc_type": document.doc_type,
            "uploaded_at": document.created_at.isoformat() + "Z",
            "chunk_count": len(chunks),
            "chunks": chunk_info,
            "error_message": document.error_message,
        }

        logger.info(f"Successfully retrieved document: {document_id} with {len(chunks)} chunks")
        return response_data

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Error retrieving document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a document from the knowledge base.

    - **document_id**: ID of the document to delete (UUID string)
    """
    db_document: Optional[DocumentSchema] = None
    try:
        logger.info(f"Deleting document with ID: {document_id}")

        db_document = await crud_document.document.get(db=db, id=document_id)

        if not db_document:
            error_msg = f"Document not found with ID: {document_id}"
            logger.warning(error_msg)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)

        await crud_document.document.remove(db=db, id=document_id)

        logger.info(f"Successfully deleted document with ID: {document_id}")
        return None

    except HTTPException:
        raise

    except Exception as e:
        error_msg = f"Error deleting document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )
