@echo off
setlocal
cd /d "%~dp0"

set "PY_BIN="
set "PYW_BIN="
if exist "venv\Scripts\pythonw.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
    set "PYW_BIN=venv\Scripts\pythonw.exe"
) else (
    set "PY_BIN=python"
    set "PYW_BIN=pythonw"
)

if "%1"=="--debug" (
    echo [DEBUG MODE] Running with console output...
    if exist main_desktop.py ("%PY_BIN%" main_desktop.py %*) else if exist main.py ("%PY_BIN%" main.py %*) else if exist app.py ("%PY_BIN%" app.py %*) else ("%PY_BIN%" -m unittest discover)
    if errorlevel 1 pause
    exit /b
)
if "%1"=="-d" (
    echo [DEBUG MODE] Running with console output...
    if exist main_desktop.py ("%PY_BIN%" main_desktop.py %*) else if exist main.py ("%PY_BIN%" main.py %*) else if exist app.py ("%PY_BIN%" app.py %*) else ("%PY_BIN%" -m unittest discover)
    if errorlevel 1 pause
    exit /b
)

if exist main_desktop.py (
    start "" "%PYW_BIN%" main_desktop.py %* 2> crash_log.txt
) else if exist main.py (
    start "" "%PYW_BIN%" main.py %* 2> crash_log.txt
) else if exist app.py (
    start "" "%PYW_BIN%" app.py %* 2> crash_log.txt
) else (
    "%PY_BIN%" -m unittest discover
    pause
)
exit
