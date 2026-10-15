Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Stopping AGY OpenAI Bridge & Telegram Bot" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Stop AGY Bridge
Write-Host "[1/2] Stopping AGY Bridge (Port 8001)..." -ForegroundColor Yellow
$bridgeConn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($bridgeConn) {
    foreach ($c in $bridgeConn) {
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  -> Successfully stopped AGY Bridge process." -ForegroundColor Green
} else {
    Write-Host "  -> AGY Bridge is not running." -ForegroundColor Gray
}

Write-Host ""

# 2. Stop Telegram Bot
Write-Host "[2/2] Stopping Telegram Bot..." -ForegroundColor Yellow
$bots = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*telegram_bot.py*" }
if ($bots) {
    foreach ($b in $bots) {
        Stop-Process -Id $b.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  -> Successfully stopped Telegram Bot process." -ForegroundColor Green
} else {
    Write-Host "  -> Telegram Bot is not running." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   All services stopped!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
