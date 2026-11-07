# Enterprise 7-Stage Agent Pipeline (Universal Harness & Multi-PC Context Sync Integrated)

## Execution Lifecycle

1. **[Step 1] Planning, Context Initialization & Checkpoint (`@pm`)**
   - 사용자 요구사항 분석 $\rightarrow$ **`PROJECT_CONTEXT.md` 존재 여부 확인 (미존재 시 자동 생성)** $\rightarrow$ **Harness Pre-Flight 체크포인트(스냅샷/브랜치) 생성** $\rightarrow$ `git checkout -b feature/<task-name>` 실행 $\rightarrow$ 인터페이스/API 스펙 문서 수립.
2. **[Step 2] Data & Schema Design (`@dba`)**
   - ERD 모델링 $\rightarrow$ DB 마이그레이션 DDL 스크립트 작성 $\rightarrow$ 인덱스 및 트랜잭션 격리 가이드 수립.
3. **[Step 3] Core Implementation & Atomic Commits (`@developer`)**
   - Step 1, 2 설계를 바탕으로 비즈니스 로직 및 모듈 구현 $\rightarrow$ **Harness Tier 0 (구문/정적 분석) & Tier 1 (빌드) 자체 검증 통과** $\rightarrow$ 작업 단위별 `git commit -m "feat: ..."` 수행.
4. **[Step 4] Quality, Regression & Harness Gate Verification (`@qa`)**
   - 단위/통합 테스트 작성 $\rightarrow$ **Harness Tier 2 (회귀/단위 테스트) & Tier 3 (런타임 스모크/헬스체크) 실행 및 `harness_status: PASSED` 공식 획득** $\rightarrow$ `git commit -m "test: ..."` 수행.
5. **[Step 5] Security & Code Audit (`@auditor`)**
   - **Harness Tier 4 (시크릿/하드코딩 및 취약점 감사)** $\rightarrow$ OWASP Top 10 정적 분석 $\rightarrow$ 보안 승인(Sign-off, 반려 시 하네스 진단 리포트 피드백).
6. **[Step 6] Infrastructure, Push & PR (`@devops`)**
   - **Harness 전 게이트(Tier 0~4) 최종 통과 여부 검증** $\rightarrow$ Dockerfile/CI 점검 $\rightarrow$ `git push origin feature/<task-name>` $\rightarrow$ PR(Pull Request) 본문 및 체인지 요약 생성.
7. **[Step 7] Documentation & Multi-PC Context Sync (`@writer`)**
   - OpenAPI/Swagger 명세, README.md, CHANGELOG.md 최신화 $\rightarrow$ **`PROJECT_CONTEXT.md`에 대화 맥락, 설계 결정 사항, 하네스 검증 결과, 현재 진행도 및 Next Actions를 완벽히 현행화** $\rightarrow$ `git commit -m "docs: sync project context and release notes"` 최종 동기화.

