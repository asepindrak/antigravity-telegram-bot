$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder 'Start_Antigravity_Telegram_Bot.lnk'
$oldShortcutPath = Join-Path $startupFolder 'Start_AGY_Bridge_and_Telegram_Bot.lnk'

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Removing Auto-Start from Windows Startup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$removed = $false
if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "[SUCCESS] Auto-start shortcut removed: $shortcutPath" -ForegroundColor Green
    $removed = $true
}

if (Test-Path $oldShortcutPath) {
    Remove-Item -Path $oldShortcutPath -Force
    Write-Host "[SUCCESS] Legacy shortcut removed: $oldShortcutPath" -ForegroundColor Green
    $removed = $true
}

if (-not $removed) {
    Write-Host "[INFO] Auto-start shortcut was not found in Startup folder." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Auto-start has been disabled." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
