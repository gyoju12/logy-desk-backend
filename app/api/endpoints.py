from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import os

from app.models.schemas import (
    Agent, AgentCreate, AgentUpdate, AgentListResponse,
    Document, DocumentListResponse,
    ChatSession, ChatSessionDetail, ChatSessionListResponse, ChatMessage,
    ChatRequest, ChatResponse
)

# Create routers
agents_router = APIRouter(prefix="/agents", tags=["Agents"])
documents_router = APIRouter(prefix="/documents", tags=["Documents"])
chat_sessions_router = APIRouter(prefix="/chat_sessions", tags=["Chat Sessions"])
chat_router = APIRouter(prefix="/chat", tags=["Chat"])

# Dummy data storage (in-memory, will be replaced with database later)
class DummyDB:
    def __init__(self):
        self.agents = {}
        self.documents = []
        self.chat_sessions = {}
        self.next_agent_id = 1
        self.next_chat_id = 1
        self.next_doc_id = 1

    def generate_agent_id(self):
        agent_id = f"agent_{self.next_agent_id:03d}"
        self.next_agent_id += 1
        return agent_id
        
    def generate_chat_id(self):
        chat_id = f"chat_{self.next_chat_id:03d}"
        self.next_chat_id += 1
        return chat_id
        
    def generate_document_id(self):
        doc_id = f"doc_{self.next_doc_id:03d}"
        self.next_doc_id += 1
        return doc_id
        
    def add_document(self, doc):
        """문서를 추가합니다."""
        self.documents.append(doc)
        return doc
        
    def get_document(self, doc_id: str):
        """문서 ID로 문서를 조회합니다."""
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        raise HTTPException(status_code=404, detail="Document not found")
        
    def delete_document(self, doc_id: str):
        """문서를 삭제합니다."""
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                return self.documents.pop(i)
        raise HTTPException(status_code=404, detail="Document not found")

# Initialize dummy database
db = DummyDB()

# Predefined agent templates for different agent types
AGENT_TEMPLATES = {
    "main": {
        "name": "메인 라우터",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "system_prompt": """
        당신은 사용자의 요청을 분석하여 가장 적합한 전문가 에이전트에게 작업을 위임하는 메인 라우터 에이전트입니다.
        사용자의 요청을 정확히 이해하고, 등록된 전문가 에이전트들 중에서 가장 적절한 에이전트를 선택하여 답변을 생성하세요.
        """.strip()
    },
    "sub": {
        "name": "전문가 에이전트",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "system_prompt": """
        당신은 특정 분야의 전문가 에이전트입니다. 
        주어진 주제에 대해 전문성 있는 답변을 제공하세요.
        """.strip()
    }
}

# Agents endpoints
@agents_router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_data: AgentCreate) -> Agent:
    """
    새로운 에이전트를 생성합니다.
    
    - **agent_type**: 'main'(라우터) 또는 'sub'(전문가) 중 하나여야 합니다.
    - **name**: 에이전트의 이름 (생략 시 기본 템플릿 사용)
    - **model**: 사용할 모델 (기본값: gpt-4o-mini)
    - **temperature**: 생성의 무작위성 (0.0 ~ 2.0)
    - **system_prompt**: 에이전트의 역할과 행동을 정의하는 시스템 프롬프트
    """
    # 입력 데이터 유효성 검사
    if agent_data.agent_type not in ["main", "sub"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_type은 'main' 또는 'sub'이어야 합니다."
        )
    
    # 기본값 설정
    agent_values = agent_data.dict()
    template = AGENT_TEMPLATES[agent_data.agent_type]
    
    # 이름이 제공되지 않은 경우 기본 템플릿 사용
    if not agent_values.get('name'):
        agent_values['name'] = template['name']
    
    # 시스템 프롬프트가 제공되지 않은 경우 기본 템플릿 사용
    if not agent_values.get('system_prompt'):
        agent_values['system_prompt'] = template['system_prompt']
    
    # 에이전트 생성
    agent_id = db.generate_agent_id()
    now = datetime.utcnow()
    
    agent = Agent(
        id=agent_id,
        created_at=now,
        updated_at=now,
        **agent_values
    )
    
    # 메모리 DB에 저장
    db.agents[agent_id] = agent
    
    return agent

@agents_router.get("", response_model=AgentListResponse)
async def list_agents(agent_type: Optional[str] = None) -> AgentListResponse:
    """
    등록된 모든 에이전트 목록을 조회합니다.
    
    - **agent_type**: 'main' 또는 'sub'으로 필터링할 수 있습니다.
    """
    agents = list(db.agents.values())
    if agent_type:
        if agent_type not in ["main", "sub"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agent_type은 'main' 또는 'sub'이어야 합니다."
            )
        agents = [agent for agent in agents if agent.agent_type == agent_type]
    return AgentListResponse(agents=agents)

@agents_router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str) -> Agent:
    """
    특정 ID를 가진 에이전트의 상세 정보를 조회합니다.
    
    - **agent_id**: 조회할 에이전트의 고유 ID
    """
    agent = db.agents.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"에이전트를 찾을 수 없습니다. (ID: {agent_id})"
        )
    return agent

