from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_chat
from app.db.session import get_db
from app.schemas import chat as schemas
from app.schemas.chat import ChatSessionPublic

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

router = APIRouter()


@router.post(
    "", response_model=schemas.ChatSession, status_code=status.HTTP_201_CREATED
)
async def create_chat_session(
    chat_session_in: schemas.ChatSessionCreate, db: AsyncSession = Depends(get_db)
) -> schemas.ChatSession:
    """
    새로운 채팅 세션을 생성합니다 (개발용 - 인증 없음).

    - **title**: 채팅 세션 제목 (기본값: '새 채팅')
    """
    # Use default user ID for MVP
    chat_session_data = chat_session_in.model_dump()
    chat_session_data["user_id"] = DEFAULT_USER_ID

    db_chat_session = await crud_chat.chat_session.create(
        db, obj_in=schemas.ChatSessionCreate(**chat_session_data)
    )
    return schemas.ChatSession.model_validate(db_chat_session)


@router.get("", response_model=List[schemas.ChatSession])
async def list_chat_sessions(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> List[schemas.ChatSession]:
    """
    모든 채팅 세션 목록을 조회합니다 (개발용 - 인증 없음).

    - **skip**: 건너뛸 레코드 수 (페이징용)
    - **limit**: 반환할 최대 레코드 수 (페이징용)
    """
    # For MVP, return all chat sessions
    chat_sessions = await crud_chat.chat_session.get_multi(db, skip=skip, limit=limit)
    return [schemas.ChatSession.model_validate(session) for session in chat_sessions]


@router.get("/{session_id}", response_model=schemas.ChatSessionDetail)
async def get_chat_session(
    session_id: UUID, db: AsyncSession = Depends(get_db)
) -> schemas.ChatSessionDetail:
    """
    특정 채팅 세션과 해당 메시지들을 조회합니다.

    - **session_id**: 조회할 채팅 세션 ID
    """
    # 채팅 세션 조회
    db_chat_session = await crud_chat.chat_session.get(db, id=session_id)
    if not db_chat_session:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")

    # 채팅 메시지 조회
    messages = await crud_chat.chat_session.get_messages(db, session_id=session_id)

    # Pydantic 모델을 사용하여 응답 생성
    session_data = schemas.ChatSession.model_validate(db_chat_session)

    # 메시지들을 Pydantic 모델로 변환
    message_models = [schemas.ChatMessage.model_validate(msg) for msg in messages]

    # ChatSessionDetail 모델 생성
    return schemas.ChatSessionDetail(
        **session_data.model_dump(), messages=message_models
    )


@router.delete("/{session_id}", response_model=ChatSessionPublic)
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    채팅 세션과 관련된 모든 메시지를 삭제합니다.
    """
    session = await crud.chat_session.get(db, id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this chat session")

    # 세션과 연결된 모든 메시지 삭제
    messages = await crud.chat_message.get_multi_by_session(db, session_id=session_id)
    for message in messages:
        await crud.chat_message.remove(db, id=message.id)

    # 채팅 세션 삭제
    await crud.chat_session.remove(db, id=session_id)
    return session
