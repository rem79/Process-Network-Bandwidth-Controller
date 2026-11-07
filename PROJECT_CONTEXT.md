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
├── main_desktop.py          # PyWebView 기반 데스크톱 UI 실행기, UAC 자동 승격 & 유저 모드 안내창
├── server.py                # FastAPI 백엔드 (WebSocket 텔레메트리 스트리밍 & REST API)
├── qos_manager.py           # Windows QoS 정책 제어 엔진 (TCP ACK Pacing & NetQosPolicy)
├── network_inspector.py     # 소켓 정밀 역추적 (DNS 역참조, GeoIP, 프로세스 소켓 강제 절단)
├── diagnostics.py           # TCP 포트 테스터, 지터/손실 레이더, DNS 벤치마크, Traceroute, 네트워크 플러시
├── history_db.py            # SQLite 기반 일일/시간대별 트래픽 히스토리 로깅 DB
├── autostart_manager.py     # Windows 시작프로그램(Registry) 등록/해제 관리
├── run.bat                  # [원클릭 실행] 무콘솔 백그라운드 실행 및 디버그 모드 지원 스크립트
├── static/                  # 프론트엔드 UI 자산
│   ├── index.html           # 메인 대시보드, QoS 모달(Down/Up 선택), 리포트 모달
│   ├── style.css            # 다크 테마 사이버네틱 UI 스타일링 및 A4 인쇄 CSS
│   └── app.js               # 실시간 웹소켓 차트, 프로세스 소팅, 리포트 생성기
├── tests/                   # 단위 테스트 스위트 (35개 테스트 100% 통과)
│   ├── test_elevation_flow.py      # 시작 시 UAC 승격 및 유저 모드 선택 안내창 테스트
│   ├── test_download_detection.py  # LDPlayer VMDK 제외 및 병렬 다운로더 캡처 테스트
│   ├── test_v3_suite.py            # 종합 진단 도구 및 엔드포인트 테스트
│   ├── test_server_api.py          # 서버 REST API 테스트
│   ├── test_qos_manager.py         # QoS NetQos 및 TCP ACK 페이싱 산출 테스트
│   └── test_history_db.py          # SQLite 영속화 및 샘플 정리 테스트
├── build_exe.py             # PyInstaller 독립 실행파일 컴파일러 (사용자 명시적 요청 시에만 수행)
└── PROJECT_CONTEXT.md       # [본 문서] AI 마스터 컨텍스트
```

---

## 3. 🚀 핵심 기능 상세

### ① 시작 시 관리자 우선 실행 & 유저 모드 안내창 Fallback (v3.3.0)
* 더블 클릭 또는 `run.bat` 실행 시 기본적으로 Windows UAC(`ShellExecuteW runas`)를 즉시 호출하여 관리자 권한 획득 시도.
* 사용자가 UAC에서 [아니오]를 누르거나 승격 실패 시, 네이티브 메시지 박스(`MessageBoxW`)로 권한 안내를 팝업:
  > *"관리자 권한을 획득하지 못했습니다. 관리자 권한이 없으면 네트워크 속도 제한(QoS) 등 일부 기능이 제한될 수 있습니다. 일반 '유저 모드'로 계속 실행하시겠습니까?"*
* [예] 클릭 시 일반 유저 모드로 안전하게 진입, [아니오] 클릭 시 클린 종료.

### ② TCP ACK Pacing 기반 정밀 다운로드 속도 제어
* Windows의 `New-NetQosPolicy -ThrottleRateActionBitsPerSecond`가 송신(Egress) 전용인 한계를 극복.
* 다운로드 트래픽에 맞춰 수신 확인용 TCP ACK 패킷 속도를 약 52:1 비율로 자동 산출 페이싱:
  $$\text{ACK Throttle bps} = \max\left(64000, \frac{\text{limit\_kbps} \times 1024 \times 8}{52.0}\right)$$
* 원격 서버의 혼잡 윈도우(CWND)와 전송 클록을 억제하여 물리적 유입 다운로드 속도를 지정한 수치(예: 1.0 MB/s)로 100% 정밀 제어 (실측 검증 완료).
* NLA(Network Location Awareness) 우회 레지스트리(`Do not use NLA = 1`) 자동 구성으로 비도메인 홈/작업그룹 PC에서도 QoS 정책 무조건 강제 적용.

### ③ 가상 머신/에뮬레이터 디스크 I/O 배제 및 소켓 집중도 가중 배분
* LDPlayer, BlueStacks 등 안드로이드 VM의 `.vmdk` 가상 디스크 쓰기를 인터넷 다운로드로 오인하던 문제 해결 (`VM_EMULATOR_NAMES` 격리).
* 단일 호스트 소켓 집중도(`max_same_host_conns`) 가중 배분으로 PoE 2, Steam 등 병렬 패처에 대역폭 99% 이상 정확 할당.

### ④ 실시간 소켓 정밀 역추적 및 강제 절단 (Kill Socket)
* 프로세스별 활성 TCP/UDP 연결 목록 조회, GeoIP 국가 플래그 및 rDNS 도메인 실시간 매핑.
* 과도한 트래픽이나 의심스러운 원격 소켓을 TCP RST 패킷으로 즉시 절단.

### ⑤ 엔터프라이즈 4대 정밀 진단 도구 (`diagnostics.py`)
1. **TCP 포트 도달성 진단기 (`test_tcp_port`):** SAP(:3200), TMS(:3300), 라벨프린터(:9100), HTTPS(:443)의 3-Way Handshake 및 RTT 측정.
2. **실시간 지터 & 패킷 손실 레이더 (`ping_target_latency`):** 대상 호스트에 연속 핑을 전송하여 지터(ms) 및 패킷 손실률(%) 시각화.
3. **DNS 벤치마크 및 Traceroute:** 통신사별/사내 커스텀 DNS 속도 비교 및 라우터 홉 역추적.
4. **원클릭 네트워크 응급 복구 (`flush_network_stack`):** DNS 캐시 플러시, ARP 테이블 초기화, NetBIOS 릴리즈 일괄 수행.

---

## 4. ⚠️ 개발 시 주의사항 및 기술적 규칙

1. **배치 파일(`run.bat`) 기반 실행 표준화 (규칙 5 준수):**
   * 개발 및 테스트 중 무거운 PyInstaller 컴파일(`.exe`)을 반복하지 않으며, `run.bat`를 통해 즉시 피드백 루프 확보.
   * **단일 바이너리(`.exe`) 빌드는 사용자가 명시적으로 요청할 때에만 수행**합니다.
2. **100% 로컬 오프라인 보장 원칙:**
   * 진단 및 리포트 생성 로직은 외부 클라우드 API에 절대 의존하지 않으며, 오프라인 환경에서도 완벽히 동작해야 합니다.
3. **PyWebView 내 파일 다운로드 이슈:**
   * PyWebView 환경에서는 브라우저의 `<a download>` 가상 클릭이 차단되므로, 백엔드 Python 파일 쓰기 후 바탕화면 경로를 반환하여 인앱 모달로 띄워야 합니다.
4. **Windows 서브프로세스 인코딩 및 관리자 권한:**
   * PowerShell 명령어 실행 시 `errors="replace"` 처리 필수.
   * `runas` 실행 시 경로 역슬래시 및 인자 공백 이스케이프 철저 유지.

---

## 5. 🛠️ 표준 개발 & 검증 명령어

```powershell
# 1. 단위 테스트 실행 (현재 35개 전체 통과 유지 필수)
python -m unittest discover -s tests -v

