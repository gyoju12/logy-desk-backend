| 구분 | 내용 |
=============
| 문서 버전 | v0.2.1 |
| 최종 수정일 | 2025년 7월 5일 |

Logy-Desk MVP API 명세서 (Multi-Agent 기반)
# 1. 기본 정보
- **Base URL:** `/api/v1`
- **인증:** MVP 단계에서는 생략. 추후 JWT (JSON Web Token) 기반 인증 도입 예정.
- **데이터 형식:** 모든 요청과 응답의 본문(Body)은 JSON 형식을 사용합니다.

# 2. 공통 응답 모델
- **에러 응답 (Error Response)**
  - HTTP Status: `4xx` 또는 `5xx`
  - **Body:**
    ```JSON
    {
      "detail": "에러 발생 원인에 대한 상세 메시지"
    }
    ```

# 3. API 엔드포인트 상세

## 3.1. Agents (메인/보조 에이전트)
'페르소나'가 'Agent' 개념으로 대체됩니다. agent_type으로 'main'(라우터)과 'sub'(전문가)를 구분합니다.

### `POST /agents` **(Create)**
- **Description:** 새로운 메인 또는 보조 Agent를 생성합니다.
- **Request Body:**
  ```JSON
  {
    "name": "새로운 Agent 이름",
    "agent_type": "sub",
    "model": "gpt-4o-mini",
    "temperature": 0.5,
    "system_prompt": "이 Agent의 역할과 전문 분야를 정의합니다."
  }
  ```
- **Success Response (201 Created):**
  ```JSON
  {
    "id": "agent_new456",
    "name": "새로운 Agent 이름",
    "agent_type": "sub",
    "model": "gpt-4o-mini",
    "temperature": 0.5,
    "system_prompt": "이 Agent의 역할과 전문 분야를 정의합니다."
  }
  ```

### `GET /agents` **(Read All)**
- **Description:** 모든 Agent 목록을 조회합니다. 쿼리 파라미터로 타입을 필터링할 수 있습니다.
- **Query Parameter:** type (string, optional) - 'main' 또는 'sub'
- **Success Response (200 OK):**
  ```JSON
  {
    "agents": [
      {
        "id": "agent_abc123",
        "name": "메인 라우터 Agent",
        "agent_type": "main",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "system_prompt": "사용자의 요청을 분석하여 가장 적합한 전문가에게 작업을 위임합니다."
      },
      {
        "id": "agent_def456",
        "name": "결제/환불 정책 전문가",
        "agent_type": "sub",
        "model": "claude-3-5-sonnet",
        "temperature": 0.7,
        "system_prompt": "환불 정책 전문가로서 약관에 기반하여 정확하게 답변합니다."
      }
    ]
  }
  ```

### `GET /agents/{agent_id}` **(**Read One)
- **Description:** 특정 ID의 Agent 정보를 조회합니다.
- **Success Response (200 OK):**
  ```JSON
  {
    "id": "agent_def456",
    "name": "결제/환불 정책 전문가",
    "agent_type": "sub",
    "model": "claude-3-5-sonnet",
    "temperature": 0.7,
    "system_prompt": "환불 정책 전문가로서 약관에 기반하여 정확하게 답변합니다."
  }
  ```

### `PUT /agents/{agent_id}` **(Update)**
- **Description:** 특정 ID의 Agent 정보를 업데이트합니다.
- **Success Response (200 OK):**
  ```JSON
  {
    "id": "agent_def456",
    "name": "수정된 환불 정책 전문가",
    "agent_type": "sub",
    "model": "claude-3-5-sonnet",
    "temperature": 0.8,
    "system_prompt": "수정된 시스템 프롬프트입니다. 더 자세한 안내를 제공합니다."
  }
  ```

### `DELETE /agents/{agent_id}` **(Delete)**
- **Description:** 특정 ID의 Agent를 삭제합니다.
- **Success Response (204 No Content):** 응답 본문 없음.

## 3.2. 지식 베이스 (Knowledge Base - RAG)
모든 Agent가 공유하는 중앙 지식 베이스 역할을 합니다.

