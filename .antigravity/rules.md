# Global Project & Autonomous GitHub Workflow Rules

## 1. Project Initialization & Auto-Execution Trigger
- 사용자가 새로운 작업, 기능 요구사항, 또는 프로젝트 시작을 지시하면 **세부 프롬프트를 일일이 입력하지 않아도** 시스템이 자동으로 아래 파이프라인 트리거를 기본 동작으로 간주하고 실행합니다:
  > **[Default Execution Pipeline with GitHub]**
  > 1. `@pm`: 이슈 분석 및 `feature/<task-name>` (또는 `fix/<task-name>`) Git 브랜치 생성
  > 2. `@dba`: 스키마/마이그레이션 DDL 작성 및 버전 관리
  > 3. `@developer`: 비즈니스 로직 구현 및 단계별 Conventional Commit (`feat:`, `fix:`, `refactor:`)
  > 4. `@qa`: 단위/통합 테스트 스위트 작성 및 검증 통과
  > 5. `@auditor`: 보안 취약점(OWASP) 및 코드 품질 심층 감사 (Read-Only)
  > 6. `@devops`: 빌드/CI 환경 점검, 원격 브랜치 `git push origin` 및 Pull Request(PR) 템플릿 생성
  > 7. `@writer`: API 명세서, README.md, CHANGELOG.md 최신화 커밋

## 2. GitHub & Quality Gate Constraints
- **Branch Protection:** 메인 브랜치(`main` 또는 `master`)에 직접 커밋하지 않으며, 항상 `@pm`이 생성한 작업 브랜치에서 진행합니다.
- **Commit Convention:** 모든 커밋은 Conventional Commits 표준(`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`)을 준수합니다.
- **Strict Quality Gate:** `@qa`의 테스트 통과와 `@auditor`의 보안 승인(High/Critical 취약점 없음)이 완료되어야만 `@devops` 단계에서 원격 push 및 PR 생성이 승인됩니다.
- **Zero Manual Overhead:** 브랜치 분기부터 커밋, 푸시, PR 설명 작성까지 전 과정을 에이전트가 백그라운드에서 자율 완수합니다.
