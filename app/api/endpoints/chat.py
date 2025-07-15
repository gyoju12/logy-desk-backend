from datetime import datetime
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_chat
from app.db.session import get_db
from app.schemas import chat as schemas
from app.services.llm_client import get_llm_client

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")  # Changed to UUID object

router = APIRouter()


@router.post("/{session_id}/messages", response_model=schemas.ChatMessage)
async def create_chat_message(
    session_id: UUID,
    message: schemas.ChatMessageCreate,
    db: AsyncSession = Depends(
        get_db
    ),  # Changed session_id type to UUID, db type to AsyncSession
) -> schemas.ChatMessage:  # Added return type
    """
    새로운 채팅 메시지를 생성하고 AI 응답을 반환합니다 (개발용 - 인증 없음).

    - **session_id**: 채팅 세션 ID (URL 경로에서 가져옴)
    - **role**: 메시지 역할 ('user', 'assistant', 'system')
    - **content**: 메시지 내용
    """
    # 채팅 세션이 존재하는지 확인
    db_chat_session = await crud_chat.chat_session.get(db, id=session_id)
    if not db_chat_session:
        # For MVP, create a new session with default user if it doesn't exist
        db_chat_session = await crud_chat.chat_session.create(
            db,
            obj_in=schemas.ChatSessionCreate(  # Pass ChatSessionCreate instance
                title=f"New Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                user_id=DEFAULT_USER_ID,
            ),
        )

    # 사용자 메시지 저장 (비동기 호출)
    db_message = await crud_chat.chat_message.create_with_session(
        db, obj_in=message, session_id=session_id
    )

    # AI 응답 생성 (비동기로 실행)
    if message.role == "user":
        # 이전 메시지 가져오기 (컨텍스트용)
        messages = await crud_chat.chat_session.get_messages(
            db, session_id=session_id, limit=10  # 최근 10개 메시지만 컨텍스트로 사용
        )

        # AI 응답 생성
        try:
            # LLM 클라이언트 초기화
            llm_client = await get_llm_client()

            # 이전 대화 맥락을 포함한 메시지 준비
            chat_messages: List[Dict[str, str]] = [
                {"role": m.role, "content": m.content} for m in messages
            ]  # Added type hint

            # LLM을 통해 응답 생성
            response_content = await llm_client.generate_chat_response(
                messages=chat_messages, temperature=0.7, max_tokens=1000
            )

            # AI 응답 저장 (비동기 호출)
            ai_message = await crud_chat.chat_message.create_with_session(
                db,
                obj_in=schemas.ChatMessageCreate(
                    role="assistant",
                    content=response_content,
                ),
                session_id=session_id,
            )
            return ai_message

        except Exception as e:
            # AI 응답 생성 중 오류 발생 시 오류 메시지 반환 (비동기 호출)
            error_message = f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}"
            await crud_chat.chat_message.create_with_session(
                db,
                obj_in=schemas.ChatMessageCreate(
                    role="system",
                    content=error_message,
                ),
                session_id=session_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message
            )

    return db_message


@router.get("/{session_id}/messages", response_model=List[schemas.ChatMessage])
async def get_chat_messages(
    session_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(
        get_db
    ),  # Changed session_id type to UUID, db type to AsyncSession
) -> List[schemas.ChatMessage]:  # Added return type
    """
    특정 채팅 세션의 메시지 목록을 조회합니다 (개발용 - 인증 없음).

    - **session_id**: 채팅 세션 ID
    - **skip**: 건너뛸 메시지 수
    - **limit**: 반환할 최대 메시지 수 (기본값: 100)
    """
    # 채팅 세션이 존재하는지 확인 (비동기 호출)
    db_chat_session = await crud_chat.chat_session.get(db, id=session_id)
    if not db_chat_session:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")

    # 채팅 메시지 조회 (비동기 호출)
    messages = await crud_chat.chat_message.get_multi_by_session(
        db, session_id=session_id, skip=skip, limit=limit
    )

    return [
        schemas.ChatMessage.model_validate(msg) for msg in messages
    ]  # Return list of ChatMessage instances
