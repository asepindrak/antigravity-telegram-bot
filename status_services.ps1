Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Checking Status: AGY Bridge & Telegram Bot" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check AGY Bridge
Write-Host "[AGY OpenAI Bridge Server]" -ForegroundColor Yellow
$bridgeConn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($bridgeConn) {
    $pidVal = $bridgeConn[0].OwningProcess
    Write-Host "  Process  : RUNNING (PID: $pidVal on Port 8001)" -ForegroundColor Green
    try {
        $res = Invoke-RestMethod -Uri "http://localhost:8001/" -TimeoutSec 3
        Write-Host "  Health   : OK ($($res.status)) | DB Logging: $($res.db_logging)" -ForegroundColor Green
    } catch {
        Write-Host "  Health   : Warning (Server warming up or slow to respond)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Process  : STOPPED" -ForegroundColor Red
}

Write-Host ""

# Check PC Music Player Server
Write-Host "[PC YouTube Music Player Server]" -ForegroundColor Yellow
$musicConn = Get-NetTCPConnection -LocalPort 8002 -ErrorAction SilentlyContinue
if ($musicConn) {
    $mPid = $musicConn[0].OwningProcess
    Write-Host "  Process  : RUNNING (PID: $mPid on Port 8002)" -ForegroundColor Green
    try {
        $mRes = Invoke-RestMethod -Uri "http://localhost:8002/api/status" -TimeoutSec 3
        $trackTitle = if ($mRes.current_track) { "$($mRes.current_track.title) - $($mRes.current_track.artist)" } else { "Idle" }
        Write-Host "  Health   : OK | Mode: $($mRes.playbackState) | Track: $trackTitle" -ForegroundColor Green
    } catch {
        Write-Host "  Health   : Warning (Server warming up)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Process  : STOPPED" -ForegroundColor Red
}

Write-Host ""

# Check Telegram Bot
Write-Host "[Telegram Bot]" -ForegroundColor Yellow
$bots = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*telegram_bot.py*" }
if ($bots) {
    foreach ($b in $bots) {
        Write-Host "  Process  : RUNNING (PID: $($b.ProcessId))" -ForegroundColor Green
    }
} else {
    Write-Host "  Process  : STOPPED" -ForegroundColor Red
}

Write-Host ""

# Check Auto-start Status
Write-Host "[Windows Auto-Start Status]" -ForegroundColor Yellow
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder 'Start_Antigravity_Telegram_Bot.lnk'
$oldShortcutPath = Join-Path $startupFolder 'Start_AGY_Bridge_and_Telegram_Bot.lnk'
if ((Test-Path $shortcutPath) -or (Test-Path $oldShortcutPath)) {
    Write-Host "  Auto-Start : ENABLED" -ForegroundColor Green
    $activeSc = if (Test-Path $shortcutPath) { $shortcutPath } else { $oldShortcutPath }
    Write-Host "  Shortcut   : $activeSc" -ForegroundColor Gray
} else {
    Write-Host "  Auto-Start : DISABLED (Run enable_autostart.bat to enable)" -ForegroundColor Gray
}

Write-Host "========================================================" -ForegroundColor Cyan
