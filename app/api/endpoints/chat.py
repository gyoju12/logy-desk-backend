from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_chat, crud_agent
from app.db.session import get_db
from app.schemas import chat as schemas
from app.services.llm_client import LLMClient
from app.services.rag_service import RAGService
from app.core.logging_config import get_logger

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{session_id}/messages", response_model=schemas.ChatMessage)
async def create_chat_message(
    session_id: UUID,
    message: schemas.ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.ChatMessage:
    """
    새로운 채팅 메시지를 생성하고 AI 응답을 반환합니다.

    - **session_id**: 채팅 세션 ID (URL 경로에서 가져옴)
    - **role**: 메시지 역할 ('user', 'assistant', 'system')
    - **content**: 메시지 내용
    """
    logger.info(f"=== Chat message creation started ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Message role: {message.role}")
    logger.info(f"Message content: {message.content}")
    
    # 채팅 세션이 존재하는지 확인
    db_chat_session = await crud_chat.chat_session.get(db, id=session_id)
    if not db_chat_session:
        logger.info("Chat session not found, creating new session")
        # For MVP, create a new session with default user if it doesn't exist
        db_chat_session = await crud_chat.chat_session.create(
            db,
            obj_in=schemas.ChatSessionCreate(
                title=f"New Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                user_id=DEFAULT_USER_ID,
            ),
        )
        logger.info(f"New chat session created: {db_chat_session.id}")
        # 새로 생성된 세션의 ID를 사용
        session_id = db_chat_session.id
    else:
        logger.info(f"Using existing chat session: {db_chat_session.id}")

    # 사용자 메시지 저장
    logger.info("Saving user message to database")
    db_message = await crud_chat.chat_message.create_with_session(
        db, obj_in=message, session_id=session_id
    )
    logger.info(f"User message saved with ID: {db_message.id}")

    # 사용자 메시지인 경우 AI 응답 생성
    if message.role == "user":
        try:
            logger.info(f"Processing user message for session: {session_id}")
            
            # MAIN 타입 에이전트 설정 가져오기
            main_agent = await crud_agent.agent.get_main_agent(db, user_id=DEFAULT_USER_ID)
            logger.info(f"Main agent found: {main_agent is not None}")
            
            # 기본값 설정 (MAIN 에이전트가 없는 경우)
            model = "gpt-3.5-turbo"
            temperature = 0.7
            system_prompt = "당신은 도움이 되는 AI 어시스턴트입니다."
            
            if main_agent:
                model = main_agent.model or model
                temperature = main_agent.temperature or temperature
                system_prompt = main_agent.system_prompt or system_prompt
                logger.info(f"Using agent settings - model: {model}, temperature: {temperature}")
            
            # 최근 채팅 기록 가져오기 (현재 사용자 메시지 제외)
            # 컨텍스트용으로 최근 8개 메시지 (4개 대화 쌍 정도)
            previous_messages = await crud_chat.chat_session.get_messages(
                db, session_id=session_id, limit=8
            )
            
            # 현재 저장된 사용자 메시지는 제외 (아직 AI 응답이 생성되지 않았으므로)
            context_messages = [msg for msg in previous_messages if msg.id != db_message.id]
            logger.info(f"Retrieved {len(context_messages)} previous messages for context")
            
            # 채팅 기록을 LLM 형식으로 변환
            chat_history = []
            
            # 1. 시스템 프롬프트 추가 (항상 첫 번째)
            if system_prompt:
                chat_history.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 2. RAG: 사용자 메시지와 관련된 문서 검색
            logger.info("Searching for relevant documents...")
            rag_service = RAGService()
            relevant_chunks = await rag_service.search_relevant_chunks(
                db=db,
                query=message.content,
                user_id=DEFAULT_USER_ID,
                top_k=5,
                threshold=0.7
            )
            
            # 검색된 문서로부터 컨텍스트 생성
            rag_context = rag_service.create_context_from_chunks(relevant_chunks)
            if rag_context:
                logger.info(f"Found {len(relevant_chunks)} relevant document chunks")
                # RAG 컨텍스트를 시스템 메시지로 추가
                chat_history.append({
                    "role": "system",
                    "content": rag_context
                })
            else:
                logger.info("No relevant documents found for the query")
            
            # 3. 이전 대화 기록 추가 (시간순으로 정렬)
            for msg in context_messages:  # 이미 시간순으로 정렬됨 (created_at.asc())
                if msg.role == "system":
                    continue  # 시스템 메시지는 이미 추가했으므로 제외
                chat_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # 4. 현재 사용자 메시지 추가 (가장 마지막)
            chat_history.append({
                "role": message.role,
                "content": message.content
            })
            
            logger.info(f"Chat history prepared: {len(chat_history)} messages (including RAG context)")
            
            # LLM 클라이언트 초기화 및 응답 생성
            llm_client = LLMClient()
            await llm_client.initialize()
            logger.info("LLM client initialized")
            
            response_content = await llm_client.generate_chat_response(
                messages=chat_history,
                temperature=temperature,
                max_tokens=1000,
                model=model
            )
            logger.info(f"LLM response generated: {len(response_content)} characters")

            # AI 응답 메시지 저장
            assistant_message = schemas.ChatMessageCreate(
                role="assistant",
                content=response_content
            )
            
            await crud_chat.chat_message.create_with_session(
                db, obj_in=assistant_message, session_id=session_id
            )
            logger.info("Assistant message saved successfully")

        except Exception as e:
            logger.error(f"Error in chat message creation: {str(e)}", exc_info=True)
            # AI 응답 생성 실패 시 에러 메시지 저장
            error_message = schemas.ChatMessageCreate(
                role="assistant",
                content=f"죄송합니다. 응답을 생성하는 중 오류가 발생했습니다: {str(e)}"
            )
            
            await crud_chat.chat_message.create_with_session(
                db, obj_in=error_message, session_id=session_id
            )

    return db_message


@router.get("/{session_id}/messages", response_model=List[schemas.ChatMessage])
async def get_chat_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.ChatMessage]:
    """
    채팅 세션의 메시지들을 조회합니다.
    """
    messages = await crud_chat.chat_session.get_messages(
        db, session_id=session_id, skip=skip, limit=limit
    )
    return messages
