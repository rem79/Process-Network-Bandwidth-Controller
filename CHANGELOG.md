# Changelog

All notable changes to the **Process Network Bandwidth Controller** will be documented in this file.

## [3.3.0] - 2026-11-08 (Administrator-First Launch & TCP ACK Pacing Throttling)
### Added
- **시작 시 관리자 권한 자동 승격 (Administrator-First Launch Flow)**:
  - 더블 클릭 및 바로가기 실행 시 기본적으로 윈도우 UAC(`ShellExecuteW runas`)를 즉시 호출하여 관리자 권한으로 실행을 시도.
  - 관리자 권한 획득 시 기존 스타터 프로세스는 즉시 종료되고 단일 윈도우 인스턴스로 매끄럽게 인계.
- **UAC 취소/실패 시 윈도우 네이티브 안내창 Fallback (User Mode Dialog)**:
  - 사용자가 UAC에서 "아니오"를 누르거나 권한 승격에 실패한 경우 `MessageBoxW`로 권한 안내 대화상자 표시.
  - "관리자 권한이 없으면 네트워크 속도 제한(QoS) 등 일부 기능이 제한될 수 있습니다. 일반 '유저 모드'로 계속 실행하시겠습니까?" 팝업 제공.
  - [예] 선택 시 유저 모드로 안전하게 진입하며, [아니오] 선택 시 깨끗하게 프로세스 종료.
- **TCP ACK Pacing 기반 정밀 다운로드 속도 제어**:
  - 윈도우 커널(`pacer.sys`)의 `New-NetQosPolicy`가 송신(Egress) 전용인 한계를 극복하기 위해, 다운로드 트래픽에 맞춰 수신 확인용 TCP ACK 패킷 속도를 약 52:1 비율로 자동 산출 페이싱.
  - 원격 서버의 혼잡 윈도우(CWND)와 ACK 클록을 억제하여 물리적 유입 다운로드 속도를 지정한 수치(예: 1.0 MB/s)로 100% 정밀 제어 실측 검증.
- **NLA(Network Location Awareness) 우회 레지스트리 자동 구성**:
  - 도메인 미가입 윈도우 10/11 환경에서 로컬 QoS가 무시되는 현상을 방지하기 위해 `HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\QoS`에 `"Do not use NLA" = "1"` 자동 보장.
- **QoS 대역폭 제한 모달 내 방향 선택 옵션 추가**:
  - 모달에 다운로드(Download Limit) 및 업로드(Upload Limit) 선택 드롭다운 추가.
- **신규 권한 흐름 단위 테스트 5종 추가 (`tests/test_elevation_flow.py`)**:
  - 전체 단위 테스트 35개 전 항목 통과 (35/35 PASSED).

