@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ==========================================================
echo   Antigravity Projects Rule Sync Utility
echo ==========================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-all-projects.ps1"

echo.
echo ==========================================================
echo   All Done!
echo ==========================================================
pause