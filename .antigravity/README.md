# Antigravity Enterprise Quality Harness & Master Pipeline

> **Google Antigravity 기반 자율 엔터프라이즈 개발 파이프라인, 5-Tier 품질 하네스(Quality Gate), EDR 안전 규약 및 Multi-PC 동기화 마스터 템플릿**

---

## 📌 개요 (Overview)

본 저장소는 로컬의 모든 Python 및 데스크톱 애플리케이션 프로젝트(`C:\temp\py\*`)에 표준 엔터프라이즈 개발 규격과 품질 검증 체계를 제공하는 **마스터 룰 및 하네스 엔진 저장소**입니다.

새로운 기능을 개발하거나 버그를 수정할 때 인공지능 에이전트(Antigravity)가 엄격한 품질 게이트를 준수하며, Windows 환경 및 사내 보안 솔루션(EDR)에 완벽히 호환되도록 구성되어 있습니다.

---

## 🚀 핵심 기능 및 규약 (Key Features)

### 1. 7단계 자율 개발 파이프라인 (`Enterprise 7-Stage Pipeline`)
- `@pm`: 요구사항 분석, `PROJECT_CONTEXT.md` 점검, 작업 브랜치 생성, 인터페이스 설계
- `@dba`: 데이터 모델링 및 마이그레이션 DDL 관리
- `@developer`: 비즈니스 로직 구현 및 단위별 Conventional Commits (`feat:`, `fix:`)
- `@qa`: 단위/통합 테스트 작성 및 5-Tier 품질 게이트 검증 통과 (`harness_status: PASSED`)
- `@auditor`: OWASP Top 10 및 시크릿/토큰 유출 정적 감사
- `@devops`: 인프라 무결성 검증, GitHub Push 및 PR 템플릿 생성
- `@writer`: API 명세, README, CHANGELOG 및 `PROJECT_CONTEXT.md` 최종 현행화

### 2. 5-Tier Universal Quality Gate (`harness.py`)
언어 및 런타임을 자동 감지하여 5단계 품질 검증을 수행합니다:
- **Tier 0 (Syntax & Static)**: 인터프리터 문법 파싱 및 린트(`py_compile`)
- **Tier 1 (Build & Packaging)**: 개발 단계에서는 기본 생략, 릴리스 시에만 검증
- **Tier 2 (Regression & Unit Test)**: 단위 및 회귀 테스트 100% 통과 보장
- **Tier 3 (Runtime Smoke & Healthcheck)**: 프로세스 콜드스타트 무결성 검증
- **Tier 4 (Secret & Security Audit)**: 하드코딩된 API 키/토큰 및 EDR 트리거 고위험 패턴 정적 감사

### 3. 🛡️ 엔터프라이즈 EDR 안전 규약 (EDR-Safe Coding)
- CrowdStrike, SentinelOne, Defender for Endpoint 등 사내 보안 솔루션의 오탐/차단 방지
- PowerShell `-EncodedCommand`, base64 인라인 실행(`iex`, `eval`), 원격 파이프 실행(`curl | sh`) 금지
- Win32 메모리 인젝션 API(`VirtualAllocEx`, `WriteProcessMemory`) 및 레지스트리 자동실행 키 무단 조작 차단

### 4. 🖥️ 네이티브 데스크톱 GUI 우선 & 무콘솔 스마트 런처
- 불필요한 웹 서버(FastAPI, Flask, Streamlit) 지양, **`CustomTkinter` / `Tkinter` 기반 Windows 네이티브 앱 우선 개발**
- `run.bat`: `pythonw.exe` + `start`를 적용하여 **더블 클릭 시 검은 콘솔 창 없이 순수 GUI만 기동**
- 사일런트 크래시 방지(`2> crash_log.txt`) 및 디버그 모드(`run.bat --debug`) 완비

### 5. 🔄 원클릭 전체 프로젝트 동기화 (`update_rules.bat`)
- 상위 디렉터리(`C:\temp\py\`)에 존재하는 수십 개의 프로젝트에 본 마스터 룰, 하네스 엔진, 최신 스킬을 **더블 클릭 한 번으로 일괄 배포 및 갱신**합니다.

---

## 📂 디렉터리 구조

```text
.antigravity/
├── GEMINI.md                    # Antigravity가 자동으로 로드하는 최상위 마스터 룰
├── rules.md                     # GitHub 워크플로우 및 파이프라인 세부 규칙
├── harness.py                   # 5-Tier 품질 게이트 자동 검증 엔진
├── harness.json                 # 게이트별 사용자 정의 커맨드 설정
├── PROJECT_CONTEXT_TEMPLATE.md  # Multi-PC 연속성 보장을 위한 컨텍스트 표준 템플릿
├── update_rules.bat             # 전체 프로젝트 룰 일괄 동기화 원클릭 배치 파일
├── update-all-projects.ps1      # 프로젝트 일괄 동기화 및 구버전 정리 스크립트
├── sync-template.ps1            # 개별 프로젝트 심볼릭 링크 동기화 스크립트
├── skills/                      # Antigravity 네이티브 스킬
│   ├── enterprise-pipeline/     # 7단계 자율 파이프라인 스킬 (SKILL.md)
│   └── quality-harness/         # 5-Tier 하네스 및 자가 치유 스킬 (SKILL.md)
└── agents/                      # 파이프라인 역할별 서브에이전트 정의
    ├── pm.md, dba.md, developer.md, qa.md, auditor.md, devops.md, writer.md
```

---

## 🏷️ 버전 관리 및 롤백 (Versioning & Safe Rollback)

- 본 프로젝트는 **Semantic Versioning (`vMAJOR.MINOR.PATCH`)** 규격을 준수합니다.
- Git의 원자적 커밋과 태그(`v1.0.0` 등)를 통해 언제든지 원하는 과거 시점이나 특정 버전으로 안전하게 원복(`git revert` 또는 `checkout`)할 수 있습니다.
