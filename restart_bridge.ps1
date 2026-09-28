# Script to restart AGY OpenAI Bridge Server
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   Restarting AGY OpenAI Bridge Server (Port 8001)   " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Checking and stopping existing process on port 8001..." -ForegroundColor Yellow
$conns = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($conn in $conns) {
        Write-Host "Stopping process PID $($conn.OwningProcess)..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "No process found on port 8001." -ForegroundColor DarkGray
}

Start-Sleep -Seconds 2

Write-Host "[2/3] Launching AGY OpenAI Bridge Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m uvicorn openai_agy_bridge:app --host 0.0.0.0 --port 8001" -WindowStyle Hidden -WorkingDirectory "C:\Users\sangp\learn-with-runa"

Start-Sleep -Seconds 3

Write-Host "[3/3] Verifying server status..." -ForegroundColor Yellow
try {
    $res = Invoke-RestMethod -Uri "http://localhost:8001/" -TimeoutSec 5
    Write-Host ""
    Write-Host "=====================================================" -ForegroundColor Green
    Write-Host " AGY OpenAI Bridge Server Restarted Successfully!     " -ForegroundColor Green
    Write-Host " Base URL    : http://localhost:8001                  " -ForegroundColor Green
    Write-Host " Status      : $($res.status)                         " -ForegroundColor Green
    Write-Host " DB Logging  : $($res.db_logging)                     " -ForegroundColor Green
    Write-Host "=====================================================" -ForegroundColor Green
} catch {
    Write-Host "Server process launched. Please check http://localhost:8001" -ForegroundColor Yellow
}
