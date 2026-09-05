# Global Project & Autonomous GitHub Workflow Rules

## 1. Project Initialization & Auto-Execution Trigger
- 사용자가 새로운 작업, 기능 요구사항, 또는 프로젝트 시작을 지시하면 **세부 프롬프트를 일일이 입력하지 않아도** 시스템이 자동으로 아래 파이프라인 트리거를 기본 동작으로 간주하고 실행합니다:
  > **[Default Execution Pipeline with GitHub & Multi-PC Context Sync]**
  > 1. `@pm`: 이슈/요구사항 분석, **`PROJECT_CONTEXT.md` 자동 생성/점검**, `feature/<task-name>` (또는 `fix/<task-name>`) Git 브랜치 생성
  > 2. `@dba`: 스키마/마이그레이션 DDL 작성 및 버전 관리
  > 3. `@developer`: 비즈니스 로직 구현 및 단계별 Conventional Commit (`feat:`, `fix:`, `refactor:`)
  > 4. `@qa`: 단위/통합 테스트 스위트 작성 및 검증 통과
  > 5. `@auditor`: 보안 취약점(OWASP) 및 코드 품질 심층 감사 (Read-Only)
  > 6. `@devops`: 빌드/CI 환경 점검, 원격 브랜치 `git push origin` 및 Pull Request(PR) 템플릿 생성
  > 7. `@writer`: API 명세서, README.md, CHANGELOG.md 및 **`PROJECT_CONTEXT.md`(작업 맥락/진행 상태/Next Actions) 최신화 동기화 커밋**

## 2. 🧠 Multi-PC Seamless Continuity & PROJECT_CONTEXT.md Protocol
- **신규 프로젝트 자동 생성:** 새 프로젝트 시작 시 `PROJECT_CONTEXT.md`가 없으면 `@pm`이 비즈니스 도메인, 아키텍처 구조, 핵심 기능, 개발 주의사항, 검증 명령어가 포함된 표준 템플릿으로 자동 생성합니다.
- **다중 환경(집/회사/노트북) 연속성 보장:** 집(Home)과 회사(Office) 등 어떤 PC에서든 `git pull` 후 AI 어시스턴트가 `PROJECT_CONTEXT.md`를 최우선으로 로드하여 이전 세션의 설계 결정, 채팅 맥락, 현재 진행 상태를 100% 온전히 이어받아 작업합니다.
- **세션 종료/완료 시 실시간 현행화:** 작업 단위 완료 시 `@writer`가 대화에서 결정된 주요 아키텍처 변경, 추가된 기능, 잔여 과제(Next Actions)를 `PROJECT_CONTEXT.md`의 히스토리 섹션에 빠짐없이 동기화합니다.

## 3. GitHub & Quality Gate Constraints
- **Branch Protection:** 메인 브랜치(`main` 또는 `master`)에 직접 커밋하지 않으며, 항상 `@pm`이 생성한 작업 브랜치에서 진행합니다.
- **Commit Convention:** 모든 커밋은 Conventional Commits 표준(`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`)을 준수합니다.
- **Strict Quality Gate:** `@qa`의 테스트 통과와 `@auditor`의 보안 승인(High/Critical 취약점 없음)이 완료되어야만 `@devops` 단계에서 원격 push 및 PR 생성이 승인됩니다.
- **Zero Manual Overhead:** 브랜치 분기부터 커밋, 푸시, PR 설명 작성 및 컨텍스트 문서 동기화까지 전 과정을 에이전트가 백그라운드에서 자율 완수합니다.
