@echo off
cd /d "%~dp0"

:: Auto-detect Python executable (prioritize actual installation over WindowsApps dummy)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" setup.py %*
    goto :eof
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" setup.py %*
    goto :eof
) else if exist "C:\Python311\python.exe" (
    "C:\Python311\python.exe" setup.py %*
    goto :eof
) else if exist "C:\Python312\python.exe" (
    "C:\Python312\python.exe" setup.py %*
    goto :eof
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py setup.py %*
    goto :eof
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python setup.py %*
    goto :eof
)

echo [ERROR] Python not found. Please install Python 3.8+ to continue.
pause
