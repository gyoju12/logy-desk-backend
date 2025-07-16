# 1. 목표
API 명세서에 정의된 `/chat` 엔드포인트의 핵심 로직인 Multi-Agent 파이프라인을 구축하는 것을 목표로 합니다. 이 파이프라인은 **메인 Agent(라우터)** 가 사용자의 요청을 분석하고, 데이터베이스에 등록된 다수의 **'보조 Agent(전문가)'** 들을 LangChain의 **`Tool`** 로 동적으로 활용하여, 최종적으로 종합된 답변을 생성하는 지능형 시스템입니다.

# 2. 기술 스택
- **언어/프레임워크:** Python, FastAPI
- **AI 오케스트레이션:** LangChain (특히 Agents, Tools, LCEL)
- **Vector DB:** ChromaDB (공유 지식 베이스)
- **Metadata DB:** PostgreSQL (Agent 설정, 대화 기록 등)
- **의존성 관리:** Poetry 또는 Pipenv

# 3. 개발 단계별 실행 계획

## Phase 1: 프로젝트 초기 설정 및 구조 설계
- 목표: Multi-Agent 로직을 담을 수 있는 확장 가능한 프로젝트 구조를 설정합니다.
- 실행 계획:
### 1. 가상 환경 및 의존성 설치:
- `fastapi`, `uvicorn`, `langchain`, `langchain-openai`, `chromadb`, `sqlalchemy`, `psycopg2-binary`, `pydantic` 등 필수 라이브러리를 설치합니다.

### 2. 프로젝트 구조 설계:
```
/logy-desk-backend
|-- /app
|   |-- /api
|   |   |-- endpoints.py      # FastAPI 라우터 (API 진입점)
|   |-- /core
|   |   |-- config.py         # 환경변수 및 설정 관리
|   |-- /services
|   |   |-- agent_service.py  # 메인/보조 Agent 생성 및 실행 로직
|   |   |-- rag_service.py    # 문서 처리 및 RAG 체인 로직
|   |-- /models
|   |   |-- schemas.py        # Pydantic 스키마 (API 요청/응답)
|   |   |-- db_models.py      # SQLAlchemy 모델 (DB 테이블)
|   |-- /db
|   |   |-- session.py        # DB 세션 관리
|   |-- main.py               # FastAPI 앱 초기화
|-- .env
|-- pyproject.toml
```

## Phase 2: 문서 처리 및 공유 지식 베이스 구축
- 목표: 모든 Agent가 공통으로 참조할 중앙 지식 베이스(Vector DB)를 구축하고, 문서를 처리하여 저장하는 로직을 구현합니다.
- 실행 계획:
### 1. `rag_service.py` 구현:
- `POST /documents/upload` API를 위한 로직을 구현합니다.
- **Document Loader:** 파일 확장자에 따라 `PyPDFLoader`, `TextLoader` 등을 사용하여 문서를 로드합니다.
- **Text Splitter:** `RecursiveCharacterTextSplitter`로 문서를 의미 있는 단위의 청크로 분할합니다.
- **Embedding & Storage:** `OpenAIEmbeddings` 모델로 각 청크를 벡터로 변환하고, 공유 **ChromaDB 인스턴스**에 저장합니다. 이때, PostgreSQL `documents` 테이블의 `id`를 메타데이터로 함께 저장하여 출처를 추적합니다.

## Phase 3: 보조 Agent(Tool) 동적 생성 로직 구현
- **목표:** PostgreSQL에 저장된 '보조 Agent' 설정 정보를 읽어, LangChain의 `Tool` 객체로 동적으로 변환하는 핵심 로직을 구현합니다.
- 실행 계획:
### 1. `agent_service.py`에 Tool 생성 함수 구현:
- `create_sub_agent_tool(agent_config: Agent)` 함수를 정의합니다.
### 2. Tool 내부 RAG 체인 구성:
- 함수 내에서, 전달받은 `agent_config`를 사용하여 개별 RAG 체인을 구성합니다.
- Retriever: 공유 ChromaDB를 기반으로 retriever를 설정합니다.
- Prompt Template: agent_config.system_prompt를 포함하는 프롬프트 템플릿을 생성합니다.
- LLM: agent_config.model과 agent_config.temperature를 사용하여 LLM을 초기화합니다.
- 이 요소들을 LCEL로 연결하여 완전한 RAG 체인을 만듭니다.
### 3. Tool 객체 반환:
- 생성된 RAG 체인을 실행 로직(func)으로 하고, agent_config.name과 역할 설명(메인 Agent가 참조할 내용)을 포함하는 LangChain Tool 객체를 생성하여 반환합니다.

## Phase 4: 메인 Agent 및 최종 파이프라인 구성
- 목표: 모든 보조 Agent(Tool)를 지휘하는 메인 Agent를 생성하고, 전체 실행 파이프라인(AgentExecutor)을 완성합니다.
- 실행 계획:
### 1. agent_service.py에 메인 Agent 실행 함수 구현:
- run_main_agent(user_message: str, session_id: str) 함수를 정의합니다.
### 2. 동적 Tool 로딩:
- 함수 실행 시, PostgreSQL agents 테이블에서 agent_type = 'sub'인 모든 보조 Agent 설정을 조회합니다.
- 조회된 각 설정을 create_sub_agent_tool 함수에 전달하여 Tool 객체 리스트를 동적으로 생성합니다.
### 3. 메인 Agent 및 Executor 생성:
- DB에서 agent_type = 'main'인 메인 Agent의 설정을 조회합니다.
- create_openai_tools_agent를 사용하여 메인 Agent를 생성합니다. 이때, 동적으로 생성된 Tool 리스트를 함께 전달합니다.
- 메인 Agent와 Tool 리스트를 AgentExecutor에 담아 최종 실행 파이프라인을 구성합니다.
### 4. 대화 기록(Memory) 연동:
- session_id를 기반으로 chat_messages 테이블에서 이전 대화 기록을 조회하고, 이를 AgentExecutor의 메모리에 주입하여 대화의 맥락을 유지합니다.
### 5. 파이프라인 실행 및 결과 반환:
- AgentExecutor를 user_message와 함께 실행(invoke)하고, 최종 결과를 반환합니다.

## Phase 5: API 엔드포인트 연동 및 데이터 저장
- 목표: FastAPI 라우터와 서비스 로직을 연결하고, 대화 결과를 DB에 저장합니다.
- 실행 계획:
### 1. /chat 엔드포인트 구현:
- api/endpoints.py의 /chat 라우터에서 요청을 받습니다.
- agent_service.run_main_agent 함수를 호출하여 AI의 응답을 받습니다.
### 2. 대화 내용 저장:
- 사용자의 메시지와 AI의 최종 답변을 chat_messages 테이블에 저장합니다.
- AI 답변의 경우, 실행 과정에서 수집된 메타데이터(사용한 보조 Agent, 참조 문서 등)를 metadata 컬럼(JSONB)에 함께 저장합니다.
### 3. 응답 반환:
- API 명세서(v2.0)에 정의된 형식에 맞춰 최종 응답을 클라이언트에게 반환합니다.