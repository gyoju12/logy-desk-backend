# Logy-Desk MVP DB 구축 및 테이블 설계서 (Multi-Agent 기반)
## 1. 개요
> 본 문서는 `Logy-Desk`의 Multi-Agent 기반 서비스의 안정적인 데이터 관리를 위한 PostgreSQL 데이터베이스 구축 계획 및 상세 테이블 스키마를 정의합니다. 설계의 기반은 최신 기능 명세서, 아키텍처, API 명세서이며, 백엔드 애플리케이션과의 원활한 연동을 목표로 합니다.

## 2. DB 구축 및 연동 계획
- **데이터베이스 선정:** PostgreSQL
  - 선정 이유: 강력한 오픈소스 관계형 데이터베이스로, 데이터의 정합성과 안정성이 중요하며 향후 기능 확장에 따른 복잡한 쿼리 처리에 용이합니다. JSONB 데이터 타입을 지원하여 유연한 메타데이터 저장이 가능합니다.
- **개발 환경 구축:**
  - **로컬 환경:** Docker를 사용하여 PostgreSQL 컨테이너를 실행하는 것을 권장합니다. 이를 통해 개발자 간의 환경을 통일하고 빠르게 구축할 수 있습니다.
    ```bash
    # Docker를 사용한 PostgreSQL 실행 예시
    docker run --name logy-desk-db -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres
    ```
  - **DB 연결 설정:** FastAPI 애플리케이션의 .env 파일에 데이터베이스 연결 정보(URL)를 설정하고, core/config.py에서 이를 읽어 사용합니다.
- **ORM 및 마이그레이션 도구:**
  - **ORM (Object-Relational Mapper):** SQLAlchemy
    - **선택 이유:** Python 코드(클래스)와 DB 테이블을 매핑하여, SQL 쿼리를 직접 작성하지 않고도 객체 지향적으로 데이터를 처리할 수 있게 해주는 가장 성숙한 라이브러리입니다.
  - **스키마 마이그레이션:** Alembic
    - **선택 이유:** SQLAlchemy와 함께 사용되며, DB 스키마의 변경 이력을** 코드로 관리하고 버전 관리를 가능하게 하여 팀 협업 시 스키마 불일치 문제를 방지합니다.

## 3. 테이블 스키마 설계
> Multi-Agent 아키텍처의 핵심 기능(사용자, 에이전트, 문서, 채팅)을 중심으로 총 5개의 테이블을 설계합니다.

### 3.1. `users`
- **설명:** 사용자 계정 정보를 저장합니다.
- **컬럼 정의:**

    | 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
    | :--- | :--- | :--- | :--- |
    | id | UUID | PRIMARY KEY | 사용자 고유 식별자 |
    | email | VARCHAR(255) | UNIQUE, NOT NULL | 로그인 시 사용할 이메일 주소 |
    | hashed_password | VARCHAR(255) | NOT NULL | 해싱 처리된 비밀번호 |
    | created_at | TIMESTAMPTZ | NOT NULL | 계정 생성 시각 |
    | updated_at | TIMESTAMPTZ | NOT NULL | 계정 정보 수정 시각 |

### 3.2. agents
- **설명:** 메인(라우터) Agent와 보조(전문가) Agent의 설정 정보를 저장합니다.
- **컬럼 정의:**

    | 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
    | :--- | :--- | :--- | :--- |
    | id | UUID | PRIMARY KEY | Agent 고유 식별자 |
    | user_id | UUID | FOREIGN KEY (users.id) | Agent를 생성한 사용자 ID |
    | name | VARCHAR(100) | NOT NULL | Agent 이름 (예: 메인 라우터 Agent) |
    | agent_type | VARCHAR(10) | NOT NULL | Agent 타입 ('main' 또는 'sub') |
    | model | VARCHAR(50) | NOT NULL | 사용할 AI 모델명 (예: gpt-4o-mini) |
    | temperature | FLOAT | NOT NULL, DEFAULT 0.5 | AI의 창의성 값 (0.0 ~ 1.0) |
    | system_prompt | TEXT | NOT NULL | AI의 역할/말투를 정의하는 시스템 프롬프트 |
    | created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 |
    | updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 |

