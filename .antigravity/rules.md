# Global Project & Autonomous GitHub Workflow Rules

## 1. Interaction Modes & Explicit Confirmation Protocol
- **상담/질문/검토 모드**: 사용자가 질문, 확인, 코드 검토를 요청하는 경우 파일을 수정하지 않고 텍스트로 분석과 대안을 제시합니다.
- **개발 작업 착수 및 자율 완수**: 사용자가 작업 계획에 대해 "진행해", "적용해줘" 등 명시적으로 승인한 경우, **사소한 단계마다 중간 질문을 반복하지 않고 계획된 파이프라인(구현, 테스트, 동기화)을 끝까지 자율 완수**합니다.
  > **[Default Execution Pipeline with GitHub & Multi-PC Context Sync]**
  > 1. `@pm`: 이슈/요구사항 분석, **`PROJECT_CONTEXT.md` 자동 생성/점검**, `feature/<task-name>` (또는 `fix/<task-name>`) Git 브랜치 생성
  > 2. `@dba`: 스키마/마이그레이션 DDL 작성 및 버전 관리
  > 3. `@developer`: 비즈니스 로직 구현 및 단계별 Conventional Commit (`feat:`, `fix:`, `refactor:`)
  > 4. `@qa`: 단위/통합 테스트 스위트 작성 및 검증 통과
  > 5. `@auditor`: 보안 취약점(OWASP) 및 코드 품질 심층 감사 (Read-Only)
  > 6. `@devops`: 빌드/CI 환경 점검, 원격 브랜치 `git push origin` 및 Pull Request(PR) 템플릿 생성
  > 7. `@writer`: API 명세서, README.md, CHANGELOG.md 및 **`PROJECT_CONTEXT.md`(작업 맥락/진행 상태/Next Actions) 최신화 동기화 커밋**

- **작업 디렉터리 엄격 격리 (Boundary Isolation)**:
  - 현재 프로젝트 폴더 외부(상위 부모 폴더, 다른 프로젝트 폴더, OS 시스템 디렉터리)에 대한 생성, 수정, 삭제를 엄격히 금지합니다. 모든 파일 I/O는 현재 프로젝트 루트 내부로만 제한됩니다.



## 2. 🧠 Multi-PC Seamless Continuity & PROJECT_CONTEXT.md Protocol
- **신규 프로젝트 자동 생성:** 새 프로젝트 시작 시 `PROJECT_CONTEXT.md`가 없으면 `@pm`이 비즈니스 도메인, 아키텍처 구조, 핵심 기능, 개발 주의사항, 검증 명령어가 포함된 표준 템플릿으로 자동 생성합니다.
- **다중 환경(집/회사/노트북) 연속성 보장:** 집(Home)과 회사(Office) 등 어떤 PC에서든 `git pull` 후 AI 어시스턴트가 `PROJECT_CONTEXT.md`를 최우선으로 로드하여 이전 세션의 설계 결정, 채팅 맥락, 현재 진행 상태를 100% 온전히 이어받아 작업합니다.
- **세션 종료/완료 시 실시간 현행화:** 작업 단위 완료 시 `@writer`가 대화에서 결정된 주요 아키텍처 변경, 추가된 기능, 잔여 과제(Next Actions)를 `PROJECT_CONTEXT.md`의 히스토리 섹션에 빠짐없이 동기화합니다.

## 3. GitHub & Quality Gate Constraints
- **Branch Protection:** 메인 브랜치(`main` 또는 `master`)에 직접 커밋하지 않으며, 항상 `@pm`이 생성한 작업 브랜치에서 진행합니다.
- **Commit Convention:** 모든 커밋은 Conventional Commits 표준(`feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`)을 준수합니다.
- **Strict Quality Gate & Harness Enforcement:** `@developer`와 `@qa`는 반드시 `.antigravity/harness.md`에 규정된 5-Tier Quality Gate(Tier 0~4)를 통과하여 `harness_status: PASSED`를 획득해야 하며, `@auditor`의 보안 승인(High/Critical 취약점 없음)이 완료되어야만 `@devops` 단계에서 원격 push 및 PR 생성이 승인됩니다.
- **Zero Manual Overhead:** 브랜치 분기부터 커밋, 푸시, PR 설명 작성 및 컨텍스트 문서 동기화까지 전 과정을 에이전트가 백그라운드에서 자율 완수합니다.

## 4. 🛡️ Universal Execution & Quality Harness Protocol
- **사전 체크포인트 의무화:** 에이전트가 코드를 수정하기 전, 하네스는 작업 전 원본 상태의 체크포인트(Git 커밋/스냅샷)를 강제 생성하여 100% 무손실 롤백 환경을 보장합니다.
- **5-Tier Quality Gate 준수:**
  - `Tier 0`: 구문/정적 분석 (Linter, TypeCheck, Compiler)
  - `Tier 1`: 빌드 및 컴파일 무결성 (Build/Packaging)
  - `Tier 2`: 회귀 및 단위 테스트 무결성 (Regression & Unit Tests)
  - `Tier 3`: 런타임 스모크 및 헬스체크 (Smoke & Cold-Start)
  - `Tier 4`: 시크릿 및 취약점 감사 (Secrets & CVE Audit)
