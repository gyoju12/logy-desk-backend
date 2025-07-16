|구분|내용|
|:--|:--|
|문서 버전|v1.1.0|
|기반 아키텍처|지식 베이스 강화 시스템 아키텍처 초안 v0.1.1|

# 지식 베이스 관리 기능 고도화 작업 내역서
본 문서는 `feature/knowledge-base-management` 브랜치에서 수행할 **지식 베이스 기능 고도화 작업**을 위한 상세 내역입니다.

## 1. 백엔드 (Backend)
### 1.1. 비동기 처리 환경 구축
- [ ] 백그라운드 작업 큐 라이브러리 선정 및 설치 (예: Celery with Redis/RabbitMQ)
- [ ] FastAPI 프로젝트에 Celery 기본 설정 및 초기화 코드 추가
- [ ] 백그라운드 워커를 실행하기 위한 별도의 실행 스크립트 작성

### 1.2. 데이터베이스 스키마 마이그레이션
- [ ] `documents 테이블 구조 변경 (Alembic 마이그레이션 스크립트 작성)
  - [ ] `summary`, `doc_type 등 메타데이터 컬럼 추가
- [ ] 기존 `document_chunks 테이블 분석 및 필요시 고도화 (Alembic 마이그레이션 스크립트 작성)

### 1.3. 문서 관리 API 개선
- [ ] `POST /documents/upload API 수정
  - [ ] 파일 수신 후 임시 저장소에 저장하는 로직 구현 **(추후 GCS 등 클라우드 스토리지로 전환을 고려한 추상화된 인터페이스 설계)**
  - [ ] `documents` 테이블에 파일 메타데이터와 함께 `processing_status='PENDING'으로 레코드 생성
  - [ ] Celery 작업 큐에 `document_id와 **임시 파일 경로**를 함께 '문서 처리' 태스크 전달
  - [ ] API는 파일 처리 완료를 기다리지 않고 즉시 `document_id`와 함께 응답
- [ ] `GET /documents/{document_id}/status **API 신규 개발**
  - [ ] 특정 문서의 전체 처리 상태와, 해당 문서에 속한 모든 청크의 `embedding_status`를 함께 조회하여 반환하는 기능 구현

### 1.4. 비동기 문서 처리 파이프라인 구현 (Background Worker)
- [ ] **'문서 처리' 태스크 정의 (`tasks.py`)**
  - [ ] `document_id`와 `file_path`를 인자로 받아 처리 시작
  - [ ] `documents` 테이블의 `status`를 `'PROCESSING'`으로 업데이트
  - [ ] 전달받은 `file_path`에서 원본 파일 로드
  - [ ] LangChain `DocumentLoader를 사용하여 문서 내용 로드
  - [ ] LangChain `TextSplitter`를 사용하여 텍스트를 청크로 분할
  - [ ] 각 청크에 대해 `document_chunks 테이블에 레코드 생성 (`embedding_status='PENDING'`)
  - [ ] 각 청크별로 '임베딩 생성' 서브 태스크를 큐에 추가
  - [ ] 처리 완료 후 임시 파일 삭제 로직 추가
- [ ] **'임베딩 생성' 태스크 정의 (`tasks.py`)**
  - [ ] `chunk_id`를 인자로 받아 처리 시작
  - [ ] `document_chunks` 테이블에서 청크 내용 조회
  - [ ] 임베딩 모델을 사용하여 텍스트를 벡터로 변환
  - [ ] 변환된 벡터를 `chunk_id`와 함께 **Vector DB**에 저장
  - [ ] `document_chunks` 테이블의 `embedding_status`를 `'COMPLETED'`로 업데이트 (실패 시 `'FAILED'`)
  - [ ] (선택) 모든 청크 완료 시, `documents`의 `processing_status`를 `'COMPLETED'`로 업데이트하는 로직 추가

### 1.5. RAG 로직 개선
- [ ] 보조 **Agent의 Retriever** 설정 시, **Vector DB**에서 벡터 검색 시 필터링 기능 추가
  - [ ] `document_chunks` 테이블과 연계하여 `embedding_status`가 `'COMPLETED'`인 청크의 벡터만 검색 대상이 되도록 로직 수정

## 2. 프론트엔드 (Frontend)
### 2.1. 지식 베이스 관리 페이지 UI/UX 구축
- [ ] `/knowledge` 경로 및 페이지 컴포넌트(`knowledge-manager.tsx`) 생성
- [ ] 헤더(`header.tsx)에 '지식 베이스 관리' 내비게이션 링크 추가
- [ ] **문서 업로드 컴포넌트 (`document-uploader.tsx`) 구현**
  - [ ] 파일 선택(Drag & Drop 지원 포함) UI 구현
  - [ ] 업로드 버튼 클릭 시 `POST /documents/upload` API 호출
  - [ ] 업로드 진행 상태(Progress Bar) 표시
- [ ] **문서 목록 컴포넌트 (`document-list.tsx`) 구현**
  - [ ] 문서 목록을 표시할 테이블 UI 구현 (파일명, 업로드 일시, 처리 상태 등)
  - [ ] `GET /documents` API를 호출하여 목록 데이터 바인딩
  - [ ] **(중요)** `processing_status` 실시간 업데이트 기능 구현 (주기적인 API 폴링 또는 웹소켓 사용)
  - [ ] 각 문서에 대한 삭제 버튼 및 `DELETE /documents/{id}` API 연동
  - [ ] 문서 클릭 시 상세 정보 확인 페이지로 이동하는 기능

### 2.2. 상태 관리 (Zustand)
- [ ] `document-store.ts` 신규 생성
  - [ ] `documents (문서 목록), `uploadStatus` 등 상태 정의
  - [ ] `fetchDocuments`, `uploadDocument`, `deleteDocument 등 API와 연동될 액션 정의

## 3. 테스트 및 배포
- [ ] **백엔드 테스트:**
  - [ ] 비동기 문서 처리 파이프라인의 각 단계(업로드, 분할, 임베딩)에 대한 단위 테스트 작성
  - [ ] 문서 처리 실패 시 `status`가 `'FAILED'`로 정상 변경되는지 예외 케이스 테스트
- [ ] **프론트엔드 테스트:**
  - [ ] 문서 업로드 및 목록 실시간 갱신 기능에 대한 E2E 테스트
- [ ] **배포 전략:**
  - [ ] 백그라운드 워커(Celery)를 위한 별도의 Docker 컨테이너 및 실행 환경 구성
  - [ ] GCP Cloud Run 또는 GKE에 API 서버와 워커 서비스를 함께 배포하도록 CI/CD 파이프라인 수정