### 3.3. documents
- **설명:** 모든 Agent가 공유하는 RAG 지식 베이스 문서의 메타데이터를 저장합니다.
- **컬럼 정의:**

    | 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
    | :--- | :--- | :--- | :--- |
    | id | UUID | PRIMARY KEY | 문서 고유 식별자 |
    | user_id | UUID | FOREIGN KEY (users.id) | 문서를 업로드한 사용자 ID |
    | filename | VARCHAR(255) | NOT NULL | 업로드된 원본 파일 이름 |
    | created_at | TIMESTAMPTZ | NOT NULL | 업로드 시각 |

### 3.4. chat_sessions
- **설명:** 하나의 완전한 대화 단위를 나타내는 세션 정보를 저장합니다. 프론트엔드 사이드바의 상담 내역을 구성하는 데 사용됩니다.
- **컬럼 정의:**

    | 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
    | :--- | :--- | :--- | :--- |
    | id | UUID | PRIMARY KEY | 채팅 세션 고유 식별자 |
    | user_id | UUID | FOREIGN KEY (users.id) | 세션을 시작한 사용자 ID |
    | title | VARCHAR(255) | NOT NULL | 대화 제목 (첫 질문으로 자동 생성) |
    | created_at | TIMESTAMPTZ | NOT NULL | 세션 시작 시각 |
    | updated_at | TIMESTAMPTZ | NOT NULL | 마지막 메시지 시각 |

### 3.5. chat_messages
- **설명:** 각 채팅 세션에 속한 개별 메시지를 저장합니다. AI 답변의 경우, 생성에 사용된 메타데이터를 JSONB 타입으로 함께 저장하여 추적성을 높입니다.
- **컬럼 정의:**

    | 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
    | :--- | :--- | :--- | :--- |
    | id | BIGSERIAL | PRIMARY KEY | 메시지 고유 식별자 (자동 증가) |
    | session_id | UUID| FOREIGN KEY (chat_sessions.id) | 메시지가 속한 세션 ID |
    | role | VARCHAR(10) | NOT NULL | 메시지 발화자 ('user' 또는 'assistant') |
    | content | TEXT | NOT NULL | 메시지 내용 |
    | metadata | JSONB | | AI 답변 생성 관련 메타데이터 (사용한 Agent, 참조 문서 등) |
    | created_at | TIMESTAMPTZ | NOT NULL | 메시지 생성 시각 |

### 4. 테이블 생성 쿼리 (SQL DDL)
```SQL
-- UUID 생성을 위한 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- updated_at 컬럼 자동 업데이트를 위한 트리거 함수 생성
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';

-- 1. users 테이블 생성
CREATE TABLE users (
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
email VARCHAR(255) UNIQUE NOT NULL,
hashed_password VARCHAR(255) NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 2. agents 테이블 생성
CREATE TABLE agents (
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
name VARCHAR(100) NOT NULL,
agent_type VARCHAR(10) NOT NULL, -- 'main' or 'sub'
model VARCHAR(50) NOT NULL,
temperature FLOAT NOT NULL DEFAULT 0.5,
system_prompt TEXT NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER update_agents_updated_at
BEFORE UPDATE ON agents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 3. documents 테이블 생성
CREATE TABLE documents (
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
filename VARCHAR(255) NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. chat_sessions 테이블 생성
CREATE TABLE chat_sessions (
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
title VARCHAR(255) NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER update_chat_sessions_updated_at
BEFORE UPDATE ON chat_sessions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 5. chat_messages 테이블 생성
CREATE TABLE chat_messages (
id BIGSERIAL PRIMARY KEY,
session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
role VARCHAR(10) NOT NULL,
content TEXT NOT NULL,
metadata JSONB,
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 인덱스 추가 (성능 향상을 위해)
CREATE INDEX idx_agents_user_id ON agents(user_id);
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
```