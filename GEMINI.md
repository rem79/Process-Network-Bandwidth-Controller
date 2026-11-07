# Antigravity Enterprise Autonomous Development & Quality Harness Rules (v2.0)

본 프로젝트는 **Google Antigravity 2.0 (Gemini 4 기반)** 자율 엔터프라이즈 개발 파이프라인, `.agents/` 네이티브 커스터마이징 아키텍처, 및 5-Tier Quality Gate 규격을 준수합니다.
에이전트는 사용자의 모든 작업 요청 시 아래 규정을 예외 없이 준수합니다.

---

## 0. 🛑 Strict Confirmation & Autonomous Completion Protocol (승인 및 자율 완수 규약)

- **단순 질문, 검토, 확인 시 파일 수정 절대 금지 (Consult Mode)**:
  - 사용자가 질문, 상태 확인, 코드 리뷰, 아키텍처/설계 조언을 구하는 경우 **절대로 소스 코드나 설정 파일을 직접 수정하거나 빌드/삭제 명령을 실행하지 않습니다.**
  - 현상 분석, 문제 원인, 권장 해결 방향을 텍스트로 친절하고 상세하게 설명하고 사용자의 판단을 기다립니다.
- **명시적 승인 후 작업 착수 (Plan & Confirm First)**:
  - 파일 수정이나 신규 생성이 필요한 경우, 변경 대상 파일 목록과 작업 계획(Action Plan)을 먼저 요약 제시합니다. (대규모 작업 시 Antigravity 네이티브 `implementation_plan.md` 아티팩트 활용)
  - 사용자가 **"진행해", "적용해줘", "수정해", "1번으로 해줘"** 등 명시적으로 동의/승인하기 전까지는 어떠한 파일 생성, 수정, 삭제, 빌드 명령도 임의로 실행하지 않습니다.
- **승인 후 질문 최소화 및 자율 완수 (Seamless Autonomous Completion)**:
  - 사용자가 작업 착수를 승인한 이후에는 사소한 단계나 개별 파일 단위마다 멈춰서 되묻는 행위를 엄격히 금지합니다.
  - 코드 구현 $\rightarrow$ 5-Tier 품질 하네스 검증(`python harness.py`) $\rightarrow$ 자가 치유(최대 3회) $\rightarrow$ `PROJECT_CONTEXT.md` 동기화까지 **스스로 책임지고 연속적으로 완수**한 뒤 최종 결과만 보고합니다.
  - 단, 기존 데이터 영구 삭제(`DROP`, `TRUNCATE`, 대규모 원본 데이터 파기) 등 비가역적 파괴 행위가 수반되는 경우에 한해서만 사전에 추가 확인을 받습니다.

---

## 0-1. 🔒 Project Boundary Isolation Protocol (작업 디렉터리 엄격 격리 규약)

