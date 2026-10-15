$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder 'Start_AGY_Bridge_and_Telegram_Bot.lnk'

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Removing Auto-Start from Windows Startup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "[SUCCESS] Auto-start shortcut removed:" -ForegroundColor Green
    Write-Host "  $shortcutPath" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Auto-start shortcut was not found in Startup folder." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Auto-start has been disabled." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
