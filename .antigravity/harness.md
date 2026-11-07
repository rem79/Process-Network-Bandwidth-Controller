# Universal Agent Execution & Quality Harness Specification

이 문서는 모든 프로젝트와 프로그래밍 언어 환경에서 AI 에이전트의 작업 안전성, 무결성, 자가 치유 및 배포 승인을 보장하기 위한 **범용 에이전트 실행 및 품질 하네스(Universal Harness)**의 표준 규격입니다.

---

## 1. Core Principles (핵심 5대 원칙)

1. **Stack-Agnostic Autonomy (스택 비종속성)**: 언어나 프레임워크에 구애받지 않고, 프로젝트 메타데이터를 기반으로 툴체인을 자동 인식하거나 선언적 설정(`harness.json`)을 따릅니다.
2. **Zero-Damage Atomic Rollback (무손실 원자적 롤백)**: 작업 착수 직전 체크포인트를 생성하며, 검증 실패 및 복구 불가 시 작업 전 상태로 100% 원복합니다.
3. **Multi-Tier Quality Gates (다계층 품질 게이트)**: 구문, 빌드, 테스트, 런타임 스모크, 보안까지 5단계의 품질 검증을 단계별로 강제합니다.
4. **Structured Self-Healing Feedback (구조화된 자가 치유)**: 실패 시 단순 에러 텍스트가 아닌 원인 분류, 영향 파일, 권장 조치안이 포함된 표준 JSON 진단 리포트를 발행하여 에이전트의 자율 교정을 유도합니다.
5. **No Pass, No Merge (품질 통과 강제)**: 하네스의 `PASSED` 판정이 없으면 어떠한 브랜치 머지, 원격 push, 배포도 허용되지 않습니다.

---

## 2. Environment Auto-Detection Matrix (런타임 자동 감지)

하네스는 프로젝트 루트를 탐색하여 아래 우선순위로 툴체인을 식별하고 게이트 명령어를 동적으로 바인딩합니다.

| 프로젝트 지표 (Indicators) | 대상 스택 | Tier 0 (정적/타입) | Tier 1 (빌드) | Tier 2 (단위/회귀 테스트) |
| :--- | :--- | :--- | :--- | :--- |
| `pyproject.toml`, `requirements.txt` | **Python** | `python -m py_compile`, `flake8` | `python -m build` (선택) | `pytest`, `unittest` |
| `package.json` | **Node / TypeScript** | `npm run lint`, `tsc --noEmit` | `npm run build` | `npm test` |
| `Cargo.toml` | **Rust** | `cargo clippy` | `cargo build` | `cargo test` |
| `go.mod` | **Go** | `golangci-lint` | `go build ./...` | `go test ./...` |
| `pom.xml`, `build.gradle` | **Java / Kotlin** | `checkstyle` | `./gradlew assemble` | `./gradlew test` |
| `CMakeLists.txt`, `Makefile` | **C / C++** | `cppcheck` | `make build` / `cmake --build` | `ctest` / `make test` |

> **Custom Override (`harness.json`)**: 루트에 `harness.json`이 존재할 경우 자동 감지된 명령어보다 사용자 정의 명령어가 최우선 적용됩니다.
> ```json
> {
>   "tier0_lint": "npm run lint",
>   "tier1_build": "npm run build",
>   "tier2_test": "npm run test:ci",
>   "tier3_smoke": "node scripts/smoke_test.js",
>   "tier4_security": "npm audit --audit-level=high"
> }
> ```

---

## 3. The 5-Tier Quality Gate Matrix (다계층 게이트)

### [Tier 0] Syntax & Static Analysis Gate (구문 및 정적 무결성)
- 컴파일러/인터프리터 파싱 에러, 심각한 린트 위반, 타입 불일치 차단.
- 검증 대상: 모든 변경 및 신규 파일.

### [Tier 1] Build & Compilation Gate (빌드 무결성)
- 의존성 패키징 충돌, 링킹 에러, 번들 생성 실패 차단.
- 산출물: 실행 가능한 아티팩트(바이너리, 번들 디렉토리, 패키지 파일 등).

### [Tier 2] Regression & Unit Test Gate (기능 회귀 방지)
- 기존 테스트 스위트가 100% 통과하여 회귀 버그(Regression)가 없음을 증명.
- 신규 작성된 기능/수정건에 대한 테스트 케이스 성공 확인.

### [Tier 3] Runtime Smoke & Healthcheck Gate (런타임 생존성)
- 프로세스 기동 즉시 크래시 발생 여부 검증 (Cold Start 체크).
- 스모크 스크립트 실행 또는 헬스체크 엔드포인트(`GET /health` 등) 핑 검증.

### [Tier 4] Secret & Security Gate (보안 및 규정 준수)
- 하드코딩된 시크릿 정규식 검사 (API Keys, JWT, Private Keys, DB Passwords).
- 알려진 High/Critical CVE 취약점 의존성 차단.

---

## 4. Atomic Checkpoint & Rollback Protocol (롤백 규약)

1. **Pre-Flight Snapshot**:
   - 에이전트 작업 시작 전, 하네스는 작업 상태를 보존합니다:
     - Git 환경: `git stash create` 또는 임시 백업 브랜치 `checkpoint/<task>-<timestamp>`
     - Non-Git/로컬 환경: `.backups/<timestamp>_<task>` 디렉토리 스냅샷
2. **Gate Evaluation**:
   - 코드 수정 완료 후 Tier 0부터 Tier 4까지 순차 실행.
3. **Self-Healing Attempt (최대 3회)**:
   - 특정 Tier 실패 시 하네스는 아래 JSON 진단 리포트를 생성하여 에이전트에게 자율 수정 명령 전달.
4. **Terminal Rollback**:
   - 3회 연속 자가 치유 실패 또는 치명적 시스템 손상 감지 시, 하네스는 체크포인트를 복원하여 변경 사항을 전면 취소하고 실패 로그를 사용자에게 보고.

---

## 5. Standard Diagnostic Telemetry Schema (진단 리포트 스키마)

게이트 실패 시 하네스가 에이전트 및 사용자에게 반환하는 표준 인터페이스입니다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "harness_version": "1.0.0",
  "timestamp": "2026-09-16T06:30:00Z",
  "status": "FAILED",
  "evaluated_tier": "Tier 2: Regression & Unit Test Gate",
  "diagnostics": {
    "command": "pytest tests/test_transcriber.py",
    "exit_code": 1,
    "error_category": "AssertionError",
    "failing_files": [
      "transcriber.py:142",
      "tests/test_transcriber.py:58"
    ],
    "summary": "Expected 200 OK with transcription text, got empty string."
  },
  "recommended_action": "Check audio buffer flushing logic in transcriber.py before retrying.",
  "attempt_count": 1,
  "max_attempts": 3
}
```

---

## 6. Agent Governance Integration (파이프라인 통제)

- **`@developer`**: 기능 구현 후 하네스를 호출하여 `status: PASSED`를 획득해야만 `@qa` 및 `@auditor`에게 인계할 수 있습니다.
- **`@qa`**: 하네스의 Tier 2(테스트) 및 Tier 3(스모크) 결과를 기반으로 품질 게이트를 최종 승인합니다.
- **`@devops`**: 하네스의 최종 `PASSED` 리포트가 없으면 원격 `git push` 및 PR 생성이 기술적으로 불가능합니다.
