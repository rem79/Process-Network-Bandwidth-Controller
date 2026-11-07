---
name: windows-gui-launcher
description: >-
  Standardizes Windows Native Desktop GUI development (CustomTkinter, Tkinter, PyQt)
  and generates the smart no-console one-click batch launcher (run.bat) with pythonw.exe,
  crash_log.txt redirection, --debug mode, and CP949/UTF-8 safe ASCII console output.
  Activate this skill when creating or updating Python desktop applications or batch/PowerShell scripts on Windows.
---

# Windows Native Desktop GUI & Smart No-Console Launcher Standard

이 스킬은 Windows 환경에서 **브라우저/웹 서버 없는 네이티브 데스크톱 GUI 애플리케이션**을 구축하고, 검은 콘솔 창 없이 깔끔하게 실행되는 **`run.bat` 스마트 런처** 및 **인코딩 안전 스크립트**를 작성하기 위한 표준 가이드입니다.

---

## 1. Native Desktop GUI Architecture Principles

1. **Web UI 기본 채택 금지**: 사용자가 명시적으로 웹 서버(FastAPI, Flask, Streamlit 등)를 요청하지 않는 한 항상 **`CustomTkinter`** 또는 **`Tkinter`** 기반의 독립 윈도우 앱으로 구현합니다.
2. **반응형 비동기 UI 처리**: 무거운 파일 I/O, 네트워크 요청, 스크래핑 작업은 반드시 `threading.Thread(..., daemon=True)` 및 `queue.Queue` / `.after()`로 분리하여 GUI 프리징(`응답 없음`)을 방지합니다.
3. **고해상도 DPI 대응 및 깔끔한 종료**: Windows 배율 환경을 고려하고 윈도우 닫기(`WM_DELETE_WINDOW`) 시 백그라운드 스레드가 안전하게 정리되도록 구성합니다.

---

## 2. Standard Smart No-Console Launcher (`run.bat`)

모든 프로젝트 루트에 배치하는 `run.bat` 표준 템플릿입니다.
- **인코딩 주의**: `cmd.exe`(CP949)에서 한글 깨짐 및 문법 에러를 원천 차단하기 위해 **`run.bat` 내부는 반드시 순수 영문(ASCII)과 CRLF 줄바꿈으로만 작성**합니다.
- 일반 더블 클릭 시 `pythonw.exe`로 콘솔 창 없이 즉시 기동하며, 예외 발생 시 `crash_log.txt`에 기록합니다.
- `run.bat --debug` 또는 `run.bat -d` 실행 시 콘솔 창을 유지하며 실시간 에러를 확인할 수 있습니다.

```bat
@echo off
setlocal
cd /d "%~dp0"

set "PY_BIN="
set "PYW_BIN="
if exist ".venv\Scripts\pythonw.exe" (
    set "PY_BIN=.venv\Scripts\python.exe"
    set "PYW_BIN=.venv\Scripts\pythonw.exe"
) else if exist "venv\Scripts\pythonw.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
    set "PYW_BIN=venv\Scripts\pythonw.exe"
) else (
    set "PY_BIN=python"
    set "PYW_BIN=pythonw"
)

if "%~1"=="--debug" goto :debug_mode
if "%~1"=="-d" goto :debug_mode

if exist "main.py" (
    start "" "%PYW_BIN%" main.py %* 2> crash_log.txt
) else if exist "app.py" (
    start "" "%PYW_BIN%" app.py %* 2> crash_log.txt
) else (
    "%PY_BIN%" harness.py
    pause
)
exit /b 0

:debug_mode
echo [DEBUG MODE] Running with console output...
if exist "main.py" (
    "%PY_BIN%" main.py %*
) else if exist "app.py" (
    "%PY_BIN%" app.py %*
) else (
    "%PY_BIN%" harness.py
)
if errorlevel 1 pause
exit /b %errorlevel%
```
