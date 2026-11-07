<#
.SYNOPSIS
    Antigravity Master Template 동기화 스크립트
.DESCRIPTION
    현재 또는 대상 프로젝트에 .antigravity 마스터 템플릿(규칙, 스킬, 하네스 엔진)을
    심볼릭 링크(또는 복사)하여 모든 프로젝트에서 즉시 동일한 개발 파이프라인을 사용하도록 설정합니다.
.EXAMPLE
    .\sync-template.ps1 -TargetPath "C:\temp\py\AI_Meeting_Pro"
#>

param (
    [string]$TargetPath = (Get-Location).Path,
    [switch]$CopyInsteadOfLink
)

$MasterPath = "c:\temp\py\.antigravity"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Antigravity Master Template Sync Utility" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Master Path : $MasterPath"
Write-Host "Target Path : $TargetPath"

if (-not (Test-Path $TargetPath)) {
    Write-Error "대상 디렉터리가 존재하지 않습니다: $TargetPath"
    exit 1
}

# 1. Antigravity 표준 .agents 디렉터리 준비
$TargetAgentsDir = Join-Path $TargetPath ".agents"
if (-not (Test-Path $TargetAgentsDir)) {
    New-Item -ItemType Directory -Path $TargetAgentsDir -Force | Out-Null
    Write-Host "[+] .agents 디렉터리 생성됨: $TargetAgentsDir" -ForegroundColor Green
}

# 2. skills 링크/복사
$TargetSkillsDir = Join-Path $TargetAgentsDir "skills"
$MasterSkillsDir = Join-Path $MasterPath "skills"
if (Test-Path $MasterSkillsDir) {
    if (Test-Path $TargetSkillsDir) {
        Remove-Item -Recurse -Force $TargetSkillsDir
    }
    if ($CopyInsteadOfLink) {
        Copy-Item -Recurse -Force $MasterSkillsDir $TargetSkillsDir
        Write-Host "[+] skills 폴더 복사 완료" -ForegroundColor Green
    } else {
        New-Item -ItemType SymbolicLink -Path $TargetSkillsDir -Target $MasterSkillsDir -Force | Out-Null
        Write-Host "[+] skills 심볼릭 링크 생성 완료 -> $MasterSkillsDir" -ForegroundColor Green
    }
}

# 3. GEMINI.md 최상위 규칙 링크/복사
$TargetGeminiFile = Join-Path $TargetPath "GEMINI.md"
$MasterGeminiFile = Join-Path $MasterPath "GEMINI.md"
if (Test-Path $MasterGeminiFile) {
    if (-not (Test-Path $TargetGeminiFile)) {
        if ($CopyInsteadOfLink) {
            Copy-Item -Force $MasterGeminiFile $TargetGeminiFile
            Write-Host "[+] GEMINI.md 복사 완료" -ForegroundColor Green
        } else {
            New-Item -ItemType HardLink -Path $TargetGeminiFile -Target $MasterGeminiFile -Force | Out-Null
            Write-Host "[+] GEMINI.md 링크 생성 완료" -ForegroundColor Green
        }
    } else {
        Write-Host "[!] GEMINI.md 파일이 이미 존재합니다. (건너뜀)" -ForegroundColor Yellow
    }
}

# 4. harness.py 링크/복사
$TargetHarnessFile = Join-Path $TargetPath "harness.py"
$MasterHarnessFile = Join-Path $MasterPath "harness.py"
if (Test-Path $MasterHarnessFile) {
    if (-not (Test-Path $TargetHarnessFile)) {
        Copy-Item -Force $MasterHarnessFile $TargetHarnessFile
        Write-Host "[+] harness.py 배포 완료" -ForegroundColor Green
    }
}

# 5. PROJECT_CONTEXT.md 초기화 (미존재 시)
$TargetContextFile = Join-Path $TargetPath "PROJECT_CONTEXT.md"
$MasterTemplateFile = Join-Path $MasterPath "PROJECT_CONTEXT_TEMPLATE.md"
if ((-not (Test-Path $TargetContextFile)) -and (Test-Path $MasterTemplateFile)) {
    Copy-Item -Force $MasterTemplateFile $TargetContextFile
    Write-Host "[+] PROJECT_CONTEXT.md 템플릿 배포 완료" -ForegroundColor Green
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "동기화가 성공적으로 완료되었습니다!" -ForegroundColor Cyan
Write-Host "이제 해당 프로젝트에서 Antigravity 7단계 파이프라인과 5-Tier 하네스가 활성화됩니다."