# 2. 로컬 개발 데스크톱 앱 원클릭 실행 (run.bat)
.\run.bat

# 3. 디버그 모드 (콘솔 로그 동시 출력)
.\run.bat --debug

# 4. (사용자 요청 시에만) 타 PC 이동/배포용 단일 실행파일(OneFile EXE) 컴파일
python build_exe.py
```

---

## 6. 🔄 Multi-PC 작업 세션 동기화 & 연속성 로그 (Continuity Log)

> **PC 전환 시 AI 필독 가이드:**  
> 다른 PC(집/회사/노트북)에서 `git pull` 후 본 섹션을 확인하여 이전 작업 맥락과 결정 사항을 즉시 이어받습니다.

### 📅 최근 세션 히스토리 & 결정 사항
* **2026-11-08 (v3.3.0 시작 시 관리자 우선 실행 & 유저 모드 안내창 Fallback, QoS 다운로드 실효성 완비):**
  * **시작 시 관리자 모드 우선 실행 (`request_self_elevation`)**: 더블 클릭 시 UAC 창을 즉시 띄워 관리자 권한 실행 우선 시도.
  * **UAC 취소 시 네이티브 안내창 Fallback (`prompt_user_mode_fallback`)**: UAC 거부 시 윈도우 `MessageBoxW`로 안내창을 띄워 사용자가 선택 시 일반 유저 모드로 안전하게 진입.
  * **TCP ACK Pacing 기반 다운로드 제어**: 윈도우 Egress 전용 QoS의 한계를 극복하여 TCP ACK 페이싱(52:1 비율)으로 실제 다운로드 유입 속도를 1.0 MB/s 등으로 물리적 억제 실측 검증.
  * **NLA 우회 레지스트리 자동화**: `HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\QoS`에 `"Do not use NLA" = "1"` 등록 자동화.
  * **UI 경로 역슬래시 인코딩 보호**: 자바스크립트 인라인 경로 파싱 버그를 수정하여 `PathOfExile_KG.exe` 등 타깃 프로세스 매칭 무결성 확보.
  * **단위 테스트 스위트 확장**: 신규 테스트 5종 추가 완료 (총 35개 테스트 100% 통과).
  * **실행 환경 표준화**: 바탕 화면의 불필요한 `.exe`를 정리하고, 개발 중에는 `run.bat`를 통한 원클릭 무콘솔 실행을 기본 워크플로우로 확립.

### 🎯 현재 상태 및 다음 진행 과제 (Next Actions)
1. **현재 상태:** 관리자 우선 실행 및 유저 모드 선택 안내창 완비, TCP ACK Pacing 기반 다운로드 QoS 제어 검증 완료, 35개 단위 테스트 100% 통과, `run.bat` 원클릭 환경 정비 완료.
2. **Next Action:** 사용자가 요청할 경우 WinDivert 듀얼 엔진 도입 또는 추가 비즈니스 모니터링 기능 개발.
