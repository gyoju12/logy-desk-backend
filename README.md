# Logy Desk Backend

Python/FastAPI 기반의 멀티 에이전트 채팅 백엔드 애플리케이션

## 기능

- 에이전트 관리 (생성, 조회, 수정, 삭제)
- 문서 업로드 및 관리
- 채팅 세션 관리
- 멀티 에이전트 기반 채팅

## 개발 환경 설정

### 필수 구성 요소

- Python 3.9+
- PostgreSQL
- pip (Python 패키지 관리자)

### 의존성 설치

```bash
# 프로젝트 클론
# 의존성 설치
pip install -r requirements.txt

# 개발용 의존성 설치 (선택사항)
pip install -r requirements-test.txt
```

### 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/logy_desk_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 데이터베이스 설정

1. PostgreSQL 데이터베이스 생성:
```bash
createdb logy_desk_db
```

2. 마이그레이션 실행:
```bash
alembic upgrade head
```

## 개발 서버 실행

```bash
uvicorn app.main:app --reload
```

서버가 시작되면 다음 주소에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 테스트 커버리지 보고서 생성
pytest --cov=app tests/
```

## API 문서

API 엔드포인트와 모델에 대한 자세한 내용은 다음을 참조하세요:
- [API 문서](./docs/API.md)
- [데이터베이스 스키마](./docs/DB_SCHEMA.md)

## 개발 가이드

### 코드 스타일

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) 스타일 가이드 준수
- 타입 힌트 사용 권장
- 모든 공개 API에 대한 문서화 문자열 작성

### 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 규칙을 따릅니다:

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 과정 또는 보조 도구 수정

## 라이선스

MIT