@agents_router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_data: AgentUpdate) -> Agent:
    """
    기존 에이전트의 정보를 업데이트합니다.
    
    - **agent_id**: 업데이트할 에이전트의 고유 ID
    - **agent_data**: 업데이트할 필드 (선택적)
    """
    if agent_id not in db.agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"에이전트를 찾을 수 없습니다. (ID: {agent_id})"
        )
    
    # 기존 에이전트 정보 가져오기
    existing_agent = db.agents[agent_id]
    
    # 업데이트할 데이터 준비
    update_data = agent_data.dict(exclude_unset=True)
    
    # 에이전트 타입은 변경 불가
    if 'agent_type' in update_data and update_data['agent_type'] != existing_agent.agent_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="에이전트 타입은 변경할 수 없습니다."
        )
    
    # 에이전트 업데이트
    updated_agent = existing_agent.copy(update=update_data)
    updated_agent.updated_at = datetime.utcnow()
    
    # DB 업데이트
    db.agents[agent_id] = updated_agent
    
    return updated_agent

@agents_router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str):
    """
    특정 ID를 가진 에이전트를 삭제합니다.
    
    - **agent_id**: 삭제할 에이전트의 고유 ID
    """
    if agent_id not in db.agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"에이전트를 찾을 수 없습니다. (ID: {agent_id})"
        )
    
    # 메인 에이전트는 삭제 불가
    if db.agents[agent_id].agent_type == "main":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="메인 에이전트는 삭제할 수 없습니다."
        )
    
    # 에이전트 삭제
    del db.agents[agent_id]
    
    # 204 No Content 반환 (본문 없음)

# Documents endpoints
@documents_router.post("/upload", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), title: str = None):
    """
    문서를 업로드합니다.
    
    - **file**: 업로드할 파일
    - **title**: 문서 제목 (생략 시 파일명 사용)
    
    Returns:
        Document: 업로드된 문서 정보
    """
    if not title:
        title = file.filename or "제목 없음"
    
    # 파일 내용 읽기 (실제 애플리케이션에서는 디스크나 클라우드 스토리지에 저장)
    content = await file.read()
    
    # 문서 레코드 생성
    doc = {
        "id": db.generate_document_id(),
        "title": title,
        "filename": file.filename,
        "content_type": file.content_type or "application/octet-stream",
        "size": len(content),
        "uploaded_at": datetime.utcnow()
    }
    
    db.add_document(doc)
    return doc

@documents_router.get("", response_model=List[Document])
async def list_documents():
    """
    업로드된 모든 문서 목록을 조회합니다.
    
    Returns:
        List[Document]: 문서 목록
    """
    return db.documents

@documents_router.get("/{doc_id}", response_model=Document)
async def get_document(doc_id: str):
    """
    특정 문서의 상세 정보를 조회합니다.
    
    - **doc_id**: 조회할 문서의 ID
    
    Returns:
        Document: 문서 상세 정보
    """
    return db.get_document(doc_id)

@documents_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str):
    """
    문서를 삭제합니다.
    
    - **doc_id**: 삭제할 문서의 ID
    """
    db.delete_document(doc_id)

# Chat Sessions endpoints
@chat_sessions_router.post("", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_chat_session(title: str = "새 채팅") -> ChatSession:
    """
    새로운 채팅 세션을 생성합니다.
    
    - **title**: 채팅 세션의 제목 (기본값: '새 채팅')
    
    Returns:
        ChatSession: 생성된 채팅 세션 정보
    """
    session_id = db.generate_chat_id()
    now = datetime.utcnow()
    
    # 새 채팅 세션 생성
    db.chat_sessions[session_id] = {
        "title": title,
        "created_at": now,
        "messages": []
    }
    
    return ChatSession(
        id=session_id,
        title=title,
        created_at=now
    )

@chat_sessions_router.get("", response_model=ChatSessionListResponse)
async def list_chat_sessions() -> ChatSessionListResponse:
    """
    모든 채팅 세션 목록을 조회합니다.
    
    Returns:
        ChatSessionListResponse: 채팅 세션 목록
    """
    sessions = [
        ChatSession(id=session_id, title=session["title"], created_at=session["created_at"])
        for session_id, session in db.chat_sessions.items()
    ]
    return ChatSessionListResponse(sessions=sessions)

@chat_sessions_router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(session_id: str) -> ChatSessionDetail:
    """Get a specific chat session with all messages"""
    if session_id not in db.chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    session = db.chat_sessions[session_id]
    return ChatSessionDetail(
        id=session_id,
        title=session["title"],
        created_at=session["created_at"],
        messages=session["messages"]
    )

@chat_sessions_router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    if session_id not in db.chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.chat_sessions.pop(session_id)

# Chat endpoint
@chat_router.post("", response_model=ChatResponse)
async def chat(chat_request: ChatRequest) -> ChatResponse:
    """Send a message to the chat and get a response"""
    session_id = chat_request.session_id or f"session_{uuid4().hex[:8]}"
    
    # Create new session if it doesn't exist
    if session_id not in db_chat_sessions:
        db_chat_sessions[session_id] = {
            "title": chat_request.user_message[:30] + ("..." if len(chat_request.user_message) > 30 else ""),
            "created_at": datetime.utcnow(),
            "messages": []
        }
    
    # Add user message to session
    db_chat_sessions[session_id]["messages"].append(
        ChatMessage(role="user", content=chat_request.user_message)
    )
    
    # Generate dummy response (will be replaced with actual agent logic)
    response_text = f"This is a dummy response to: {chat_request.user_message}"
    
    # Add assistant response to session
    db_chat_sessions[session_id]["messages"].append(
        ChatMessage(role="assistant", content=response_text)
    )
    
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        metadata={"dummy": True}
    )

# Include all routers in the main router
router = APIRouter()
router.include_router(agents_router)
router.include_router(documents_router)
router.include_router(chat_sessions_router)
router.include_router(chat_router)