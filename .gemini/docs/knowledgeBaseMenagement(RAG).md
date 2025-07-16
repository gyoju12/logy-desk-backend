|구분|내용|
|:--|:--|
|문서 버전|v0.1.0|
|최종 수정일|2025년 7월 16일|

# 지식 베이스 강화 시스템 아키텍처 초안
## 1. 목표
> 본 문서는 `Logy-Desk`의 지식 베이스 기능을 강화하기 위한 시스템 구조와 아키텍처 초안을 정의합니다. 사용자가 업로드한 문서를 체계적으로 `처리`, `저장`, `관리`하고, 이를 Multi-Agent 파이프라인과 안정적으로 통합하여 RAG(검색 증강 생성) 성능을 극대화하는 것을 목표로 합니다.

## 2. 핵심 문제 해결: 비동기 처리 파이프라인 도입
> 기존 구조의 가장 큰 문제는 문서 업로드와 동시에 모든 처리(분할, 임베딩)를 완료하려는 동기식 접근 방식에 있습니다. 문서의 크기가 크거나 여러 문서가 동시에 업로드될 경우, API 응답 시간이 길어지고 시스템에 부하를 주게 됩니다.
>
> 이를 해결하기 위해, **비동기(Asynchronous) 처리 파이프라인**을 도입합니다.

- **동작 방식:**
  1. [API] 빠른 응답: 사용자가 문서를 업로드하면, API는 파일을 저장하고 즉시 "업로드 접수 완료" 응답을 보냅니다.
  2. [백그라운드] 작업 처리: 실제 문서 분할 및 임베딩 작업은 별도의 백그라운드 워커(Background Worker)가 비동기적으로 수행합니다.
  3. [DB] 상태 추적: `documents`와 `document_chunks` 테이블의 `status 컬럼을 통해, 프론트엔드는 각 문서와 청크의 처리 상태를 실시간으로 확인할 수 있습니다.

## 3. 전체 시스템 아키텍처
```
[사용자 (프론트엔드)]
       | 1. 문서 업로드 (POST /documents/upload)
       v
[FastAPI 백엔드 (API 서버)]
       | 2. 파일 저장 & DB에 문서 정보 생성 (status: 'PENDING') & 빠른 응답
       |
       | 3. 백그라운드 작업 큐에 '문서 처리' 작업 추가
       v
[백그라운드 워커 (Celery, Dramatiq 등)]
       | 4. 작업 수신
       | 5. 문서 분할 (Text Splitter) -> `document_chunks` 테이블에 저장 (status: 'PENDING')
       | 6. 각 청크 임베딩 (Embedding Model)
       | 7. 벡터 DB에 저장 (Vector DB)
       | 8. `document_chunks` 상태 업데이트 (status: 'COMPLETED')
       | 9. 모든 청크 완료 시 `documents` 상태 업데이트 (status: 'COMPLETED')
       v
[데이터베이스 계층]
  - PostgreSQL (Cloud SQL): 문서 및 청크 메타데이터, 처리 상태 관리
  - Vector DB (ChromaDB/Vertex AI): 임베딩된 벡터 저장 및 검색
```

## 4. 데이터베이스 스키마 (RAG 강화)
피드백을 반영하여 `DB 구축 및 테이블 설계서 (RAG 강화)`에 정의된 스키마를 기반으로 합니다.
- **`documents` 테이블:**
  - `processing_status`: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`
  - `summary`: AI가 생성한 문서 요약
  - `doc_type`: `MANUAL`, `FAQ` 등 문서 분류
- **`document_chunks` 테이블:**
  - `id`: Vector DB의 벡터 ID와 동일하게 사용하여 두 시스템을 연결합니다.
  - `embedding_status`: `PENDING`, `COMPLETED`, `FAILED`
  - `num_tokens`: 청크의 토큰 수 (비용 및 성능 분석용)

## 5. 세부 기능 구현 계획
### 5.1. 문서 관리 (백엔드)
- **문서 업로드 API (`POST /documents/upload`):**
  - 파일을 GCS(Google Cloud Storage)와 같은 스토리지에 저장합니다.
  - documents 테이블에 파일 메타데이터와 함께 processing_status='PENDING'으로 레코드를 생성합니다.
  - 백그라운드 작업 큐에 document_id와 함께 '문서 처리' 작업을 전달합니다.
- **문서 상태 조회 API (`GET /documents/{document_id}`):**
  - `documents` 테이블과 `document_chunks` 테이블을 조인하여, 특정 문서의 전체 처리 상태와 각 청크의 임베딩 상태를 함께 반환합니다.

### 5.2. 벡터 검색 및 RAG (백엔드)
- **Retriever 로직 개선:**
  - 보조 Agent의 RAG 체인 내에서 retriever를 설정할 때, embedding_status='COMPLETED'인 청크만 검색 대상이 되도록 필터링 로직을 추가합니다.
  - 사용자 질문을 임베딩하여 Vector DB에서 유사도 높은 청크의 ID 목록을 가져옵니다.
  - 가져온 ID를 사용하여 document_chunks 테이블에서 실제 텍스트 내용을 조회하여 최종 컨텍스트를 구성합니다.

### 5.3. 지식 베이스 관리 (프론트엔드)
- **문서 목록 UI:**
  - `GET /documents` API를 주기적으로 호출(폴링)하거나, 웹소켓을 사용하여 각 문서의 `processing_status`를 실시간으로 표시합니다. (예: 처리중, 완료, 실패)
- **문서 상세 UI:**
  - 특정 문서를 클릭하면, 문서의 요약 정보와 함께 각 청크의 내용 및 `embedding_status`를 확인할 수 있는 상세 페이지를 제공합니다.
- 문서 분류 및 필터링:
  - 사용자가 문서를 업로드할 때 `doc_type`을 지정하거나, 업로드된 문서에 태그를 추가할 수 있는 기능을 제공합니다.
  - 이 정보를 바탕으로 지식 베이스 문서를 필터링하여 검색할 수 있습니다.

## 6. 다음 단계
이 아키텍처 초안을 바탕으로, `feature/knowledge-base-management` 브랜치에서 다음 작업을 시작할 수 있습니다.
- 백엔드: 백그라운드 워커(예: Celery) 환경을 설정하고, 비동기 문서 처리 파이프라인의 기본 로직을 구현합니다.
- 프론트엔드: 지식 베이스 관리 페이지의 UI를 구현하고, 문서 업로드 및 상태 조회 API와 연동합니다.