import logging
import os
from pathlib import Path
from typing import List
from uuid import UUID
import asyncio

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


async def async_process_document(document_id: str, file_path: str, task=None):
    """비동기 문서 처리 함수"""
    db: AsyncSession = None
    try:
        async with async_session_maker() as session:
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

            # 진행 상황 업데이트: 문서 로딩
            if task:
                task.update_state(state='PROCESSING', meta={
                    'current': 10,
                    'total': 100,
                    'status': 'Loading document...'
                })

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

            # 진행 상황 업데이트: 문서 분할
            if task:
                task.update_state(state='PROCESSING', meta={
                    'current': 30,
                    'total': 100,
                    'status': f'Splitting document into chunks...'
                })

            # Split document into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            chunks = text_splitter.split_documents(langchain_documents)
            
            total_chunks = len(chunks)
            logger.info(f"Document split into {total_chunks} chunks")

            # Create document chunks in DB and enqueue embedding tasks
            chunk_ids = []
            for i, chunk in enumerate(chunks):
                # 진행 상황 업데이트: 각 chunk 처리
                if task:
                    progress = 30 + int((i / total_chunks) * 60)  # 30% ~ 90%
                    task.update_state(state='PROCESSING', meta={
                        'current': progress,
                        'total': 100,
                        'status': f'Processing chunk {i+1}/{total_chunks}...',
                        'chunks_processed': i,
                        'total_chunks': total_chunks
                    })
                
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
                
                chunk_ids.append(str(db_chunk.id))
                # Enqueue embedding task for each chunk
                embed_chunk_task.delay(str(db_chunk.id), db_chunk.content)

            # 진행 상황 업데이트: 완료
            if task:
                task.update_state(state='PROCESSING', meta={
                    'current': 90,
                    'total': 100,
                    'status': 'Finalizing document processing...',
                    'chunks_processed': total_chunks,
                    'total_chunks': total_chunks
                })

            # Update document status to COMPLETED if all chunks are enqueued
            await document.update(
                session,
                db_obj=db_document,
                obj_in={
                    "processing_status": DocumentProcessingStatus.COMPLETED,
                    "chunk_count": len(chunks),
                },
            )
            await session.commit()
            logger.info(f"Document {document_id} processing completed. Created {len(chunks)} chunks.")
            
            return {
                "status": "completed",
                "document_id": document_id,
                "message": "Document processing completed",
                "chunks_created": len(chunks),
                "chunk_ids": chunk_ids
            }

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        if db:
            async with async_session_maker() as session:
                doc_uuid = UUID(document_id)
                db_document = await document.get(session, id=doc_uuid)
                if db_document:
                    await document.update(
                        session,
                        db_obj=db_document,
                        obj_in={
                            "processing_status": DocumentProcessingStatus.FAILED,
                            "error_message": str(e),
                        },
                    )
                    await session.commit()


@celery_app.task(name="process_document_task", bind=True)
def process_document(self, document_id: str, file_path: str):
    """동기 Celery task wrapper"""
    logger.info(f"Starting document processing for document {document_id}")
    
    # 작업 시작 상태 업데이트
    self.update_state(state='PROCESSING', meta={
        'current': 0,
        'total': 100,
        'status': 'Starting document processing...'
    })
    
    # 이벤트 루프에서 비동기 함수 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # self 객체를 async 함수에 전달
        result = loop.run_until_complete(async_process_document(document_id, file_path, self))
    finally:
        loop.close()
    
    return result


@celery_app.task(bind=True, max_retries=3)
def embed_chunk_task(self, chunk_id: str, chunk_content: str):
    """
    Celery task for embedding a document chunk with progress updates.
    비동기 작업을 위해 새로운 이벤트 루프를 생성합니다.
    """
    import asyncio
    from app.tasks.document_tasks import async_embed_chunk_with_new_loop
    
    try:
        # 새로운 이벤트 루프 생성
        result = asyncio.run(async_embed_chunk_with_new_loop(chunk_id, chunk_content))
        return result
    except Exception as exc:
        logger.error(f"Error embedding chunk {chunk_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def async_embed_chunk_with_new_loop(chunk_id: str, chunk_content: str):
    """새로운 이벤트 루프에서 실행되는 비동기 chunk 임베딩 함수"""
    from app.db.session import async_session_maker
    from app.crud import document_chunk
    from app.models.db_models import DocumentProcessingStatus
    from uuid import UUID
    
    try:
        async with async_session_maker() as session:
            chunk_uuid = UUID(chunk_id)
            db_chunk = await document_chunk.get(session, id=chunk_uuid)

            if not db_chunk:
                logger.error(f"Chunk with ID {chunk_id} not found.")
                return {"status": "failed", "chunk_id": chunk_id, "message": "Chunk not found"}

            # Update chunk status to PROCESSING
            await document_chunk.update(
                session,
                db_obj=db_chunk,
                obj_in={
                    "embedding_status": DocumentProcessingStatus.PROCESSING,
                },
            )
            await session.commit()

            # 임시로 Mock 임베딩 사용 (OpenAI API 키가 없는 경우)
            # TODO: 실제 환경에서는 OpenAI API 키 설정 필요
            try:
                if settings.OPENAI_API_KEY:
                    embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model="text-embedding-ada-002")
                    embedding_result = embeddings.embed_documents([chunk_content])
                    embedding_vector = embedding_result[0]
                else:
                    logger.warning("OpenAI API key not set. Using mock embedding.")
                    # Mock 임베딩 - 1536 차원의 더미 벡터
                    import random
                    embedding_vector = [random.random() for _ in range(1536)]

                # Update chunk with embedding and success status
                await document_chunk.update(
                    session,
                    db_obj=db_chunk,
                    obj_in={
                        "embedding": embedding_vector,
                        "embedding_status": DocumentProcessingStatus.SUCCESS,
                    },
                )
                await session.commit()

                logger.info(f"Successfully embedded chunk {chunk_id}")
                return {"status": "success", "chunk_id": chunk_id}

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to generate embedding for chunk {chunk_id}: {error_msg}")
                
                # Update chunk with error status
                await document_chunk.update(
                    session,
                    db_obj=db_chunk,
                    obj_in={
                        "embedding_status": DocumentProcessingStatus.FAILED,
                        "error_message": error_msg,
                    },
                )
                await session.commit()
                
                return {"status": "failed", "chunk_id": chunk_id, "message": error_msg}

    except Exception as exc:
        logger.error(f"Database error in embedding chunk {chunk_id}: {exc}")
        return {"status": "failed", "chunk_id": chunk_id, "message": str(exc)}