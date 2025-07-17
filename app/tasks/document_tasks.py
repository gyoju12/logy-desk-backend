import logging
import os
from pathlib import Path
from typing import List
from uuid import UUID

from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.crud.crud_document import document, document_chunk
from app.models.db_models import DocumentProcessingStatus
from app.schemas.document import DocumentChunkCreate, DocumentChunkUpdate

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from app.core.config import settings
from app.core.celery_utils import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document_task", bind=True)
async def process_document(self, document_id: str, file_path: str):
    db: AsyncSession = None
    try:
        db = async_session_maker()
        async with db as session:
            doc_uuid = UUID(document_id)
            db_document = await document.get(session, id=doc_uuid)

            if not db_document:
                logger.error(f"Document with ID {document_id} not found.")
                return

            # Update document status to PROCESSING
            await document.update(
                session,
                db_obj=db_document,
                obj_in={
                    "processing_status": DocumentProcessingStatus.PROCESSING,
                    "error_message": None,
                },
            )
            await session.commit()
            await session.refresh(db_document)

            # Load document
            loader = None
            file_extension = Path(file_path).suffix.lower()
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
            elif file_extension == ".txt":
                loader = TextLoader(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            langchain_documents = loader.load()

            # Split document into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            chunks = text_splitter.split_documents(langchain_documents)

            # Create document chunks in DB and enqueue embedding tasks
            for i, chunk in enumerate(chunks):
                chunk_data = DocumentChunkCreate(
                    document_id=doc_uuid,
                    content=chunk.page_content,
                    embedding_status=DocumentProcessingStatus.PENDING,
                    num_tokens=len(chunk.page_content.split()),  # Simple token count
                )
                db_chunk = await document_chunk.create(session, obj_in=chunk_data)
                await session.flush()
                await session.refresh(db_chunk)
                logger.info(f"Created chunk {db_chunk.id} for document {document_id}")

                # Enqueue embedding task for each chunk
                embed_chunk.delay(str(db_chunk.id), db_chunk.content)

            # Update document status to COMPLETED if all chunks are enqueued
            await document.update(
                session,
                db_obj=db_document,
                obj_in={
                    "processing_status": DocumentProcessingStatus.COMPLETED,
                },
            )
            await session.commit()
            logger.info(f"Document {document_id} processing completed and chunks enqueued.")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        if db and db_document:
            await document.update(
                db,
                db_obj=db_document,
                obj_in={
                    "processing_status": DocumentProcessingStatus.FAILED,
                    "error_message": str(e),
                },
            )
            await db.commit()
    finally:
        # Clean up the uploaded file
        if Path(file_path).exists():
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")


@celery_app.task(name="embed_chunk_task", bind=True)
async def embed_chunk(self, chunk_id: str, chunk_content: str):
    db: AsyncSession = None
    try:
        db = async_session_maker()
        async with db as session:
            chunk_uuid = UUID(chunk_id)
            db_chunk = await document_chunk.get(session, id=chunk_uuid)

            if not db_chunk:
                logger.error(f"Chunk with ID {chunk_id} not found.")
                return

            # Initialize embedding model and ChromaDB
            embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model="text-embedding-ada-002")
            # Assuming ChromaDB is initialized to a persistent path
            # For simplicity, we'll re-initialize it here. In a real app, manage this more robustly.
            # Ensure CHROMA_DB_PATH is configured in settings
            chroma_client = Chroma(persist_directory=settings.CHROMA_DB_PATH, embedding_function=embeddings)

            # Add chunk to ChromaDB
            # ChromaDB expects a list of documents, so we wrap the content
            chroma_client.add_texts(texts=[chunk_content], metadatas=[{"chunk_id": str(chunk_uuid), "document_id": str(db_chunk.document_id)}])

            # Update chunk status to COMPLETED
            await document_chunk.update(
                session,
                db_obj=db_chunk,
                obj_in={
                    "embedding_status": DocumentProcessingStatus.COMPLETED,
                },
            )
            await session.commit()
            logger.info(f"Chunk {chunk_id} embedded and stored in ChromaDB.")

    except Exception as e:
        logger.error(f"Error embedding chunk {chunk_id}: {e}", exc_info=True)
        if db and db_chunk:
            await document_chunk.update(
                db,
                db_obj=db_chunk,
                obj_in={
                    "embedding_status": DocumentProcessingStatus.FAILED,
                },
            )
            await db.commit()