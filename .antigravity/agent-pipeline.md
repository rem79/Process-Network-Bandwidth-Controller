# Enterprise 7-Stage Agent Pipeline (GitHub Integrated)

## Execution Lifecycle

1. **[Step 1] Planning & Git Branching (`@pm`)**
   - 사용자 요구사항 분석 $\rightarrow$ WBS 세부 작업 분할 $\rightarrow$ `git checkout -b feature/<task-name>` 실행 $\rightarrow$ 인터페이스/API 스펙 문서 수립.
2. **[Step 2] Data & Schema Design (`@dba`)**
   - ERD 모델링 $\rightarrow$ DB 마이그레이션 DDL 스크립트 작성 $\rightarrow$ 인덱스 및 트랜잭션 격리 가이드 수립.
3. **[Step 3] Core Implementation & Atomic Commits (`@developer`)**
   - Step 1, 2 설계를 바탕으로 비즈니스 로직 및 모듈 구현 $\rightarrow$ 작업 단위별 `git commit -m "feat: ..."` 수행.
4. **[Step 4] Quality & Verification (`@qa`)**
   - 단위/통합 테스트 작성 $\rightarrow$ 엣지 케이스 검증 $\rightarrow$ `git commit -m "test: ..."` 수행.
5. **[Step 5] Security & Code Audit (`@auditor`)**
   - OWASP Top 10, 메모리/동시성 이슈 정적 분석 $\rightarrow$ 취약점 통과 승인 (반려 시 @developer 자율 수정).
6. **[Step 6] Infrastructure, Push & PR (`@devops`)**
   - Dockerfile 및 CI/CD 워크플로우 점검 $\rightarrow$ `git push origin feature/<task-name>` $\rightarrow$ PR(Pull Request) 본문 및 체인지 요약 생성.
7. **[Step 7] Documentation & Release Sync (`@writer`)**
   - OpenAPI/Swagger 명세, README.md, CHANGELOG.md 최신화 $\rightarrow$ `git commit -m "docs: ..."` 최종 동기화.
