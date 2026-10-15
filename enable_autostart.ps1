$ErrorActionPreference = "Stop"

$workspaceDir = $PSScriptRoot
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder 'Start_AGY_Bridge_and_Telegram_Bot.lnk'
$targetVbs = Join-Path $workspaceDir 'start_services_silent.vbs'

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Setting up Auto-Start on Windows Startup" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = "wscript.exe"
$sc.Arguments = "`"$targetVbs`""
$sc.WorkingDirectory = $workspaceDir
$sc.Description = "Auto-start AGY OpenAI Bridge and Telegram Bot on Windows Login"
$sc.IconLocation = "shell32.dll,43"
$sc.Save()

Write-Host "[SUCCESS] Auto-start shortcut created in Windows Startup folder:" -ForegroundColor Green
Write-Host "  $shortcutPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Target Script:" -ForegroundColor Gray
Write-Host "  $targetVbs" -ForegroundColor Gray
Write-Host ""
Write-Host "Services will now start silently in the background whenever you sign in." -ForegroundColor Green
Write-Host "You can also manage this entry in Windows Task Manager -> Startup Apps tab." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
