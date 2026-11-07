# Antigravity Enterprise Autonomous Development & Quality Harness Rules

본 프로젝트는 Antigravity 기반의 자율 엔터프라이즈 개발 파이프라인 및 5-Tier Quality Gate 규격을 준수합니다.
에이전트는 사용자의 작업 요청 시 아래 규정을 엄격하게 따릅니다.

## 0. 🛑 Strict Confirmation & Autonomous Completion Protocol (승인 및 자율 완수 규약)

- **단순 질문, 검토, 확인 시 코드 수정 금지**:
  - 사용자가 질문, 상태 확인, 코드 리뷰, 설계 조언을 구하는 경우 **절대로 소스 코드나 설정 파일을 직접 수정하지 않습니다.**
  - 현상 분석, 문제 원인, 권장 해결 방향을 텍스트로 친절하고 상세하게 설명하고 사용자의 판단을 기다립니다.
- **명시적 승인 후 작업 착수**:
  - 파일 수정이 필요한 경우에도 변경 대상 파일과 작업 계획(Plan)을 먼저 요약 제시합니다.
  - 사용자가 **"진행해", "적용해줘", "수정해", "1번으로 해줘"** 등 명시적으로 동의/승인하기 전까지는 어떠한 파일 생성, 수정, 삭제, 빌드 명령도 임의로 실행하지 않습니다.
- **승인 후 질문 최소화 및 자율 완수 (Seamless Autonomous Completion)**:
  - 사용자가 작업 착수를 승인한 이후에는, 사소한 단계나 파일 단위마다 멈춰서 되묻는 행위를 엄격히 지양합니다.
  - 구현, 린트, 테스트 검증, 컨텍스트 동기화까지 **스스로 책임지고 연속적으로 완수**한 뒤 최종 완료 결과를 사용자에게 보고합니다.
  - 단, 기존 데이터 영구 삭제(Drop, Purge) 등 비가역적 파괴 행위가 수반되는 경우에 한해서만 사전에 추가 확인을 받습니다.

---

## 0-1. 🔒 Project Boundary Isolation Protocol (작업 디렉터리 엄격 격리 규약)