- **자가 치유(Self-Healing) 및 자동 롤백:** 게이트 실패 시 하네스의 표준 JSON 진단 리포트를 바탕으로 최대 3회까지 자가 교정을 시도하며, 최종 실패 시 환경 오염 방지를 위해 즉각 이전 체크포인트로 원자적 롤백을 수행합니다.

## 5. 🛡️ Enterprise EDR-Safe Coding & Execution Protocol (EDR 안전 규약)
- **의심스러운 쉘 실행 및 난독화 금지:**
  - `powershell.exe -EncodedCommand`, base64 디코딩 후 인라인 실행(`iex`, `eval`), 웹 직접 파이프 실행(`curl | sh`, `irm | iex`) 금지.
  - 명시적이고 읽을 수 있는 표준 스크립트 파일 및 인자 사용.
- **타 프로세스 메모리 침범 및 조작 금지:**
  - Win32 API / `ctypes`를 통한 프로세스 인젝션(`VirtualAllocEx`, `WriteProcessMemory`, `CreateRemoteThread`) 금지.
  - 레지스트리 자동 실행(`Run`, `RunOnce`) 무단 수정 및 서비스/드라이버 생성 금지.
- **임시 경로 내 실행 파일 동적 생성 및 실행 회피:**
  - `%TEMP%`, `AppData\Local\Temp\` 등에 `.exe`, `.bat`, `.ps1`, `.vbs` 등을 생성 후 즉시 실행하는 패턴 배제 (프로젝트 내부 명시적 경로 사용).
- **네트워크 무차별 스캔 및 과도한 프로세스 열거 완화:**
  - 대규모 서브넷 포트 스캔(`nmap`, 멀티스레드 포트 폭격) 금지 및 타깃/타임아웃 명시.
  - 짧은 주기의 프로세스 목록 무한 폴링 지양.
- **자격 증명(Credential) 접근 패턴 금지:**
  - SAM, LSASS 메모리 덤프 또는 브라우저/OS 자격 증명 저장소 무단 접근 코드 금지.

## 6. ⚡ Minimal Build & Batch-First Execution Protocol (빌드 최소화 및 실행기 규약)
- **개발 중 빌드(패키징/컴파일) 최소화:**
  - 개발 진행 중 PyInstaller, Nuitka 등을 통한 무거운 바이너리 빌드를 반복하지 않고, 소스 코드 직접 실행 방식으로 빠른 피드백을 유지합니다.
- **배치 파일(`run.bat`) 기반 원클릭 실행 체계:**
  - 사용자가 마치 완성된 `.exe`를 다루듯 더블 클릭이나 터미널에서 즉시 실행할 수 있는 `run.bat` 스크립트를 기본 제공합니다.
  - **GUI 프로젝트 무콘솔(No-Console) 표준**: GUI 앱은 `pythonw.exe`와 `start`를 적용하여 콘솔 창을 즉시 닫고, 에러 추적을 위한 `crash_log.txt` 리다이렉션 및 `--debug` 모드를 지원합니다.
- **윈도우 스크립트(`.bat` / `.ps1` / CLI) 콘솔 출력 및 인코딩 무결성:**
  - `cmd.exe` 및 PowerShell에서 UTF-8 한글 문자열과 시스템 코드페이지(CP949) 간 충돌로 인한 글자 깨짐(Mojibake) 및 구문 오류를 원천 차단하기 위해, **콘솔 출력 로그, 진행 상태, 프롬프트는 영문(ASCII) 위주로 작성**합니다.
  - 파일 콘텐츠(`*.md`, `*.json`)에는 한글을 자유롭게 사용하되, 터미널 출력은 영문 표준을 유지합니다.
- **바이너리(`.exe`) 빌드는 외부 배포 시점으로 한정:**
  - 타인 배포, 릴리스 패키징 요청 시에만 `build.bat` 등을 통해 독립 실행 파일(`.exe`)을 생성합니다.

## 7. 🖥️ Native Desktop GUI First Protocol (네이티브 데스크톱 앱 우선 규약)
- **웹 애플리케이션(Web UI) 기본 채택 금지:**
  - 사용자가 명시적으로 웹 개발을 요구하지 않는 한, 로컬 웹 서버(FastAPI, Flask, Streamlit 등)를 기본 아키텍처로 삼지 않습니다.
- **Windows 네이티브 데스크톱 GUI 기본 채택:**
  - UI 프로그램은 `CustomTkinter` 또는 `Tkinter` 기반의 단독 윈도우 데스크톱 애플리케이션으로 개발합니다.








## 8. 🏷️ GitHub Documentation, Semantic Versioning & Rollback Protocol (버전/설명 및 롤백 규약)
- **상세 설명(README.md) 및 릴리스 노트:**
  - 앱의 기능과 사용법(run.bat), UI 가이드가 포함된 명확한 README.md를 항상 동기화하고 배포 시 변경 사항을 요약합니다.
- **시맨틱 버전 관리(vX.Y.Z) & 태깅:**
  - 기능 추가 및 패치 단위로 Git 태그를 발행하고 CHANGELOG.md에 변경 이력을 누적합니다.
- **과거 시점 무손실 롤백 지원:**
  - 오래된 과거 버전이나 특정 커밋 시점으로 언제든지 안전하게 롤백(Revert/Checkout)할 수 있도록 이력 보존 원칙을 준수합니다.