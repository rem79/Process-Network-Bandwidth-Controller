---
name: enterprise-pipeline
description: >-
  Executes the 7-stage enterprise engineering pipeline (@pm, @dba, @developer, @qa, @auditor, @devops, @writer)
  with automated branch management, atomic commits, quality gate enforcement, and Multi-PC context synchronization.
  Use when starting a new feature, bugfix, or refactoring task.
---

# Enterprise 7-Stage Autonomous Pipeline

이 스킬은 비즈니스 요구사항을 수신하여 분석, 설계, 구현, 검증, 감사, 배포 및 컨텍스트 동기화까지 7단계를 완전 자율로 수행하는 엔터프라이즈 엔지니어링 표준 워크플로우입니다.

---

## 1. Pipeline Execution Stages

### Stage 1: Planning, Context & Branching (`@pm`)
1. 프로젝트 루트의 `PROJECT_CONTEXT.md` 존재 여부를 확인합니다.
   - 없을 경우 `PROJECT_CONTEXT_TEMPLATE.md`를 기반으로 즉시 생성합니다.
2. 사용자의 요구사항을 Task 단위 및 수용 기준(Acceptance Criteria)으로 분해합니다.
3. 작업 브랜치를 생성하고 전환합니다:
   ```bash
   git checkout -b feature/<task-name>
   # 또는 버그 수정 시
   git checkout -b fix/<task-name>
   ```
4. 디렉터리 및 아키텍처 스펙 문서를 정리합니다.

### Stage 2: Data & Schema Design (`@dba`)
1. 데이터 변경이 필요한 경우, 스키마 및 마이그레이션 DDL을 작성합니다.
2. 복합 인덱스, N+1 쿼리 방지 전략 및 트랜잭션 격리 수준을 정의합니다.

### Stage 3: Core Implementation & Atomic Commits (`@developer`)
1. 설계 명세를 바탕으로 비즈니스 로직 및 모듈을 구현합니다.
2. **개발 중 빌드 최소화 & 원클릭 배치 제공**: 무거운 바이너리(`.exe`) 빌드를 지양하고, 사용자가 더블 클릭으로 바로 실행할 수 있는 `run.bat` 스크립트를 제공합니다.
3. 기능 단위별로 명확한 Conventional Commits를 실행합니다:
   ```bash
   git add <modified-files>
   git commit -m "feat: implement <feature-description>"
   ```


### Stage 4: Quality & Regression Gate Verification (`@qa`)
1. 단위(Unit) 및 통합(Integration) 테스트 코드를 작성합니다.
2. 품질 하네스 엔진을 실행하여 5-Tier 검증을 통과시킵니다:
   ```bash
   python c:/temp/py/.antigravity/harness.py
   ```
3. 테스트 커밋을 수행합니다:
   ```bash
   git commit -m "test: add unit/integration tests for <feature>"
   ```

### Stage 5: Security & Code Audit (`@auditor`)
1. Git diff를 기반으로 OWASP Top 10 및 하드코딩된 시크릿/토큰을 엄격히 검사합니다.
2. 취약점이 없을 경우에만 보안 Sign-off를 부여합니다. (취약점 발견 시 Stage 3로 피드백)

### Stage 6: Infrastructure & PR (`@devops`)
1. Dockerfile, 패키징 설정 및 CI 파이프라인 무결성을 점검합니다.
2. 원격 저장소로 브랜치를 푸시합니다:
   ```bash
   git push origin feature/<task-name>
   ```
3. 변경 요약 및 테스트 결과가 포함된 Pull Request(PR) 본문을 생성합니다.

### Stage 7: Documentation & Multi-PC Context Sync (`@writer`)
1. README.md, API 명세, CHANGELOG.md를 최신화합니다.
2. **`PROJECT_CONTEXT.md` 동기화**: 세션 중 발생한 핵심 결정사항, 추가된 기능, 잔여 작업(Next Actions)을 기록합니다.
3. 최종 동기화 커밋을 수행합니다:
   ```bash
   git commit -m "docs: sync project context and changelog"
   ```