- **상위 및 타 프로젝트 폴더 침범 절대 금지**:
  - 에이전트는 현재 작업 중인 프로젝트 루트(CWD)를 벗어나 **상위 부모 폴더, 다른 프로젝트 폴더, 사용자 홈 디렉터리 및 OS 시스템 경로(`C:\`, `%USERPROFILE%` 등)를 절대로 수정/생성/삭제할 수 없습니다.**
  - 모든 코드 수정, 신규 파일 생성, 임시 데이터, 테스트 로그는 오직 **현재 프로젝트 폴더 내부**로만 엄격히 격리(Sandbox)됩니다.
  - 마스터 룰 배포 스크립트(`update_rules.bat`)와 같이 사용자가 명시적으로 전체 동기화를 지시한 특수 작업을 제외하고는 어떠한 외부 경로 침범도 허용되지 않습니다.

---


## 1. Multi-PC Context Continuity (`PROJECT_CONTEXT.md`)


- **작업 착수 전 확인**: 프로젝트 루트에 `PROJECT_CONTEXT.md`가 존재하는지 확인하고, 없을 경우 표준 템플릿(`PROJECT_CONTEXT_TEMPLATE.md` 기반)으로 즉시 자동 생성합니다.
- **다중 환경(집/회사/노트북) 연속성 보장**: 이전 세션의 설계 결정 사항, 진행 상태, 잔여 과제(Next Actions)를 최우선으로 로드하여 이어받습니다.
- **작업 완료 후 실시간 현행화**: 작업 세션이 끝날 때마다 주요 변경점, 아키텍처 결정, 테스트 결과 및 Next Actions를 `PROJECT_CONTEXT.md`에 동기화합니다.

---

## 2. Enterprise 7-Stage Pipeline

새로운 작업이나 기능 개발 착수 시 다음 7단계를 순차적으로 수행합니다:

1. **[Step 1] Planning & Branching (`@pm`)**: 요구사항 분석, `PROJECT_CONTEXT.md` 점검/생성, 작업 브랜치(`feature/<task>` 또는 `fix/<task>`) 생성, 인터페이스/모듈 스펙 설계.
2. **[Step 2] Data & Schema Design (`@dba`)**: 필요 시 DB 스키마/마이그레이션 DDL 작성, ERD 모델링 및 쿼리 격리 가이드 수립.
3. **[Step 3] Core Implementation (`@developer`)**: 설계에 기반한 비즈니스 로직 작성 및 기능 단위별 Conventional Commits (`feat:`, `fix:`, `refactor:`).
4. **[Step 4] Quality & Regression Gate (`@qa`)**: 단위/통합 테스트 작성, 5-Tier Quality Gate 검증 실행 및 통과(`harness_status: PASSED`).
5. **[Step 5] Security & Code Audit (`@auditor`)**: OWASP Top 10 점검, 시크릿/토큰 하드코딩 검사, 정적 분석 보안 승인 (Read-Only).
6. **[Step 6] Infrastructure & PR (`@devops`)**: CI/CD 및 빌드 설정 점검, `git push origin <branch>`, PR 본문 자동 생성.
7. **[Step 7] Context Sync & Documentation (`@writer`)**: README, API 명세, CHANGELOG 및 `PROJECT_CONTEXT.md` 최종 현행화 커밋.

---

## 3. Strict 5-Tier Quality Gate Protocol

에이전트는 코드 작성 후 반드시 검증을 거쳐야 하며, 게이트 통과 없이 메인 브랜치 머지나 푸시를 진행하지 않습니다:

- **Tier 0 (Syntax & Static)**: 파싱 에러, 린트(Linter), 타입체크(`tsc`, `mypy`, `py_compile` 등) 무결성
- **Tier 1 (Build & Packaging)**: 개발 단계에서는 기본 생략(선택). 패키징 충돌 여부는 최종 릴리스/배포 시에만 검증
- **Tier 2 (Regression & Unit Test)**: 기존 및 신규 테스트 100% 통과
- **Tier 3 (Runtime Smoke & Healthcheck)**: 프로세스 콜드스타트 / 헬스체크 검증
- **Tier 4 (Secret & CVE Audit)**: API 키/시크릿 유출 및 보안 취약점 점검

### 자가 치유(Self-Healing) 및 롤백 원칙
- 게이트 실패 시 원인 진단 후 최대 3회까지 자율 수정을 시도합니다.
- 3회 연속 실패 시 무손실 원자적 롤백(작업 전 체크포인트 복원)을 수행하고 상세 원인을 사용자에게 보고합니다.

---

## 4. 🛡️ Enterprise EDR-Safe Coding & Execution Protocol (EDR 안전 규약)

엔터프라이즈 보안 솔루션 및 EDR(CrowdStrike, SentinelOne, Defender for Endpoint 등)의 오탐 및 프로세스 차단을 방지하기 위해 다음 패턴을 엄격히 회피합니다:

1. **의심스러운 쉘 실행 및 난독화 금지**:
   - `powershell.exe -EncodedCommand`, base64 디코딩 후 즉시 실행(`iex`, `eval`), 원격 스크립트 파이프 실행(`curl | sh`, `irm | iex`) 금지.
   - 표준 인자 전달 및 명시적인 파일 기반 스크립트 실행 방식을 채택합니다.
2. **타 프로세스 침범 및 메모리 조작 금지**:
   - `ctypes`, Win32 API(`VirtualAllocEx`, `WriteProcessMemory`, `CreateRemoteThread`) 등을 통한 프로세스 인젝션/조작 코드 작성 금지.
   - 시스템 레지스트리 자동 실행 키(`Run`, `RunOnce`) 무단 수정 및 서비스/드라이버 등록 금지.
3. **임시 폴더 내 비표준 실행 파일 동적 생성 및 실행 회피**:
   - `%TEMP%`, `AppData\Local\Temp\` 등에 `.exe`, `.bat`, `.ps1`, `.vbs` 등을 동적으로 떨구고 즉시 실행하는 패턴 금지 (프로젝트 작업 디렉터리 내 명시적 경로 사용).
4. **네트워크/포트 무차별 스캐닝 및 과도한 프로세스 열거 완화**:
   - 서브넷 전체 포트 스캔(`nmap`, 멀티스레드 소켓 폭격) 금지. 연결 검사는 타깃 주소와 타임아웃을 명시하여 수행.
   - 로컬 프로세스 전체 목록의 짧은 주기 무한 루프 폴링 금지.
5. **시스템 자격 증명(Credential) 접근 패턴 절대 금지**:
   - SAM, LSASS 메모리 덤프 시도 또는 브라우저/OS 자격 증명 저장소 무단 접근 코드 금지.

---

## 5. ⚡ Minimal Build & Batch-First Execution Protocol (빌드 최소화 및 실행기 규약)

- **개발 중 빌드(컴파일/패키징) 최소화**:
  - 개발 및 테스트 도중 PyInstaller, Nuitka, Webpack 번들링 등의 무거운 빌드 과정을 매번 반복하지 않습니다.
  - 소스 코드 수정 후 즉시 실행하여 빠른 피드백 루프를 확보합니다.
- **배치 파일(`run.bat` / `start.bat`) 기반 실행 환경 표준화**:
  - 프로젝트 루트에 원클릭 실행용 배치 파일(`run.bat`)을 제공하여 사용자가 최종 바이너리(`.exe`)를 실행하듯 더블 클릭으로 바로 구동할 수 있도록 구성합니다.
  - 가상환경(venv) 자동 감지 및 인자 전달(`%*`)을 포함하여 일반 exe와 동일한 사용자 경험을 제공합니다.
  - **🖥️ GUI 프로그램 무콘솔(No-Console) & 스마트 에러 가드**:
    - GUI 애플리케이션(Tkinter, PyQt, CustomTkinter, WebUI 등)의 경우 `python.exe` 대신 `pythonw.exe`와 `start` 명령어를 사용하여, **실행 시 검은 CMD 콘솔 창이 남지 않고 즉시 닫히도록 구성**합니다.
    - `pythonw.exe` 특유의 사일런트 크래시(에러 시 조용히 꺼짐)를 방지하기 위해 `2> crash_log.txt` 리다이렉션을 기본 적용하고, `--debug` 또는 `-d` 인자 전달 시 콘솔 창과 함께 로그를 실시간 출력하는 디버그 모드를 지원합니다.
- **🛡️ 윈도우 스크립트(`.bat` / `.ps1` / CLI) 콘솔 출력 및 인코딩 무결성 규약**:
  - `cmd.exe` 및 PowerShell 콘솔에서 한글 멀티바이트 문자열(UTF-8)과 OS 기본 코드페이지(CP949) 간의 충돌로 인한 **글자 깨짐(Mojibake), 문법 파싱 오류, 명령어 오인식을 원천 방지**합니다.
  - 배치 파일(`.bat`, `.cmd`) 및 CLI 자동화 스크립트(`.ps1`, `.py`)의 **콘솔 출력 로그, 진행 상태 메시지, 에러 메시지, 프롬프트는 원칙적으로 깔끔한 영문(ASCII) 위주로 작성**합니다.
  - 파일 본문이나 문서(`*.md`, `*.json`) 등 정적 데이터에는 한글을 자유롭게 사용하되, **터미널/콘솔에 실시간 출력되는 로그 메시지는 항상 영문 표준을 유지**하여 모든 Windows 환경에서 가독성과 안정성을 100% 보장합니다.
- **바이너리(`.exe`) 빌드는 최종 릴리스/배포 시점으로 한정**:
  - 다른 사람에게 배포하거나 최종 릴리스 태그 생성 시에만 `@devops` 단계 또는 사용자의 명시적 요청 하에 빌드 스크립트(`build.bat`)를 통해 `.exe`를 패키징합니다.

---

## 6. 🖥️ Native Desktop GUI First Protocol (네이티브 데스크톱 앱 우선 규약)

- **웹 애플리케이션(Web UI) 기본 채택 금지**:
  - 사용자가 명시적으로 "웹으로 만들어줘", "FastAPI/Flask/HTML로 해줘"라고 지정하지 않는 한, **로컬 웹 서버, 브라우저 기반 Web UI(Streamlit, Gradio, Flask, FastAPI, React 등)를 기본 아키텍처로 제안하거나 구현하지 않습니다.**
- **Windows 네이티브 데스크톱 GUI 우선 개발**:
  - 사용자 인터페이스(UI)가 필요한 모든 애플리케이션은 **`CustomTkinter`** 또는 **`Tkinter`** (필요 시 PyQt/PySide) 기반의 독립 실행형 Windows 데스크톱 GUI로 개발합니다.
  - 별도의 브라우저 창 기동이나 포트 충돌 없이, 단일 윈도우 창과 `run.bat` / `.exe`로 깔끔하게 완결되는 데스크톱 앱 구조를 기본으로 합니다.

---

## 7. 🏷️ GitHub Documentation, Semantic Versioning & Rollback Protocol (버전/설명 및 롤백 규약)

- **GitHub 업로드 시 상세 설명(README) 및 릴리스 노트 필수화**:
  - **`README.md` 완비**: 프로젝트의 목적, 핵심 기능, 조작 방법, 원클릭 실행(`run.bat`) 가이드를 일반 사용자도 쉽게 이해할 수 있는 한글로 친절히 작성합니다.
  - **PR 및 Release 본문 자동 요약**: 이번 버전에서 변경/추가된 기능을 체계적으로 서술합니다.
- **시맨틱 버전 관리 (`vMAJOR.MINOR.PATCH`) & `CHANGELOG.md`**:
  - 기능 추가 및 구조 변경 시 `v1.1.0`, 버그 수정 시 `v1.1.1` 등 명확한 시맨틱 버전 태그(`git tag -a vX.Y.Z -m "..."`)를 발행합니다.
  - `CHANGELOG.md`에 날짜별, 버전별 변경 내역(`[Added]`, `[Changed]`, `[Fixed]`)을 누적 관리합니다.
- **언제든지 과거 시점 롤백 보장 (Safe Historic Rollback)**:
  - 사용자가 과거 특정 시점 또는 버전(`v1.0.0` 등)으로 되돌리기를 원할 경우, Git의 이력을 파괴하지 않고 안전하게 해당 시점 상태로 원복(`git revert` 또는 특정 커밋/태그 체크아웃)할 수 있도록 전 과정을 지원합니다.
  - "오래된 과거 버전"이나 "특정 파일의 과거 상태"도 언제든지 즉시 안전 복구할 수 있도록 커밋 단위 무결성을 유지합니다.







