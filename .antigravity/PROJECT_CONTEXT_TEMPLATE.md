# Project Context & Continuity Specification

> 본 문서는 다중 환경(사무실/재택/노트북) 및 세션 간 AI 어시스턴트와의 완벽한 연속성을 유지하기 위한 실시간 동기화 문서입니다.
> Antigravity 에이전트는 세션 시작 시 이 문서를 최우선으로 읽고, 세션 종료 시 최신 상태로 업데이트합니다.

---

## 1. Project Overview & Architecture
- **프로젝트명**: [Project Name]
- **비즈니스 도메인**: [도메인 요약 및 목적]
- **주요 기술 스택**: 
  - Language: [e.g. Python 3.11 / TypeScript 5.0]
  - Framework: [e.g. FastAPI / React / Spring Boot]
  - Database: [e.g. PostgreSQL / SQLite]
  - Tooling: [e.g. Docker, pytest, ruff]

---

## 2. Architecture & Directory Conventions
- **핵심 디렉토리 구조**:
  - `src/` : 핵심 비즈니스 로직
  - `tests/` : 단위 및 통합 테스트 스위트
- **설계 원칙**: [e.g. 계층형 아키텍처, 도메인 주도 설계 등]

---

## 3. Environment & Validation Commands (Harness Binding)
- **Tier 0 (Lint/Type)**: `python -m py_compile ...`
- **Tier 1 (Build)**: `...`
- **Tier 2 (Test)**: `pytest`
- **Tier 3 (Smoke)**: `python -c "import src"`
- **Tier 4 (Audit)**: `...`

---

## 4. Current Status & Active Tasks
- **현재 작업 브랜치**: `main`
- **최근 진행 상태**: [완료된 작업 요약]
- **현재 해결 중인 과제**: [진행 중인 이슈]

---

## 5. Next Actions (우선순위 대기열)
1. [ ] [다음 진행할 작업 1]
2. [ ] [다음 진행할 작업 2]

---

## 6. Session Decision History & Changelog
- **[YYYY-MM-DD HH:MM]**:
  - **작업자 / 에이전트**: 
  - **핵심 결정 사항**:
  - **테스트 및 하네스 검증 결과**: `harness_status: PASSED`
