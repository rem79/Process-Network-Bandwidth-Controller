# 🛡️ Process Network Bandwidth Controller (Network Sentinel)
## 📌 AI Master Project Context & Knowledge Base

> **문서 목적:**  
> 이 문서는 집(Home)과 회사(Office) 등 여러 개발 환경에서 AI 페어 프로그래밍 어시스턴트(Antigravity 등)가 프로젝트의 도메인 배경, 전체 아키텍처, 주요 기능, 개발 히스토리 및 코딩 규칙을 즉시 파악하고 일관되게 작업을 이어받을 수 있도록 작성된 **현행화 마스터 컨텍스트 문서**입니다.

---

## 1. 🏢 비즈니스 도메인 및 엔터프라이즈 배경

### 📦 3-Tier SAP ERP & TMS 물류 아키텍처
본 프로젝트는 제조/물류 현장의 네트워크 장애 예방 및 대역폭 통제를 위해 구축되었습니다:
1. **Client PC (로컬 작업자 환경):** Windows 10/11 환경에서 SAP GUI, 웹 ERP, 안드로이드 에뮬레이터(LD플레이어 다중 구동 등) 동시 실행.
2. **SAP ERP & 중국 TMS 서버 (Middle Tier):**
   * SAP GUI / Dispatcher 통신 (`TCP :3200`)
   * 중국 TMS 연동 및 RFC Gateway (`TCP :3300`)
   * 출하 및 송장 발행 시 SAP/TMS를 거쳐 로컬 PC로 데이터 패킷 유입.
3. **출하장 바코드 라벨 프린터 (Endpoint):**
   * Zebra 및 산업용 바코드 라벨 프린터 (`TCP :9100`, RAW 9100 / LPD 515)
   * 백그라운드 프로세스(LD플레이어, 대용량 다운로드 등)가 네트워크 대역폭이나 CPU 자원을 과점유할 경우, 라벨 프린터 통신이 타임아웃되어 **송장 출력 지연 및 출하 마비** 발생.

---

## 2. 🧩 핵심 모듈 및 아키텍처 구성

```
Process-Network-Bandwidth-Controller/
├── main_desktop.py       # PyWebView 기반 데스크톱 윈도우 UI 실행기 & 백그라운드 서버 스레드
├── server.py             # FastAPI 백엔드 (WebSocket 텔레메트리 스트리밍 & REST API)
├── qos_manager.py        # Windows 커널 QoS 정책 제어 엔진 (PowerShell NetQoS 래퍼)
├── network_inspector.py  # 소켓 정밀 역추적(DNS 역참조, GeoIP, 프로세스 소켓 강제 절단)
├── diagnostics.py        # TCP 포트 테스터, 지터/패킷 손실 레이더, DNS 벤치마크, Traceroute, 네트워크 플러시
├── history_db.py         # SQLite 기반 일일/시간대별 트래픽 히스토리 로깅 DB
├── autostart_manager.py  # Windows 시작프로그램(Registry) 등록/해제 관리
├── static/               # 프론트엔드 UI 자산
│   ├── index.html        # 메인 대시보드 및 모달 팝업 구조
│   ├── style.css         # 다크 테마 사이버네틱 UI 스타일링 및 A4 인쇄 CSS
│   └── app.js            # 실시간 웹소켓 차트, 프로세스 소팅, 리포트 생성기
├── tests/                # 단위 테스트 스위트 (22개 테스트 전체 통과)
│   ├── test_v3_suite.py  # 종합 진단 도구 및 엔드포인트 테스트
│   ├── test_server_api.py
│   ├── test_qos_manager.py
│   └── test_history_db.py
├── build_exe.py          # PyInstaller 독립 실행파일 컴파일러
└── PROJECT_CONTEXT.md    # [본 문서] AI 마스터 컨텍스트
```

---

## 3. 🚀 핵심 기능 상세

### ① 실시간 트래픽 관제 & 프로세스별 QoS 대역폭 제어
* 프로세스별 실시간 다운로드/업로드 속도(KB/s, MB/s) 및 CPU/메모리 모니터링
* `qos_manager.py`를 통해 Windows QoS 정책을 커널 레벨에서 즉시 적용/해제 (`[Throttle]` 모달)
* 시스템 트레이 최소화(`pystray`) 및 윈도우 부팅 시 자동 시작 지원

### ② 실시간 소켓 정밀 역추적 및 강제 절단 (Kill Socket)
* 프로세스별 활성 TCP/UDP 연결 목록 조회
* 원격 IP의 GeoIP 국가 및 rDNS 도메인 실시간 확인
* 불필요하거나 과도한 트래픽을 유발하는 원격 소켓을 TCP RST 패킷 또는 API로 즉시 강제 절단

### ③ 엔터프라이즈 4대 정밀 진단 도구 (`diagnostics.py`)
1. **TCP 포트 도달성 진단기 (`test_tcp_port`):** SAP(:3200), TMS(:3300), 라벨프린터(:9100), HTTPS(:443)의 3-Way Handshake 도달 여부 및 RTT 측정.
2. **실시간 지터 & 패킷 손실 레이더 (`ping_target_latency`):** 대상 호스트에 연속 핑을 전송하여 지터(Jitter ms) 및 패킷 손실률(%)을 실시간 캔버스 그래프로 시각화.
3. **DNS 벤치마크 및 Traceroute:** 통신사별(KT, SK, LG, Google, Cloudflare) DNS 속도 비교 및 라우터 홉 역추적.
4. **원클릭 네트워크 응급 복구 (`flush_network_stack`):** DNS 캐시 플러시(`ipconfig /flushdns`), ARP 테이블 초기화(`arp -d`), NetBIOS 릴리즈를 원클릭으로 일괄 수행.

