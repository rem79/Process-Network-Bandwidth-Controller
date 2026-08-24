# Process Network Bandwidth Controller (Antigravity Sentinel v2.0)

윈도우 환경에서 실행 중인 모든 프로세스의 실시간 네트워크 트래픽(다운로드/업로드 속도 및 누적량, 소켓 연결 수)을 정밀 모니터링하고, Windows `NetQosPolicy` 엔진을 활용하여 프로세스별/전역 대역폭을 즉각 제한(QoS Throttling) 및 우선순위를 제어할 수 있는 고성능 데스크톱 컨트롤러입니다.

---

## 주요 고도화 기능 (v2.0)

1. **실시간 트래픽 텔레메트리 & 60초 챠트**
   - WebSocket 스트림을 통해 1초 단위로 시스템 전체 및 개별 프로세스 I/O 실시간 측정
   - Chart.js 기반 실시간 네트워크 속도 변화 챠트 렌더링

2. **SQLite 기반 트래픽 사용 이력 분석 (Traffic Analytics)**
   - `%APPDATA%/AntigravityNetworkSentinel/traffic_history.db`를 통해 프로세스별 트래픽 데이터 누적 기록
   - 최근 24시간 상위 대역폭 소모 앱(Top Bandwidth Consumers) 및 일별 사용 요약(Daily Data Usage Summary) 제공
   - 장기 실행 시 자동 데이터 정리(14일 단위 가비지 컬렉션)

3. **소켓 & 원격 엔드포인트 정밀 인스펙터 (Socket Inspector)**
   - 프로세스별 연결된 로컬/원격 IP 주소, 포트, 프로토콜(TCP/UDP), 연결 상태(ESTABLISHED, LISTEN 등) 실시간 확인 모달

4. **보안 및 다중 제어 정책 (Advanced QoS & Priority)**
   - PowerShell 커맨드 인젝션 방지 문자열 정제(Sanitization)
   - 일반(Normal), 우선(High, DSCP 46), 저우선(Low, DSCP 10) QoS 우선순위 정책 태깅
   - 브라우저/고대역폭/제한된 프로세스 원클릭 필터 칩 지원

5. **시스템 트레이 & 윈도우 부팅 자동 실행**
   - 닫기([X]) 버튼 클릭 시 백그라운드 시스템 트레이로 자동 최소화
   - 트레이 메뉴 및 대시보드 UI를 통한 Windows 시작 프로그램 등록/해제

---

## 프로젝트 구조

```
Process Network Bandwidth Controller/
├── main_desktop.py          # PyWebView 데스크톱 윈도우 및 시스템 트레이 관리자
├── server.py                # FastAPI 백엔드 (WebSocket 텔레메트리 & REST API)
├── qos_manager.py           # Windows NetQosPolicy QoS 대역폭 제어 엔진
├── history_db.py            # SQLite3 트래픽 이력 저장 및 통계 분석 모듈
├── autostart_manager.py     # Windows 시작 프로그램 레지스트리 관리자
├── build_exe.py             # PyInstaller 기반 Standalone EXE 빌드 스크립트
├── static/                  # Cyberpunk Dark UI 프론트엔드 (HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── tests/                   # 자동화 단위/통합 테스트 스위트
│   ├── test_history_db.py
│   ├── test_qos_manager.py
│   └── test_server_api.py
└── .antigravity/            # 7단계 자율 에이전트 파이프라인 및 실행 규칙
```

---

## 실행 및 사용 방법

### 1. 가상환경 및 의존성 설치
```powershell
pip install -r requirements.txt
```

### 2. 데스크톱 앱 실행 (관리자 권한 필수)
```powershell
python main_desktop.py
```
> 실행 시 Windows NetQosPolicy 조작을 위해 UAC 관리자 권한 요청 창이 나타납니다.

### 3. 테스트 실행
```powershell
python -m unittest discover -s tests -v
```

### 4. 독립 실행형 단독 EXE 빌드
```powershell
python build_exe.py
```
빌드 완료 후 `dist/Process Network Bandwidth Controller/` 폴더에 생성된 실행 파일(`Process Network Bandwidth Controller.exe`)을 바로 실행할 수 있습니다.

---

## REST API 스펙 요약

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/system-info` | 시스템 관리자 권한 여부, CPU/RAM, 자동시작 상태 조회 |
| `POST` | `/api/limit` | 프로세스별/전역 대역폭 제한 설정 (`target`, `app_exe`, `limit_kbps`, `priority`) |
| `DELETE` | `/api/limit/{target}` | 특정 타겟의 QoS 대역폭 제한 해제 |
| `POST` | `/api/limits/clear` | 모든 QoS 대역폭 제한 정책 일괄 제거 |
| `GET` | `/api/history/top` | 최근 N시간 기준 상위 트래픽 사용 앱 목록 조회 |
| `GET` | `/api/history/daily` | 일자별 프로세스 트래픽 누적 통계 조회 |
| `GET` | `/api/process/{pid}/connections` | 특정 PID의 활성 소켓 및 원격 IP/포트 상세 조회 |
| `WS` | `/ws/stats` | 실시간 네트워크 텔레메트리 스트리밍 (1초 주기) |
