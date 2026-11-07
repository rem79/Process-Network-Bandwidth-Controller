---
name: enterprise-pipeline
description: >-
  Executes the Antigravity 2.0 Adaptive & 7-Stage Enterprise Engineering Pipeline
  (Planning/PM, DBA, Developer, QA, Security Auditor, DevOps, Technical Writer)
  using native subagent tools (define_subagent, invoke_subagent), automated Git branching,
  5-Tier Quality Gate verification, and PROJECT_CONTEXT.md continuity sync.
  Activate this skill when starting a new feature, multi-file refactoring, or major bugfix.
---

# Enterprise Adaptive & 7-Stage Autonomous Pipeline (v2.0)

이 스킬은 사용자의 요구사항을 작업 규모에 따라 **Fast-Track** 또는 **7-Stage Enterprise Pipeline**으로 라우팅하여 설계, 구현, 검증, 감사, 배포 및 컨텍스트 동기화까지 자율 완수하는 표준 런북입니다.

---

## 1. Adaptive Routing Criteria (적응형 트랙 선정)

- **Track A (Consult / Read-Only)**: 단순 질문, 코드 분석, 아키텍처 리뷰 요청 시 $\rightarrow$ 파일 수정 금지, 텍스트 분석 후 대기.
- **Track B (Fast-Track)**: 단일 파일 수정, 경미한 버그 패치, UI 텍스트/레이아웃 미세 조정 $\rightarrow$ 승인 후 단일 에이전트가 직접 수정 $\rightarrow$ `python harness.py` 통과 $\rightarrow$ 커밋 & `PROJECT_CONTEXT.md` 갱신.
- **Track C (Full 7-Stage Pipeline)**: 신규 애플리케이션 생성, 복합 기능 개발, DB 스키마 변경, 다중 모듈 리팩터링 $\rightarrow$ 아래 7단계를 순차 실행.

---

## 2. Full 7-Stage Execution Workflow

각 단계의 상세 서브에이전트 프롬프트 및 권한 정의는 [references/subagent-roles.md](./references/subagent-roles.md)를 참조하십시오.
단일 에이전트 컨텍스트로 연속 처리가 가능한 경우 인라인으로 수행하고, 대규모 코드베이스 조사나 독립 코드 감사가 필요한 경우 `invoke_subagent` (`research` 또는 `define_subagent`로 정의한 커스텀 에이전트)를 호출합니다.

### Stage 1: Planning, Context & Branching (`pm`)
1. 프로젝트 루트의 `PROJECT_CONTEXT.md` 존재 여부를 확인합니다. (미존재 시 템플릿 기반으로 즉시 생성)
2. 요구사항을 작업 단위(Tasks)와 수용 기준(Acceptance Criteria)으로 분해합니다.
3. Git 저장소가 초기화된 경우 작업 브랜치를 생성합니다:
   ```powershell
   git checkout -b feature/<task-name>
   # 버그 수정 시: git checkout -b fix/<task-name>
   ```

### Stage 2: Data & Schema Design (`dba`)
1. 영속 데이터(SQLite, PostgreSQL, JSON/Config 스토어 등) 변경이 필요한 경우 스키마 및 마이그레이션 스크립트를 설계합니다.
2. 인덱스, 트랜잭션 무결성 및 쿼리 격리 전략을 수립합니다.

### Stage 3: Core Implementation & Smart Launcher (`developer`)
1. 비즈니스 로직 및 모듈을 구현합니다.
2. 데스크톱 UI 프로젝트인 경우 [windows-gui-launcher](../windows-gui-launcher/SKILL.md) 스킬 규격에 맞춰 `CustomTkinter` / `Tkinter` 기반 GUI와 무콘솔 `run.bat`(`pythonw.exe` + `2> crash_log.txt` + `--debug`)을 구성합니다.
3. 기능 단위별로 Conventional Commits를 수행합니다:
   ```powershell
   git add <modified-files>
   git commit -m "feat: implement <feature-description>"
   ```

### Stage 4: Quality & Regression Gate Verification (`qa`)
1. 단위(Unit) 및 통합(Integration) 테스트를 작성합니다.
2. 프로젝트 루트에서 5-Tier 품질 하네스를 실행합니다 ([quality-harness](../quality-harness/SKILL.md) 참조):
   ```powershell
   python harness.py
   ```
3. `"status": "PASSED"` 획득 후 테스트 커밋을 수행합니다.

### Stage 5: Security & EDR Audit (`auditor`)
1. `git diff` 및 전체 변경 파일을 대상으로 OWASP Top 10, 하드코딩된 시크릿, EDR 오탐 유발 패턴(`-EncodedCommand`, 메모리 인젝션 등)을 감사(Read-Only)합니다.
2. 독립적인 감사가 필요할 경우 `invoke_subagent`로 읽기 전용 `research` 서브에이전트를 호출하여 교차 검증합니다.

### Stage 6: Infrastructure, Versioning & PR (`devops`)
1. 시맨틱 버전(`vMAJOR.MINOR.PATCH`) 태그 및 원격 브랜치 푸시를 준비합니다:
   ```powershell
   git push origin <branch-name>
   ```
2. PR 본문 및 릴리스 요약을 작성합니다.

### Stage 7: Documentation & Multi-PC Context Sync (`writer`)
1. `README.md`, `CHANGELOG.md`를 최신화합니다.
2. **`PROJECT_CONTEXT.md` 실시간 현행화**: 이번 세션의 아키텍처 결정 사항, 하네스 검증 결과(`harness_status: PASSED`), 잔여 과제(Next Actions)를 기록합니다.
3. 최종 문서 동기화 커밋을 수행합니다:
   ```powershell
   git commit -m "docs: sync project context and changelog"
   ```
