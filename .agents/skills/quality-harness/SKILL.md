---
name: quality-harness
description: >-
  Executes the 5-Tier Universal Quality Gate (Syntax/Lint, Build, Regression Tests, Runtime Smoke, Security/EDR Audit)
  via harness.py and manages automated self-healing loops (up to 3 attempts) with atomic rollback on failure.
  Activate this skill whenever verifying code changes, running tests, or preparing commits/releases.
---

# Quality Harness & Self-Healing Protocol (v2.0)

이 스킬은 프로젝트 루트의 `harness.py`를 실행하여 5단계 품질 게이트를 검증하고, 실패 시 표준 JSON 진단 리포트를 기반으로 최대 3회까지 자율 교정(Self-Healing)을 수행하는 절차입니다.

---

## 1. 5-Tier Quality Gate Matrix

1. **Tier 0 (Syntax & Static Analysis)**: 프로젝트 로컬 가상환경(`.venv` / `venv`) 우선 감지 후 `py_compile` 및 정적 문법 파싱 무결성 검증
2. **Tier 1 (Build & Packaging)**: `harness.json`에 바인딩된 경우에만 실행 (개발 중 기본 생략으로 빠른 피드백 유지)
3. **Tier 2 (Regression & Unit Test)**: `unittest` 또는 `pytest` 스위트 100% 통과 검증
4. **Tier 3 (Runtime Smoke & Healthcheck)**: 엔트리포인트 모듈 임포트 및 콜드스타트 크래시 여부 검증
5. **Tier 4 (Secret & EDR Security Audit)**: 하드코딩된 API 키/시크릿 및 EDR 오탐 유발 고위험 패턴(`-EncodedCommand`, Win32 메모리 인젝션, 원격 파이프 실행 등) 정적 스캔

---

## 2. Execution Command

현재 작업 중인 프로젝트 루트에서 상대 경로로 즉시 실행합니다:

```powershell
python harness.py
```

---

## 3. Structured Self-Healing Loop (최대 3회 자율 교정)

`python harness.py` 실행 결과 `"status": "FAILED"`가 반환되면:

1. **진단 분석**: 출력된 JSON의 `evaluated_tier` 및 `diagnostics`(`error_category`, `stderr`, `details`, `recommendation`)를 정밀 분석합니다.
2. **원자적 교정**: 실패 원인을 해결하는 최소한의 명확한 코드 수정을 적용합니다.
3. **재검증**: `python harness.py`를 다시 실행합니다. (최대 **3회**까지 반복)
4. **무손실 롤백 (Terminal Rollback)**:
   - 3회 연속 자가 치유에 실패할 경우, 환경을 오염시키지 않도록 즉시 작업 전 체크포인트(`git checkout -- .` 또는 백업 상태)로 원복하고 상세 실패 원인을 사용자에게 보고합니다.

---

## 4. Custom Gate Configuration (`harness.json`)

프로젝트별 맞춤 검증 명령어가 필요한 경우 루트의 `harness.json`을 통해 오버라이드합니다:

```json
{
  "tiers": {
    "tier0_lint": { "command": "" },
    "tier1_build": { "command": "" },
    "tier2_test": { "command": "" },
    "tier3_smoke": { "command": "" },
    "tier4_security": { "command": "internal_security_scan" }
  }
}
```
