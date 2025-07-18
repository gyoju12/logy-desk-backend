from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_agent
from app.db.session import get_db
from app.schemas import agent as schemas

router = APIRouter()

# Default user ID for MVP
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000000")  # Changed to UUID object


@router.post("", response_model=schemas.Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_in: schemas.AgentCreate, db: AsyncSession = Depends(get_db)
) -> schemas.Agent:  # Added return type
    """
    새로운 에이전트를 생성합니다 (개발용 - 인증 없음).

    - **name**: 에이전트 이름 (필수)
    - **agent_type**: 에이전트 유형 ('main' 또는 'sub')
    - **model**: 사용할 모델 이름 (예: 'gpt-4')
    - **temperature**: 창의성 (0-10, 기본값: 7)
    - **system_prompt**: 시스템 프롬프트
    """
    # For MVP, use a default user ID
    agent_data = agent_in.model_dump()  # Use model_dump()
    agent_data["user_id"] = DEFAULT_USER_ID

    db_agent = await crud_agent.agent.get_by_name(db, user_id=DEFAULT_USER_ID, name=agent_in.name)
    if db_agent:
        raise HTTPException(
            status_code=400, detail="이미 존재하는 에이전트 이름입니다."
        )
    return await crud_agent.agent.create(
        db, obj_in=schemas.AgentCreate(**agent_data)
    )


@router.get("", response_model=List[schemas.Agent])
async def list_agents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> List[schemas.Agent]:  # Added return type
    """
    모든 에이전트 목록을 조회합니다 (개발용 - 인증 없음).

    - **skip**: 건너뛸 레코드 수 (페이징용)
    - **limit**: 반환할 최대 레코드 수 (페이징용)
    """
    # For MVP, return all agents without user filtering
    agents = await crud_agent.agent.get_multi(db, skip=skip, limit=limit)
    return [
        schemas.Agent.model_validate(agent) for agent in agents
    ]  # Return list of Agent instances


@router.get("/{agent_id}", response_model=schemas.Agent)
async def get_agent(
    agent_id: UUID, db: AsyncSession = Depends(get_db)
) -> schemas.Agent:  # Changed agent_id type to UUID, added return type
    """
    특정 에이전트의 상세 정보를 조회합니다.

    - **agent_id**: 조회할 에이전트의 ID
    """
    db_agent = await crud_agent.agent.get(db, id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    return schemas.Agent.model_validate(db_agent)  # Return Agent instance


@router.put("/{agent_id}", response_model=schemas.Agent)
async def update_agent(
    agent_id: UUID, agent_in: schemas.AgentUpdate, db: AsyncSession = Depends(get_db)
) -> schemas.Agent:  # Added return type
    """
    에이전트 정보를 수정합니다.

    - **agent_id**: 수정할 에이전트의 ID
    - **agent_in**: 업데이트할 에이전트 정보
    """
    db_agent = await crud_agent.agent.get(db, id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    updated_agent = await crud_agent.agent.update(db, db_obj=db_agent, obj_in=agent_in)
    return schemas.Agent.model_validate(updated_agent)  # Return Agent instance


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:  # Changed agent_id type to UUID, added return type
    """
    에이전트를 삭제합니다.

    - **agent_id**: 삭제할 에이전트의 ID
    """
    db_agent = await crud_agent.agent.get(db, id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다.")
    await crud_agent.agent.remove(db, id=agent_id)
    # 204 No Content 반환 (본문 없음)