### ④ 엔터프라이즈 종합 인텔리전스 진단 리포트 (v4.5 Suite)
* **100% 오프라인 로컬 동작:** 외부 인터넷이 완전히 끊긴 상황에서도 로컬 AI 휴리스틱 룰 엔진이 0.003초 만에 원인 분석.
* **종합 건전성 점수 (Health Score: 100점 만점):** 게이트웨이 핑, 어댑터 품질, CPU 과점유, 대역폭 경합 자동 계산.
* **AI 로컬 진단 소견 & 조치 권고안 수록:** 병목 프로세스(LD플레이어 등) 식별 및 즉시 조치 방안 가이드.
* **A4 인쇄 & PDF 최적화:** 브라우저 인쇄(`Ctrl + P`) 시 정갈한 사내 보고서 규격 자동 정렬.
* **인앱 완료 팝업 & 파일 탐색기 연동:** 바탕화면에 HTML 자동 생성 및 탐색기(`explorer /select`) 연동.

---

## 4. ⚠️ 개발 시 주의사항 및 기술적 규칙

1. **100% 로컬 오프라인 보장 원칙:**
   * 진단 및 리포트 생성 로직은 외부 클라우드 API에 절대 의존하지 않으며, 인터넷 단절 상태에서도 완벽히 동작해야 합니다.
2. **PyWebView 내 파일 다운로드 이슈:**
   * PyWebView 환경에서는 브라우저의 `<a download>` 가상 클릭이 차단되므로, 백엔드 Python 파일 쓰기(`server.py`의 `/api/diagnostics/export-report`) 후 바탕화면 경로를 반환하여 인앱 모달(`openReportExportModal`)로 띄워야 합니다.
3. **전역 변수 정합성 유지 (`static/app.js`):**
   * 실시간 프로세스 목록은 `allProcesses`, 프로세스별 포맷 속도는 `p.down_formatted` / `p.up_formatted`, 소켓 수는 `p.connections`를 사용해야 합니다.
4. **Windows 서브프로세스 인코딩 및 관리자 권한:**
   * PowerShell 명령어 실행 시 `errors="replace"` 처리 필수. QoS 및 네트워크 초기화는 UAC 관리자 권한이 요구됩니다.

---

## 5. 🛠️ 표준 개발 & 검증 명령어

```powershell
# 1. 단위 테스트 실행 (현재 22개 전체 통과 유지 필수)
python -m unittest discover -s tests -v

# 2. 로컬 개발 데스크톱 앱 실행
python main_desktop.py

# 3. 다른 PC 이동/배포용 단일 실행파일(OneFile EXE) 컴파일
python build_exe.py
# 결과물: dist/NetworkSentinelApp.exe (단 1개의 파일로 타 PC에서 즉시 구동)
```

---

## 6. 🔄 Multi-PC 작업 세션 동기화 & 연속성 로그 (Continuity Log)

> **PC 전환 시 AI 필독 가이드:**  
> 다른 PC(집/회사/노트북)에서 `git pull` 후 본 섹션을 확인하여 이전 작업 맥락과 결정 사항을 즉시 이어받습니다.

### 📅 최근 세션 히스토리 & 결정 사항
* **2026-08-31 (v3.1.0 사내 전용 DNS 벤치마크 지원 & 타 PC 배포용 단일 포터블 EXE 완비):**
  * **사내 커스텀 DNS & 로컬 DNS 자동 연동:** `NSLOOKUP & DNS BENCHMARK`에 사내 프라이빗 DNS IP(예: `10.x.x.x`, `192.168.x.x`) 직접 입력 슬롯 추가 및 현재 PC 어댑터에 할당된 사내 DNS 자동 감지 기능을 추가하여, 통신사/글로벌 DNS와 사내 DNS의 응답 속도 및 사내 도메인 해석 결과를 동시 벤치마킹하도록 개선.
  * **단 1개의 포터블 단일 파일(`dist/NetworkSentinelApp.exe`) 빌드:** 폴더 형태가 아닌 단 1개의 `.exe` 파일로 압축 패키징하여 USB 복사나 네트워크 전송으로 다른 PC에서 추가 설치/폴더 없이 즉시 실행 가능하도록 개편.
  * **Leaflet.js 기반 고해상도 인터랙티브 실사 세계지도:** CartoDB Dark Matter 고해상도 타일 레이어 + 실시간 아크 빔 + 마우스 줌/패닝 지원.
  * **진단 도구함 상하 순서 최적화 & IPConfig 인스펙터 완비:** 로컬 상태 $\rightarrow$ IPConfig 인스펙터 $\rightarrow$ 원클릭 응급 복구 $\rightarrow$ 4대 정밀 진단 툴 순서 완비.
  * 전체 단위 테스트 22개 통과 확인 및 단일 실행 파일(`dist/NetworkSentinelApp.exe`) 컴파일 완료.

### 🎯 현재 상태 및 다음 진행 과제 (Next Actions)
1. **현재 상태:** 사내 커스텀 DNS 벤치마크, 타 PC 즉시 실행 가능한 단일 포터블 EXE(`dist/NetworkSentinelApp.exe`), Leaflet 인터랙티브 실사 세계지도, 진단 툴박스 최적 배치, IPConfig 실시간 진단, 100% 화면 가변 폭, 한/영 듀얼 매뉴얼, 금일 전체 트래픽 리스트, 시간 필터 칩, 중복 실행 방지, CPU/RAM 분리, 무권한 일반 실행 및 UAC 원클릭 전환이 모두 완비된 배포 준비 완료.
2. **Next Action:** 사용자 타 PC 테스트 및 실무 배포.













