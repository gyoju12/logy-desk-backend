# Logy Desk Backend 기여 가이드

Logy Desk 백엔드 프로젝트에 기여해 주셔서 감사합니다! 이 문서는 프로젝트에 기여하기 위한 가이드라인을 제공합니다.

## 📋 시작하기 전에

1. [GitHub Issues](https://github.com/your-username/logy-desk-backend/issues)에서 작업할 이슈를 선택하거나 새 이슈를 생성해주세요.
2. 작업을 시작하기 전에 해당 이슈에 작업을 시작한다고 댓글을 남겨주세요.

## 🛠 개발 환경 설정

1. 저장소를 포크하고 클론합니다:
   ```bash
   git clone https://github.com/your-username/logy-desk-backend.git
   cd logy-desk-backend
   ```

2. Python 3.11+와 pip가 설치되어 있는지 확인하세요.

3. 가상환경을 생성하고 활성화합니다:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

4. 의존성을 설치합니다:
   ```bash
   pip install -e ".[dev]"
   ```

5. pre-commit 훅을 설정합니다:
   ```bash
   pre-commit install
   ```

## 🔧 개발 워크플로우

1. 최신 `main` 브랜치에서 새로운 기능 브랜치를 생성합니다:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. 변경사항을 커밋할 때는 [Conventional Commits](https://www.conventionalcommits.org/) 규칙을 따릅니다:
   ```
   feat: 새로운 기능 추가
   fix: 버그 수정
   docs: 문서 수정
   style: 코드 포맷팅, 세미콜론 누락 등
   refactor: 코드 리팩토링
   test: 테스트 코드 추가/수정
   chore: 빌드 프로세스, 패키지 매니저 설정 등
   ```

3. 변경사항을 커밋하기 전에 다음 명령어로 코드 품질을 확인하세요:
   ```bash
   black .
   isort .
   flake8
   mypy .
   pytest
   ```

4. 변경사항을 푸시하고 Pull Request를 생성합니다.

## 🧪 테스트

- 모든 테스트 실행:
  ```bash
  pytest
  ```

- 코드 커버리지 포함 테스트:
  ```bash
  pytest --cov=app --cov-report=term-missing
  ```

## 📝 Pull Request 가이드라인

1. PR 제목은 [타입]: 제목 형식으로 작성해주세요.
   - 예: `feat: 사용자 인증 기능 추가`

2. PR 설명에는 다음 내용을 포함해주세요:
   - 변경 사항에 대한 상세 설명
   - 관련된 이슈 번호 (Resolves #123)
   - 테스트 방법
   - 스크린샷 (UI 변경이 있는 경우)

3. PR을 보내기 전에 다음 사항을 확인해주세요:
   - 모든 테스트가 통과하는지
   - 코드가 포매팅 가이드라인을 준수하는지
   - 문서가 업데이트되었는지

## 🏷 코드 리뷰

- 모든 PR은 최소 1명 이상의 리뷰어의 승인이 필요합니다.
- 리뷰어는 코드 품질, 성능, 보안 등을 검토합니다.
- 리뷰 코멘트에 대한 피드백은 1주일 이내에 반영해주세요.

## 🚀 배포

- `main` 브랜치에 머지되면 자동으로 스테이징 환경에 배포됩니다.
- 태그를 푸시하면 프로덕션 환경에 배포됩니다:
  ```bash
  git tag -a v1.0.0 -m "버전 1.0.0"
  git push origin v1.0.0
  ```

## ❓ 도움이 필요하신가요?

질문이 있으시면 [이슈](https://github.com/your-username/logy-desk-backend/issues)를 생성해 주세요.