### `POST /documents/upload` **(Create)**
- **Description:** 지식 베이스로 사용할 문서를 업로드하고 처리합니다.
- **Request Body:** multipart/form-data 형식으로 파일 전송 (file 키 사용).
- **Success Response (200 OK):**
  ```JSON
  {
    "message": "파일이 성공적으로 업로드 및 처리되었습니다.",
    "filename": "상담매뉴얼_v2.pdf",
    "document_id": "doc_abc123"
  }
  ```

### `GET /documents` **(Read All)**
- **Description:** 업로드된 모든 문서의 메타데이터 목록을 조회합니다.
- **Success Response (200 OK):**
  ```JSON
  {
    "documents": [
      {
        "id": "doc_abc123",
        "filename": "상담매뉴얼_v2.pdf",
        "uploaded_at": "2025-07-05T12:00:00Z"
      }
    ]
  }
  ```

### `DELETE /documents/{document_id}` **(Delete)**
- **Description:** 특정 ID의 문서를 지식 베이스에서 삭제합니다.
- **Path Parameter:** document_id (string) - 삭제할 문서의 고유 ID.
- **Success Response (200 OK):**
  ```JSON
  {
    "message": "문서(ID: doc_abc123)가 성공적으로 삭제되었습니다."
  }
  ```

## 3.3. 상담 내역 (Chat Sessions)
프론트엔드 사이드바에 이전 대화 목록을 표시하기 위한 API입니다. (참고: 명시적인 세션 시작/종료 API 추가는 추후 논의될 예정이며, MVP 단계에서는 첫 메시지 전송 시 세션이 자동 생성됩니다.)

### `GET /chat_sessions` **(Read All)**
- **Description:** 현재 사용자의 모든 상담 세션 목록을 최신순으로 조회합니다.
- **Success Response (200 OK):**
```JSON
{
  "sessions": [
    {
      "id": "session_xyz789",
      "title": "비밀번호 재설정 관련 문의",
      "created_at": "2025-07-05T11:00:00Z"
    }
  ]
}
```

### `GET /chat_sessions/{session_id}` **(Read One)**
- **Description:** 특정 상담 세션의 전체 대화 기록을 조회합니다.
- **Success Response (200 OK):**
  ```JSON
  {
    "id": "session_xyz789",
    "title": "비밀번호 재설정 관련 문의",
    "messages": [
      { "role": "user", "content": "안녕하세요, 비밀번호를 잊어버렸어요." },
      { "role": "assistant", "content": "네, 비밀번호 재설정을 도와드리겠습니다..." }
    ]
  }
  ```

### `DELETE /chat_sessions/{session_id}` **(Delete)**
- **Description:** 특정 상담 세션을 삭제합니다.
- **Success Response (204 No Content):**응답 본문 없음.

## 3.4. 메인 채팅 (Chat)

### `POST /chat`
- **Description:** 단일화된 채팅 인터페이스를 통해 메인 Agent에게 요청을 보냅니다.
- **Request Body:**
  ```JSON
  {
    "user_message": "결제 수단을 바꾸고 싶은데, 환불도 가능한가요?",
    "session_id": "session_xyz789"
  }
  ```
- **Success Response (200 OK):**
  ```JSON
  {
    "session_id": "session_xyz789",
    "assistant_message": "네, 결제 수단 변경 및 환불 정책에 대해 안내해 드리겠습니다. (결제 담당 Agent와 환불 정책 전문가의 답변을 종합함)",
    "metadata": {
      "used_agents": [
        { "id": "agent_def456", "name": "결제/환불 정책 전문가" },
        { "id": "agent_ghi789", "name": "결제 시스템 담당자" }
      ],
      "retrieved_sources": [
        { "document_id": "doc_abc123", "content_snippet": "..." }
      ]
    }
  }
  ```

# 4. 추후 계획 (Future Plans)기
> 대시보드 API: 상담 내역 분석 및 시각화를 위한 대시보드 관련 API는 MVP 이후 단계에서 구체화될 예정입니다.