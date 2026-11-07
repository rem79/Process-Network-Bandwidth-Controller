# Process Network Bandwidth Controller (Antigravity Sentinel v3.3)

윈도우 환경에서 실행 중인 모든 프로세스의 실시간 네트워크 트래픽(다운로드/업로드 속도 및 누적량, 소켓 연결 수)을 정밀 모니터링하고, Windows `NetQosPolicy` 및 **TCP ACK Pacing** 엔진을 활용하여 프로세스별/전역 대역폭을 즉각 제한(QoS Throttling) 및 우선순위를 제어할 수 있는 고성능 데스크톱 컨트롤러입니다.

---

## 🚀 주요 핵심 기능 (v3.3)

1. **시작 시 관리자 권한 자동 승격 & 유저 모드 안내창 (v3.3.0)**
   - 실행 시 윈도우 UAC 창을 즉시 띄워 관리자 권한으로 실행 우선 시도
   - UAC 취소 또는 실패 시, 윈도우 네이티브 안내창(`MessageBoxW`)을 띄워 유저 모드로 계속 실행할지 친절히 안내
   - [예] 선택 시 안전하게 유저 모드로 진입하며, [아니오] 선택 시 클린 종료

2. **TCP ACK Pacing 기반 정밀 다운로드 속도 제어**
   - 윈도우 커널(`pacer.sys`)의 Egress 전용 QoS 한계를 극복하여 수신 확인용 TCP ACK 패킷을 약 52:1 비율로 페이싱
   - 물리적 유입 다운로드 속도를 지정한 수치(예: 1.0 MB/s, 8.0 MB/s 등)로 정밀하게 제한 실측 검증
   - 비도메인 윈도우 10/11 환경에서도 QoS가 작동하도록 NLA 우회 레지스트리(`Do not use NLA = 1`) 자동 구성

3. **가상 머신/에뮬레이터 디스크 I/O 배제 및 소켓 집중도 가중 배분**
   - LDPlayer, BlueStacks 등 안드로이드 VM의 `.vmdk` 가상 디스크 쓰기를 인터넷 다운로드로 오인하지 않도록 격리
   - PoE 2, Steam 등 병렬 패처의 동일 호스트 소켓 집중도를 분석하여 실제 대용량 다운로더에 대역폭 99% 이상 정확 할당

4. **실시간 트래픽 텔레메트리 & 소켓 역추적 (Socket Inspector)**
   - WebSocket 스트림을 통해 1초 단위로 시스템 전체 및 개별 프로세스 I/O 실시간 측정
   - 프로세스별 활성 TCP/UDP 연결 목록 조회, GeoIP 국가 플래그 및 rDNS 도메인 실시간 매핑
   - 비정상 소켓 즉시 강제 절단 (`[✂️ Kill Socket]`) 지원

5. **엔터프라이즈 4대 정밀 진단 도구 & 오프라인 AI 리포트**
   - TCP 포트 도달성 진단기 (SAP :3200, TMS :3300, 라벨프린터 :9100, HTTPS :443)
   - 실시간 지터 & 패킷 손실 레이더
   - DNS 벤치마크 및 시각적 Traceroute
   - 원클릭 네트워크 응급 복구 (`ipconfig /flushdns`, `arp -d`)
   - 100% 로컬 오프라인 AI 종합 진단 리포트 생성 및 A4 인쇄 지원

---

## 🧩 프로젝트 구조

```
Process-Network-Bandwidth-Controller/
├── main_desktop.py          # PyWebView 데스크톱 UI 실행기, UAC 자동 승격 & 유저 모드 안내창
├── server.py                # FastAPI 백엔드 (WebSocket 텔레메트리 & REST API)
├── qos_manager.py           # Windows QoS 정책 제어 엔진 (TCP ACK Pacing & NetQosPolicy)
├── network_inspector.py     # 소켓 정밀 역추적 (DNS 역참조, GeoIP, 프로세스 소켓 강제 절단)
├── diagnostics.py           # TCP 포트 테스터, 지터/손실 레이더, DNS 벤치마크, Traceroute
├── history_db.py            # SQLite 기반 일일/시간대별 트래픽 히스토리 로깅 DB
├── autostart_manager.py     # Windows 시작프로그램(Registry) 등록/해제 관리
├── run.bat                  # [원클릭 실행] 무콘솔 백그라운드 실행 및 디버그 모드 지원 스크립트
├── static/                  # Cyberpunk Dark UI 프론트엔드 (HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/                   # 자동화 단위 테스트 스위트 (35개 테스트 100% 통과)
│   ├── test_elevation_flow.py      # 시작 시 UAC 승격 및 유저 모드 선택 안내창 테스트
│   ├── test_download_detection.py  # LDPlayer VMDK 제외 및 병렬 다운로더 캡처 테스트
│   ├── test_v3_suite.py            # 종합 진단 도구 및 엔드포인트 테스트
│   ├── test_server_api.py          # 서버 REST API 테스트
│   ├── test_qos_manager.py         # QoS NetQos 및 TCP ACK 페이싱 산출 테스트
│   └── test_history_db.py          # SQLite 영속화 및 샘플 정리 테스트
├── build_exe.py             # PyInstaller 기반 Standalone EXE 빌드 스크립트
└── PROJECT_CONTEXT.md       # 다중 PC 연속성 AI 마스터 컨텍스트
```

---

## 🛠️ 실행 및 사용 방법

### 1. 원클릭 실행 (권장)
프로젝트 폴더에서 **`run.bat`**를 더블 클릭하여 실행합니다.
- 콘솔 창 없이 백그라운드에서 깔끔하게 시작되며, UAC 관리자 승격 창이 자동으로 팝업됩니다.
- 디버그 모드(콘솔 로그 동시 출력) 실행 시:
  ```powershell
  .\run.bat --debug
  ```

### 2. 소스 코드 직접 실행
```powershell
python main_desktop.py
```

### 3. 단위 테스트 실행
```powershell
python -m unittest discover -s tests -v
```
*(35개 전체 테스트가 100% 통과해야 합니다)*

### 4. 독립 실행형 단독 EXE 빌드 (요청 시에만)
```powershell
python build_exe.py
```
빌드 완료 후 `dist/NetworkSentinelApp.exe`로 생성됩니다.
