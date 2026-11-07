param(
    [string]$MasterPath = "",
    [string]$RootDir = ""
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ([string]::IsNullOrWhiteSpace($MasterPath)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $MasterPath = $PSScriptRoot
    } else {
        $MasterPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
}
$MasterPath = (Get-Item -LiteralPath $MasterPath).FullName

if ([string]::IsNullOrWhiteSpace($RootDir)) {
    $RootDir = (Get-Item -LiteralPath $MasterPath).Parent.FullName
}
$RootDir = (Get-Item -LiteralPath $RootDir).FullName

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Antigravity Projects Multi-Sync & Cleanup Utility" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Master Path : $MasterPath"
Write-Host "Target Root : $RootDir"
Write-Host "----------------------------------------------------------"

if (-not (Test-Path -LiteralPath $MasterPath)) {
    Write-Error "Cannot find master directory: $MasterPath"
    exit 1
}

$MasterGEMINI = Join-Path $MasterPath "GEMINI.md"
$MasterHarnessPy = Join-Path $MasterPath "harness.py"
$MasterHarnessJson = Join-Path $MasterPath "harness.json"
$MasterContextTpl = Join-Path $MasterPath "PROJECT_CONTEXT_TEMPLATE.md"

$projects = Get-ChildItem -LiteralPath $RootDir -Directory | Where-Object { $_.FullName -ne $MasterPath }

$successCount = 0
$skipCount = 0

foreach ($proj in $projects) {
    $projPath = $proj.FullName
    $projName = $proj.Name

    Write-Host ""
    Write-Host ">> [$projName] Synchronizing..." -ForegroundColor Yellow

    try {
        # 1. 기존 .antigravity 폴더 제거 및 최신 마스터 복사
        $targetAntigravityDir = Join-Path $projPath ".antigravity"
        if (Test-Path -LiteralPath $targetAntigravityDir) {
            Remove-Item -LiteralPath $targetAntigravityDir -Recurse -Force
            Write-Host "   [-] Removed old $projName\.antigravity" -ForegroundColor DarkGray
        }

        New-Item -ItemType Directory -Path $targetAntigravityDir -Force | Out-Null
        Copy-Item -Path (Join-Path $MasterPath "*") -Destination $targetAntigravityDir -Recurse -Force -Exclude "__pycache__", "*.pyc", ".git"
        Write-Host "   [+] Copied latest .antigravity" -ForegroundColor Green

        # 2. GEMINI.md 최신화
        $targetGEMINI = Join-Path $projPath "GEMINI.md"
        if ($targetGEMINI -ne $MasterGEMINI) {
            Copy-Item -LiteralPath $MasterGEMINI -Destination $targetGEMINI -Force
            Write-Host "   [+] Updated GEMINI.md" -ForegroundColor Green
        }

        # 3. harness.py 및 harness.json 배포
        $targetHarnessPy = Join-Path $projPath "harness.py"
        if ($targetHarnessPy -ne $MasterHarnessPy) {
            Copy-Item -LiteralPath $MasterHarnessPy -Destination $targetHarnessPy -Force
        }
        
        $targetHarnessJson = Join-Path $projPath "harness.json"
        if (-not (Test-Path -LiteralPath $targetHarnessJson)) {
            Copy-Item -LiteralPath $MasterHarnessJson -Destination $targetHarnessJson -Force
            Write-Host "   [+] Created default harness.json" -ForegroundColor Green
        }

        # 4. PROJECT_CONTEXT.md (미존재 시 생성)
        $targetContext = Join-Path $projPath "PROJECT_CONTEXT.md"
        if (-not (Test-Path -LiteralPath $targetContext)) {
            Copy-Item -LiteralPath $MasterContextTpl -Destination $targetContext -Force
            Write-Host "   [+] Created PROJECT_CONTEXT.md" -ForegroundColor Green
        }

        # 5. run.bat 스마트 무콘솔 런처 생성
        $targetRunBat = Join-Path $projPath "run.bat"
        if (-not (Test-Path -LiteralPath $targetRunBat)) {
            $batLines = @(
                "@echo off",
                "setlocal",
                "cd /d `"%~dp0`"",
                "",
                "set `"PY_BIN=`"",
                "set `"PYW_BIN=`"",
                "if exist `"venv\Scripts\pythonw.exe`" (",
                "    set `"PY_BIN=venv\Scripts\python.exe`"",
                "    set `"PYW_BIN=venv\Scripts\pythonw.exe`"",
                ") else (",
                "    set `"PY_BIN=python`"",
                "    set `"PYW_BIN=pythonw`"",
                ")",
                "",
                "if `"%1`"==`"--debug`" (",
                "    echo [DEBUG MODE] Running with console output...",
                "    if exist main.py (`"%PY_BIN%`" main.py %*) else if exist app.py (`"%PY_BIN%`" app.py %*) else (`"%PY_BIN%`" -m unittest discover)",
                "    if errorlevel 1 pause",
                "    exit /b",
                ")",
                "if `"%1`"==`"-d`" (",
                "    echo [DEBUG MODE] Running with console output...",
                "    if exist main.py (`"%PY_BIN%`" main.py %*) else if exist app.py (`"%PY_BIN%`" app.py %*) else (`"%PY_BIN%`" -m unittest discover)",
                "    if errorlevel 1 pause",
                "    exit /b",
                ")",
                "",
                "if exist main.py (",
                "    start `"`" `"%PYW_BIN%`" main.py %* 2> crash_log.txt",
                ") else if exist app.py (",
                "    start `"`" `"%PYW_BIN%`" app.py %* 2> crash_log.txt",
                ") else (",
                "    `"%PY_BIN%`" -m unittest discover",
                "    pause",
                ")",
                "exit"
            )
            [System.IO.File]::WriteAllLines($targetRunBat, $batLines, [System.Text.Encoding]::ASCII)
            Write-Host "   [+] Created smart run.bat launcher" -ForegroundColor Green
        }

        $successCount++
    } catch {
        Write-Error "   [X] Error during $projName sync: $_"
        $skipCount++
    }
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Sync Complete!" -ForegroundColor Cyan
Write-Host "  - Success: $successCount project(s)" -ForegroundColor Green
if ($skipCount -gt 0) {
    Write-Host "  - Failed : $skipCount project(s)" -ForegroundColor Red
}
Write-Host "==========================================================" -ForegroundColor Cyan