# ==============================================================================
# Antigravity Telegram Bot - Multiplatform One-Line Installer (Windows PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "      🤖 Antigravity Telegram Bot - 1-Line Windows Auto Installer   " -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# Helper to read host input safely
function Get-UserInput([string]$prompt, [string]$defaultValue = "") {
    Write-Host -NoNewline "$prompt " -ForegroundColor Yellow
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) {
        return $defaultValue
    }
    return $val.Trim()
}

# 1. Check System Prerequisites
Write-Host "[1/6] Checking system dependencies..." -ForegroundColor Cyan

# Check Git
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Host "[ERROR] Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Git for Windows (https://git-scm.com/) and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Git: $(git --version)" -ForegroundColor Green

# Check Python
$py = "python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $py = "py"
    } elseif (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe") {
        $py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    } elseif (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe") {
        $py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    } else {
        Write-Host "[ERROR] Python 3.8+ was not found on your system." -ForegroundColor Red
        Write-Host "Please install Python from https://www.python.org/ or Microsoft Store." -ForegroundColor Yellow
        exit 1
    }
}
$pyVer = & $py --version 2>&1
Write-Host "  ✓ Python: $pyVer ($py)" -ForegroundColor Green

# Check Antigravity CLI
if (Get-Command agy -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Antigravity CLI (agy): Found in PATH" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ Antigravity CLI ('agy') was not found in PATH." -ForegroundColor Yellow
    Write-Host "     Ensure Google Antigravity is installed and agy is added to your PATH." -ForegroundColor DarkGray
}

# 2. Target Directory & Clone/Update
$defaultInstallDir = Join-Path $env:USERPROFILE ".antigravity-telegram-bot"
$repoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { "https://github.com/asepindrak/antigravity-telegram-bot.git" }
$fallbackRepoUrl = "https://github.com/asepindrak/learn-with-runa.git"

if ((Test-Path "telegram_bot.py") -and (Test-Path "setup.py")) {
    $targetDir = (Get-Location).Path
    Write-Host "[2/6] Running inside repository folder: $targetDir" -ForegroundColor Cyan
} else {
    $targetDir = $defaultInstallDir
    Write-Host "[2/6] Setting up installation in: $targetDir" -ForegroundColor Cyan
    if (Test-Path (Join-Path $targetDir ".git")) {
        Write-Host "Updating existing installation..." -ForegroundColor Yellow
        Set-Location $targetDir
        git pull | Out-Null
    } else {
        Write-Host "Cloning repository..." -ForegroundColor Yellow
        try {
            git clone $repoUrl $targetDir
        } catch {
            Write-Host "Primary repo not found, falling back to $fallbackRepoUrl..." -ForegroundColor Yellow
            git clone $fallbackRepoUrl $targetDir
        }
        Set-Location $targetDir
    }
}

# 3. Install Python Dependencies & Node packages
Write-Host "[3/6] Installing dependencies..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt --quiet --disable-pip-version-check
Write-Host "  ✓ Python packages installed successfully." -ForegroundColor Green

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "  Installing Node.js dependencies for PC Music Player..." -ForegroundColor Cyan
    npm install --silent 2>$null
    Write-Host "  ✓ Node.js packages (ytmusic-api) installed." -ForegroundColor Green
}

# 4. Interactive Configuration Wizard
Write-Host ""
Write-Host "[4/6] Configuration Setup Wizard" -ForegroundColor Cyan
Write-Host "(Press Enter to skip any setting and configure later using: python setup.py)" -ForegroundColor DarkGray
Write-Host ""

$botToken = Get-UserInput "Enter Telegram Bot Token from @BotFather:" ""
$telegramUid = Get-UserInput "Enter your Telegram User ID from @userinfobot:" ""

Write-Host ""
Write-Host "Select an AI Persona:" -ForegroundColor Cyan
Write-Host "  [1] Runa Shirakawa       - Warm, friendly, supportive companion & coder (Default)"
Write-Host "  [2] Senior Engineer      - Direct, pragmatic, expert software architect"
Write-Host "  [3] JARVIS AI            - Witty, cybernetic, intelligent assistant"
Write-Host "  [4] Custom / Keep        - Use existing persona.md"
$personaChoice = Get-UserInput "Choose Persona (1-4) [default: 1]:" "1"

# Copy chosen persona
if ($personaChoice -eq "1" -and (Test-Path "personas\runa.md")) {
    Copy-Item "personas\runa.md" "persona.md" -Force
} elseif ($personaChoice -eq "2" -and (Test-Path "personas\engineer.md")) {
    Copy-Item "personas\engineer.md" "persona.md" -Force
} elseif ($personaChoice -eq "3" -and (Test-Path "personas\jarvis.md")) {
    Copy-Item "personas\jarvis.md" "persona.md" -Force
}

# Configure .env
$envFilePath = Join-Path $targetDir ".env"
if (-not (Test-Path $envFilePath)) {
    $envContent = @"
# Antigravity Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=$botToken
TELEGRAM_ALLOWED_USER_ID=$telegramUid
AGY_BRIDGE_HOST=0.0.0.0
AGY_BRIDGE_PORT=8001
AGY_BRIDGE_API_KEY=
DEFAULT_PROJECT_NAME=general
"@
    Set-Content -Path $envFilePath -Value $envContent -Encoding UTF8
} else {
    $existing = Get-Content $envFilePath -Raw
    if ($botToken) {
        $existing = $existing -replace "TELEGRAM_BOT_TOKEN=.*", "TELEGRAM_BOT_TOKEN=$botToken"
    }
    if ($telegramUid) {
        $existing = $existing -replace "TELEGRAM_ALLOWED_USER_ID=.*", "TELEGRAM_ALLOWED_USER_ID=$telegramUid"
    }
    Set-Content -Path $envFilePath -Value $existing -Encoding UTF8
}

# Initialize clean projects.json if not present
$projectsFilePath = Join-Path $targetDir "projects.json"
if (-not (Test-Path $projectsFilePath)) {
    $userHomeEscaped = $env:USERPROFILE.Replace("\", "\\")
    $initialProjects = @"
{
  "general": "$userHomeEscaped"
}
"@
    Set-Content -Path $projectsFilePath -Value $initialProjects -Encoding UTF8
}

# 5. Configure Auto-Start on Windows Startup
Write-Host ""
Write-Host "[5/6] Auto-Start Configuration" -ForegroundColor Cyan
$enableStart = Get-UserInput "Enable auto-run on Windows startup? (Y/n) [default: Y]:" "y"

if ($enableStart -match "^[Yy]") {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $targetDir "enable_autostart.ps1")
}

# 6. Start Services Silently in Background
Write-Host ""
Write-Host "[6/6] Launching services in background..." -ForegroundColor Cyan
$silentVbs = Join-Path $targetDir "start_services_silent.vbs"
if (Test-Path $silentVbs) {
    Start-Process "wscript.exe" -ArgumentList "`"$silentVbs`"" -WorkingDirectory $targetDir
}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  🎉 Antigravity Telegram Bot Successfully Installed & Running!    " -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "📁 Installed Directory : $targetDir" -ForegroundColor Yellow
Write-Host "⚙️ Management CLI       : python setup.py (or setup.bat)" -ForegroundColor Yellow
Write-Host "📋 Status Check        : status_services.bat (or status_services.ps1)" -ForegroundColor Yellow
Write-Host "⏹️ Stop Services       : stop_services.bat (or stop_services.ps1)" -ForegroundColor Yellow
Write-Host "🔄 Restart Services    : restart_bridge.bat" -ForegroundColor Yellow
Write-Host "====================================================================" -ForegroundColor Green
Write-Host ""