- **상위 및 타 프로젝트 폴더 침범 절대 금지**:
  - 에이전트는 현재 작업 중인 프로젝트 루트(CWD)를 벗어나 **상위 부모 폴더, 다른 프로젝트 폴더, 사용자 홈 디렉터리 및 OS 시스템 경로(`C:\`, `%USERPROFILE%` 등)를 절대로 수정/생성/삭제할 수 없습니다.**
  - 모든 코드 수정, 신규 파일 생성, 임시 데이터, 테스트 로그는 오직 **현재 프로젝트 폴더 내부**(및 Antigravity 공식 `<appDataDir>\brain\<conversation-id>` 아티팩트/스크래치 경로)로만 엄격히 격리(Sandbox)됩니다.
  - 예외: 마스터 룰 배포 스크립트(`update_rules.bat` / `update-all-projects.ps1`)와 같이 사용자가 명시적으로 전체 프로젝트 동기화를 지시한 특수 작업만 예외로 허용됩니다.

---

## 1. 🧠 Multi-PC Context Continuity (`PROJECT_CONTEXT.md`)

- **작업 착수 전 확인**: 프로젝트 루트에 `PROJECT_CONTEXT.md`가 존재하는지 확인하고, 없을 경우 `PROJECT_CONTEXT_TEMPLATE.md` 기반으로 즉시 자동 생성합니다.
- **다중 환경(집/회사/노트북) 연속성 보장**: 세션 시작 시 `PROJECT_CONTEXT.md`의 이전 설계 결정 사항, 진행 상태, 잔여 과제(Next Actions)를 최우선으로 로드하여 이어받습니다.
- **작업 완료 후 실시간 현행화**: 작업 세션이 끝날 때마다 주요 변경점, 아키텍처 결정, 하네스 검증 결과(`harness_status: PASSED`) 및 Next Actions를 `PROJECT_CONTEXT.md`에 동기화합니다.

---

## 2. ⚡ Adaptive Execution Pipeline & Native Subagents (적응형 파이프라인 규약)

작업의 규모와 위험도에 따라 아래 3가지 트랙 중 최적의 경로를 선택하여 실행합니다 (상세 런북: `.agents/skills/enterprise-pipeline/SKILL.md`):

1. **Track A — Consult / Read-Only (질문·코드 리뷰·원인 분석)**:
   - 파일 수정 없이 코드베이스를 탐색하고 명확한 분석 리포트와 해결 방안을 제시합니다.
2. **Track B — Fast-Track Execution (단일 파일 수정·경미한 버그 패치·UI 미세 조정)**:
   - 작업 계획 승인 $\rightarrow$ 단일 에이전트가 즉시 코드 수정 $\rightarrow$ `python harness.py` (Tier 0~4) 검증 통과 $\rightarrow$ 원자적 커밋(`fix:` / `feat:`) 및 `PROJECT_CONTEXT.md` 현행화.
3. **Track C — Enterprise 7-Stage Pipeline (신규 기능 개발·DB 스키마 변경·다중 모듈 리팩터링)**:
   - 승인 후 아래 7단계를 순차 수행하며, 병렬 탐색이나 독립 감사/검증이 유리할 경우 Antigravity 네이티브 서브에이전트 도구(`define_subagent`, `invoke_subagent`, `Workspace: "branch" | "share"`)를 적극 활용합니다:
     - **[Step 1] Planning & Branching (`pm`)**: 요구사항 분석, `PROJECT_CONTEXT.md` 점검, 작업 브랜치(`feature/<task>` 또는 `fix/<task>`) 생성, 인터페이스 설계.
     - **[Step 2] Data & Schema Design (`dba`)**: 필요 시 DB 스키마/마이그레이션 DDL 작성, 인덱스 및 쿼리 격리 설계.
     - **[Step 3] Core Implementation (`developer`)**: 비즈니스 로직 구현, 원클릭 `run.bat` 구성, 기능 단위별 Conventional Commits (`feat:`, `fix:`, `refactor:`).
     - **[Step 4] Quality & Regression Gate (`qa`)**: 단위/통합 테스트 작성 및 `python harness.py` 실행을 통한 5-Tier Quality Gate 통과(`status: PASSED`).
     - **[Step 5] Security & Code Audit (`auditor`)**: OWASP Top 10, 시크릿/토큰 하드코딩, EDR 위험 패턴 정적 감사 (Read-Only).
     - **[Step 6] Infrastructure & PR (`devops`)**: 빌드/CI 설정 점검, `git push origin <branch>`, PR 본문 자동 생성.
     - **[Step 7] Context Sync & Documentation (`writer`)**: `README.md`, `CHANGELOG.md` 및 `PROJECT_CONTEXT.md` 최종 현행화 커밋.

---

## 3. 🛡️ Strict 5-Tier Quality Gate & Self-Healing Protocol (`harness.py`)

코드 작성 또는 수정 후 반드시 `python harness.py` (상세 런북: `.agents/skills/quality-harness/SKILL.md`)를 실행하여 검증을 통과해야 합니다:

- **Tier 0 (Syntax & Static)**: 프로젝트 `venv` 기반 파싱 에러(`py_compile`), 린터(`ruff`/`flake8`), 타입체크 무결성
- **Tier 1 (Build & Packaging)**: 개발 단계에서는 기본 생략(선택). 최종 릴리스/배포 시에만 검증
- **Tier 2 (Regression & Unit Test)**: 기존 및 신규 단위/회귀 테스트(`pytest` / `unittest`) 100% 통과
- **Tier 3 (Runtime Smoke & Healthcheck)**: 프로세스 콜드스타트 및 엔트리포인트 임포트 생존성 검증
- **Tier 4 (Secret, EDR & Encoding Audit)**: API 키/시크릿 유출, EDR 트리거 고위험 패턴, 스크립트 인코딩 무결성 감사

### 자가 치유(Self-Healing) 및 원자적 롤백 원칙
- 게이트 실패 시 `harness.py`의 표준 JSON 진단 리포트를 바탕으로 최대 **3회**까지 자율 수정을 시도합니다.
- 3회 연속 실패 시 작업 전 체크포인트로 무손실 원자적 롤백을 수행하고 상세 원인을 사용자에게 보고합니다.

---

## 4. 🛡️ Enterprise EDR-Safe Coding & Hook Guard Protocol (EDR 안전 규약)

엔터프라이즈 보안 솔루션(CrowdStrike, SentinelOne, Defender for Endpoint 등)의 오탐 및 프로세스 차단을 방지하기 위해 다음 5대 패턴을 엄격히 금지하며, `.agents/hooks.json`(`PreToolUse`)을 통해 실행 전 시스템 레벨에서 차단합니다:

1. **의심스러운 쉘 실행 및 난독화 금지**:
   - `powershell.exe -EncodedCommand`, base64 디코딩 후 즉시 실행(`iex`, `eval`), 원격 스크립트 파이프 실행(`curl | sh`, `irm | iex`) 금지. 명시적인 파일 기반 스크립트 및 표준 인자만 사용합니다.
2. **타 프로세스 침범 및 메모리 조작 금지**:
   - `ctypes`, Win32 API(`VirtualAllocEx`, `WriteProcessMemory`, `CreateRemoteThread`) 등을 통한 프로세스 인젝션/조작 및 레지스트리 자동 실행 키(`Run`, `RunOnce`) 무단 수정 금지.
3. **임시 폴더 내 비표준 실행 파일 동적 생성 및 실행 회피**:
   - `%TEMP%`, `AppData\Local\Temp\` 등에 `.exe`, `.bat`, `.ps1`, `.vbs` 등을 동적으로 생성하고 즉시 실행하는 패턴 금지.
4. **네트워크/포트 무차별 스캐닝 및 과도한 프로세스 열거 완화**:
   - 서브넷 전체 포트 스캔(`nmap`, 멀티스레드 소켓 폭격) 및 로컬 프로세스 전체 목록의 짧은 주기 무한 루프 폴링 금지.
5. **시스템 자격 증명(Credential) 접근 패턴 절대 금지**:
   - SAM, LSASS 메모리 덤프 시도 또는 브라우저/OS 자격 증명 저장소 무단 접근 코드 금지.

---

## 5. ⚡ Minimal Build, Batch-First & ASCII Console Protocol (빌드 최소화 및 실행기 규약)

- **개발 중 무거운 컴파일/패키징 최소화**:
  - 개발 및 테스트 도중 PyInstaller, Nuitka, Webpack 번들링 등의 무거운 빌드를 매번 반복하지 않고 소스 코드 직접 실행으로 빠른 피드백 루프를 유지합니다.
  - 바이너리(`.exe`) 빌드는 타인 배포 또는 최종 릴리스 시점에 한해 `build.bat`으로 수행합니다.
- **배치 파일(`run.bat`) 기반 원클릭 실행 환경 표준화** (`.agents/skills/windows-gui-launcher/SKILL.md` 참조):
  - 프로젝트 루트에 원클릭 실행용 `run.bat`을 제공하여 더블 클릭만으로 즉시 구동되도록 구성합니다.
  - 가상환경(`venv` / `.venv`) 자동 감지 및 인자 전달(`%*`)을 포함합니다.
  - **🖥️ GUI 프로그램 무콘솔(No-Console) & 스마트 에러 가드**:
    - GUI 앱은 `python.exe` 대신 `pythonw.exe`와 `start` 명령어를 사용하여 **검은 CMD 콘솔 창이 남지 않고 즉시 닫히도록 구성**합니다.
    - 사일런트 크래시 방지를 위해 `2> crash_log.txt` 리다이렉션을 기본 적용하고, `--debug` 또는 `-d` 인자 전달 시 콘솔 창과 함께 실시간 로그를 출력하는 디버그 모드를 지원합니다.
- **🛡️ 윈도우 스크립트(`.bat` / `.ps1` / CLI) 콘솔 영문(ASCII) 출력 무결성**:
  - `cmd.exe` 및 PowerShell에서 UTF-8 한글 문자열과 OS 기본 코드페이지(CP949) 충돌로 인한 **글자 깨짐(Mojibake), 문법 파싱 오류, 명령어 오인식을 원천 방지**합니다.
  - 배치 파일(`.bat`, `.cmd`) 및 CLI 스크립트(`.ps1`, `.py`)의 **콘솔 실시간 출력 로그(`echo`, `Write-Host`, CLI `print`)는 원칙적으로 깔끔한 영문(ASCII) 위주로 작성**합니다.
  - 문서 파일(`*.md`, `*.json`) 및 데스크톱 GUI 위젯 화면 텍스트에는 한글을 자유롭게 사용합니다.

---

## 6. 🖥️ Native Desktop GUI First Protocol (네이티브 데스크톱 앱 우선 규약)

- **웹 애플리케이션(Web UI) 기본 채택 금지**:
  - 사용자가 명시적으로 "웹으로 만들어줘", "FastAPI/Flask/Streamlit/React로 해줘"라고 지정하지 않는 한, 로컬 웹 서버나 브라우저 기반 Web UI를 기본 아키텍처로 제안하거나 구현하지 않습니다.
- **Windows 네이티브 데스크톱 GUI 우선 개발**:
  - 사용자 인터페이스(UI)가 필요한 모든 애플리케이션은 **`CustomTkinter`** 또는 **`Tkinter`** (필요 시 PyQt/PySide) 기반의 독립 실행형 Windows 데스크톱 GUI로 개발합니다.

---

## 7. 🏷️ Antigravity Communication, Versioning & Safe Rollback Protocol

- **클릭 가능한 파일/심볼 링크 의무화**:
  - 사용자에게 파일이나 코드 심볼(클래스, 함수 등)을 안내할 때는 반드시 `[파일명](file:///절대/경로#L시작-L끝)` 형식의 클릭 가능한 링크를 제공합니다.
- **GitHub 문서화(`README.md`, `CHANGELOG.md`) 및 시맨틱 버전 관리(`vMAJOR.MINOR.PATCH`)**:
  - 프로젝트 목적, 핵심 기능, 조작 방법, 원클릭 실행(`run.bat`) 가이드를 일반 사용자도 쉽게 이해할 수 있는 친절한 한글 `README.md`로 작성합니다.
  - 기능 추가(`v1.1.0`), 패치(`v1.1.1`) 단위로 시맨틱 버전 태그를 발행하고 `CHANGELOG.md`에 변경 내역(`[Added]`, `[Changed]`, `[Fixed]`)을 누적 기록합니다.
- **언제든지 과거 시점 무손실 롤백 보장 (Safe Historic Rollback)**:
  - 사용자가 과거 특정 시점이나 버전으로 되돌리기를 원할 경우, Git 이력을 파괴하지 않고 안전하게 원복(`git revert` 또는 특정 태그/커밋 체크아웃)할 수 있도록 원자적 커밋 무결성을 유지합니다.
