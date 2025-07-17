"""RAG (Retrieval-Augmented Generation) 서비스"""
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from langchain_openai import OpenAIEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import numpy as np
from app.models.db_models import DocumentChunk, Document, DocumentProcessingStatus
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """문서 검색 및 컨텍스트 생성을 위한 RAG 서비스"""
    
    def __init__(self):
        self.embeddings = None
        if settings.OPENAI_API_KEY:
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model="text-embedding-ada-002"
            )
    
    async def search_relevant_chunks(
        self,
        db: AsyncSession,
        query: str,
        user_id: UUID,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        쿼리와 관련된 문서 청크를 검색합니다.
        
        Args:
            db: 데이터베이스 세션
            query: 검색 쿼리
            user_id: 사용자 ID
            top_k: 반환할 최대 청크 수
            threshold: 최소 유사도 임계값
            
        Returns:
            (DocumentChunk, 유사도 점수) 튜플 리스트
        """
        if not self.embeddings:
            logger.warning("Embeddings not available. Using fallback search.")
            return await self._fallback_search(db, query, user_id, top_k)
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embeddings.embed_query(query)
            
            # 사용자의 문서에서 임베딩이 있는 청크 검색
            stmt = (
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    and_(
                        Document.user_id == user_id,
                        DocumentChunk.embedding_status == DocumentProcessingStatus.SUCCESS,
                        DocumentChunk.embedding.isnot(None)
                    )
                )
            )
            
            result = await db.execute(stmt)
            chunks_with_docs = result.all()
            
            if not chunks_with_docs:
                logger.info(f"No embedded chunks found for user {user_id}")
                return []
            
            # 유사도 계산
            scored_chunks = []
            for chunk, doc in chunks_with_docs:
                if chunk.embedding:
                    # 코사인 유사도 계산
                    similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                    if similarity >= threshold:
                        scored_chunks.append((chunk, similarity))
            
            # 유사도 기준으로 정렬
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 k개 반환
            return scored_chunks[:top_k]
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return await self._fallback_search(db, query, user_id, top_k)
    
    async def _fallback_search(
        self,
        db: AsyncSession,
        query: str,
        user_id: UUID,
        top_k: int
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        벡터 검색이 불가능할 때 사용하는 대체 검색 (키워드 기반)
        """
        # 간단한 키워드 매칭을 사용한 대체 검색
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                and_(
                    Document.user_id == user_id,
                    DocumentChunk.content.ilike(f"%{query}%")
                )
            )
            .limit(top_k)
        )
        
        result = await db.execute(stmt)
        chunks = result.all()
        
        # 대체 검색에서는 모든 결과에 동일한 점수 부여
        return [(chunk, 0.5) for chunk, doc in chunks]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """두 벡터 간의 코사인 유사도 계산"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def create_context_from_chunks(
        self,
        chunks: List[Tuple[DocumentChunk, float]],
        max_length: int = 2000
    ) -> str:
        """
        검색된 청크들로부터 컨텍스트 문자열 생성
        
        Args:
            chunks: (DocumentChunk, 유사도) 튜플 리스트
            max_length: 최대 컨텍스트 길이
            
        Returns:
            컨텍스트 문자열
        """
        if not chunks:
            return ""
        
        context_parts = []
        current_length = 0
        
        for chunk, score in chunks:
            chunk_text = f"[관련도: {score:.2f}]\n{chunk.content}\n"
            chunk_length = len(chunk_text)
            
            if current_length + chunk_length > max_length:
                break
            
            context_parts.append(chunk_text)
            current_length += chunk_length
        
        if context_parts:
            return "다음은 관련 문서 내용입니다:\n\n" + "\n---\n".join(context_parts)
        
        return ""


# 싱글톤 인스턴스
rag_service = RAGService()