### Fixed
- **UI 경로 역슬래시(`\`) 인라인 탈락 버그 수정**:
  - 자바스크립트 인라인 파싱 중 `D:\Daum Games\...`의 역슬래시가 탈락되던 문제를 `data-target`과 URI 인코딩으로 해결하여 `PathOfExile_KG.exe` 등 타깃 프로세스 매칭 무결성 확보.
- **원클릭 배치 스크립트(`run.bat`) 현행화**:
  - `main_desktop.py` 타깃팅 및 `.exe` 빌드 최소화 규격 준수.

## [3.2.0] - 2026-09-12 (Precise Download Attribution & VMDK Exclusion)
### Added
- **가상 머신/에뮬레이터 디스크 I/O 배제 (`VM_EMULATOR_NAMES`)**:
  - LDPlayer, BlueStacks, Nox, VirtualBox, VMware, WSL 등 안드로이드 VM/에뮬레이터의 `.vmdk` 가상 디스크 쓰기를 인터넷 다운로드로 오인하던 현상 방지.
- **동일 호스트 소켓 집중도(`max_same_host_conns`) 기반 가중 배분 알고리즘**:
  - PoE 2, Steam, 대용량 패처처럼 단일 CDN 서버에 16~32개 소켓을 집중 병렬 연결하는 프로세스를 정밀 식별하여 대역폭 99% 이상 정확 할당.

## [3.1.0] - 2026-08-26 (Hybrid User/Admin Mode & Zero UAC Barrier)
### Added
- **NIC Adapter & IPConfig (/all) Live Inspector (실무 네트워크 카드 진단)**:
  - `Diagnostic Toolbox` 탭에 사용자 PC의 모든 물리/무선 네트워크 카드(이더넷, Wi-Fi), IPv4 주소, 기본 게이트웨이, 서브넷 마스크, 물리적 MAC 주소, DNS 서버 설정을 한눈에 파악할 수 있는 시각적 어댑터 요약 카드 추가.
  - `ipconfig /all`의 전체 콘솔 원문을 터미널 뷰어로 토글 조회할 수 있으며, `[Copy Output]` 원클릭 클립보드 복사 지원.
- **UI 일관성 영문화 & 네온 Cyberpunk 테마 최적화**:
  - 상단 헤더 버튼: `Field Ops Manual`, `Export Diagnostic Report`
  - 시간 범위 필터 칩: `Today`, `10m`, `1h`, `3h`, `6h`, `12h`, `24h`
  - 트래픽 타이틀: `BANDWIDTH CONSUMERS (TODAY)`
- **전체 화면 100% 가변 폭 & 테이블 우측 짤림 방지 (Fluid Full-Width Layout)**:
  - 창을 최대화(Maximize)했을 때 100% 화면 전체에 맞추어 유연하게 확장되며 컬럼이 잘리지 않도록 최적화.
- **좌우 카드 레이아웃 높이 밸런스 조정**:
  - 좌측 `Top Consumers` 리스트 높이를 우측 `Daily Summary` 테이블과 동일하게 `calc(100vh - 280px)`로 확장하여 화면 불균형 해소.
- **실무 진단 매뉴얼 모달(Playbook Modal) 한/영 듀얼 언어 지원 (Bilingual Support)**:
  - 모달 상단에 `[🇰🇷 한국어]` / `[🇺🇸 English]` 언어 토글 탭을 배치하여 실무 SOP 및 용어사전을 한국어와 영어로 자유롭게 전환 조회 가능.
- **금일 전체 트래픽 소비 프로세스 목록 & 유연한 시간 범위 필터 (Time Range Selector)**:
  - Top 8개 제한을 해제하고 **금일(Today 00:00~) 데이터를 사용한 모든 프로세스를 트래픽 순서대로 누락 없이 전체 표시**.
  - `[🔄 Refresh]` 클릭 시 아이콘 360도 회전 애니메이션 및 `"X apps refreshed"` 네온 토스트 피드백 제공.
- **Windows Named Mutex 기반 중복 실행 방지 (Single Instance Guard)**:
  - 이미 프로그램이 실행 중일 때 추가로 더블 클릭 시, 중복 인스턴스가 생성되지 않고 기존 창을 자동으로 화면 맨 앞으로 복원(Restore & Bring to Front)하고 새 프로세스는 즉시 종료.
- **CPU (%) 및 RAM (MB) 컬럼 독립 분리 & 개별 정렬**:
  - 프로세스 모니터링 테이블에서 기존 `CPU / RAM` 통합 컬럼을 `CPU (%)`와 `RAM (MB)` 2개 컬럼으로 명확히 분리하고, 각각 헤더 클릭 오름차순/내림차순 정렬 지원.
- **Zero-UAC Direct Execution (일반 사용자 모드 기본 지원)**:
  - UAC 프롬프트 없이 더블 클릭 즉시 일반 권한으로 구동되어 트래픽 관제, 60초 차트, 소켓 역추적, 4대 진단 툴, AI 리포트 생성 및 인쇄를 자유롭게 이용 가능.
- **On-Demand Administrator Privilege Elevation (`/api/system/elevate`)**:
  - 일반 모드 실행 중 상단 상태 뱃지 또는 QoS 모달/정책 탭에서 원클릭으로 관리자 권한(UAC) 승격 재실행 지원.
- **Clear Admin Badging & Alert Banners**:
  - 관리자 권한이 필요한 기능(QoS 속도 제한 모달, Active QoS Rules 탭 등)에 `[🛡️ ADMIN REQUIRED]` 배지 및 친절한 안내 배너 명시.
- **PROJECT_CONTEXT.md Multi-PC Session Continuity Rule**:
  - 신규 프로젝트 자동 생성 및 다중 PC(집/회사) Git 동기화 후 세션 연속성 유지 규칙 파이프라인 반영.

## [3.0.0] - 2026-08-25 (Next-Gen Network Sentinel Suite)
### Added
- **Supercharged Sockets Inspector (Telemetry & Route Inspector):**
  - **Reverse DNS & GeoIP:** Real-time domain resolution, country flags (🇰🇷, 🇺🇸, 🇯🇵, 🇩🇪 등), and CDN/ASN organization mapping (Netflix, Cloudflare, AWS, Google).
  - **Live Ping & Latency Telemetry:** Real-time TCP connect RTT (ms) with fast (🟢), medium (🟡), slow (🔴) status pills.
  - **Socket-Level Termination (`[✂️ Kill Socket]`):** Direct TCP RST / connection teardown to drop bugged/malicious sockets without terminating host processes.
  - **Threat Intelligence Badging:** Heuristic scanning for suspicious ports (Metasploit, Mining Stratum, Tor, IRC).
- **Tab 4: 🌍 Global Cyber Map:**
  - Interactive Cyberpunk neon world map with real-time arc line animations connecting local origins to global cloud/CDN endpoints.
  - Active Outbound Destinations side-panel with latency metrics.
- **Tab 5: 🛠️ Diagnostic Toolbox:**
  - **Multi-DNS nslookup & Benchmark:** Instant domain propagation queries and comparative latency benchmarks across top DNS providers (KT, SK, LG, Cloudflare, Google, Quad9).
  - **Visual Hop Traceroute:** Step-by-step router hop tracing with GeoIP flags, router names, and latency hops.
  - **Local Wi-Fi / LAN Quality Diagnostic:** Wi-Fi signal percentage, gateway ping latency, and local vs server bottleneck analyzer.

## [2.3.0] - 2026-08-25

### Added
- **Interactive Bidirectional Table Header Sorting**: Added interactive click sorting with ascending (▲) and descending (▼) toggle icons to all column headers across both the **Live Process Sentinel Table** (`APPLICATION`, `PID`, `CONNECTIONS`, `DOWNLOAD SPEED`, `UPLOAD SPEED`, `CPU / RAM`, `LIMIT STATUS`) and the **Daily Analytics History Table** (`DATE`, `APPLICATION`, `UPLOAD`, `DOWNLOAD`, `TOTAL DATA`).
- **Non-blocking Neon Toast Notification System**: Replaced all blocking browser modal alerts with responsive cyber-neon toast notifications and full UI crash protection.
- **Active QoS Rule Adjustment**: Added an **`Adjust Limit`** action button to each configured policy card in the Active QoS Rules tab, allowing users to modify existing limits, presets, and priorities on the fly.
- **Micro-Bandwidth Presets**: Added 10 KB/s, 100 KB/s, and 500 KB/s ultra-low speed limit presets for extreme traffic throttling tests.

## [2.1.0] - 2026-08-25

### Fixed
- **Windows QoS Policy Throttling Match**: Fixed Windows `NetQosPolicy` `-AppPathNameMatchCondition` to pass pure executable filenames (e.g. `chrome.exe` instead of malformed absolute paths), ensuring Windows QoS engine correctly throttles Chrome/Netflix streaming traffic.

### Changed
- **Global Speed Limit Presets**: Updated quick preset buttons on the dashboard to **10 MB/s**, **100 MB/s**, **1 GB/s**, and **Off** for high-speed network environments.
- **Traffic Analytics QoS Creation**: Added direct QoS Limit creation buttons to both **Top Bandwidth Consumers (24h)** list items and **Daily Data Usage Summary** table rows.

## [2.0.0] - 2026-08-25

### Added
- **SQLite Traffic Analytics Engine (`history_db.py`)**: Persistent high-frequency sampling and daily/hourly data usage aggregations in `%APPDATA%/AntigravityNetworkSentinel/traffic_history.db`.
- **Socket Inspector Modal**: Real-time per-process socket inspection showing protocol (TCP/UDP), local/remote IP endpoints, and socket status.
- **QoS Priority Tagging**: High (DSCP 46), Normal, and Low (DSCP 10) QoS bandwidth policy levels.
- **PowerShell Parameter Sanitization**: Alphanumeric policy name sanitization and exe string filtering in `qos_manager.py`.
- **Navigation Tabs & Category Filtering**: Three distinct views (Live Sentinel, Traffic Analytics, Active QoS Policies) and dynamic category chips (All, Browsers, High Usage, Throttled).
- **Automated Test Suite**: 13 unit/integration tests covering SQLite persistence, QoS sanitization, and FastAPI REST endpoints in `tests/`.
- **PyInstaller Build Improvements**: Added hidden imports for `history_db` and `sqlite3` in `build_exe.py`.
- **Documentation**: Updated `README.md` and REST API specification.
