---
name: quality-harness
description: >-
  Enforces the 5-Tier Quality Gate (Syntax, Build, Regression Tests, Runtime Smoke, Security Audit)
  and runs automated self-healing loops upon test failures.
  Use when verifying code changes, preparing PRs, or executing regression tests.
---

# Quality Harness & Self-Healing Protocol

이 스킬은 작성된 코드가 5단계 품질 기준을 만족하는지 검증하고, 실패 시 자동 진단 리포트를 바탕으로 최대 3회까지 자율 수정을 수행하는 하네스 실행 지침입니다.

---

## 1. Quality Gate Tiers

1. **Tier 0 (Syntax & Static)**: 린터, 타입체커, 컴파일러 문법 파싱 오류 검증
2. **Tier 1 (Build & Packaging)**: 번들링/빌드 충돌 및 아티팩트 무결성 확인
3. **Tier 2 (Regression & Unit Tests)**: 기존 및 신규 테스트 100% 통과 보장
4. **Tier 3 (Runtime Smoke & Healthcheck)**: 프로세스 기동 즉시 크래시(Cold Start) 여부 및 헬스체크
5. **Tier 4 (Secret & Security Audit)**: 토큰/인증정보 유출 및 CVE 취약점 차단

---

## 2. Execution & Diagnostics

### 하네스 엔진 실행
```bash
python c:/temp/py/.antigravity/harness.py
```

### Self-Healing 루프 (최대 3회)
하네스 실행 결과 `status: FAILED`와 진단 리포트가 반환되면:
1. `evaluated_tier` 및 `diagnostics`의 에러 카테고리와 실패 파일을 분석합니다.
2. 문제를 해결하는 원자적 수정을 적용합니다.
3. 하네스를 재실행하여 검증합니다. (최대 3회 반복)
4. 3회 연속 실패 시 작업 전 커밋(`git checkout .` 또는 백업 스냅샷)으로 롤백하고 실패 원인을 사용자에게 상세 보고합니다.
