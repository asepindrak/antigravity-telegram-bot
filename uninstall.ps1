# ==============================================================================
# Antigravity Telegram Bot - Uninstaller (Windows PowerShell)
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Uninstalling Antigravity Telegram Bot" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Stop all services
Write-Host "[1/3] Stopping running processes..." -ForegroundColor Yellow
$bridgeConn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($bridgeConn) {
    foreach ($c in $bridgeConn) {
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  ✓ AGY Bridge stopped." -ForegroundColor Green
}

$bots = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*telegram_bot.py*" }
if ($bots) {
    foreach ($b in $bots) {
        Stop-Process -Id $b.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  ✓ Telegram Bot stopped." -ForegroundColor Green
}

# 2. Remove Startup shortcuts
Write-Host ""
Write-Host "[2/3] Removing from Windows Startup..." -ForegroundColor Yellow
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcut1 = Join-Path $startupFolder 'Start_Antigravity_Telegram_Bot.lnk'
$shortcut2 = Join-Path $startupFolder 'Start_AGY_Bridge_and_Telegram_Bot.lnk'

if (Test-Path $shortcut1) {
    Remove-Item -Path $shortcut1 -Force
    Write-Host "  ✓ Removed: $shortcut1" -ForegroundColor Green
}
if (Test-Path $shortcut2) {
    Remove-Item -Path $shortcut2 -Force
    Write-Host "  ✓ Removed: $shortcut2" -ForegroundColor Green
}

# 3. Check ~/.antigravity-telegram-bot folder
Write-Host ""
Write-Host "[3/3] Checking standalone install directory..." -ForegroundColor Yellow
$standaloneDir = Join-Path $env:USERPROFILE ".antigravity-telegram-bot"
if (Test-Path $standaloneDir) {
    Remove-Item -Path $standaloneDir -Recurse -Force
    Write-Host "  ✓ Removed standalone directory: $standaloneDir" -ForegroundColor Green
} else {
    Write-Host "  ✓ No standalone installation directory found in $standaloneDir." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Uninstallation Complete!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
