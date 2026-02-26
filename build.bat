@echo off
REM === 1609 Manager Build Script ===

cd /d "%~dp0"

echo [1/3] Closing running instances...
taskkill /F /IM 1609Manager.exe /T 2>nul >nul

echo [2/3] Activating environment...
call .venv\Scripts\activate.bat 2>nul
if %errorlevel% neq 0 (
    echo [!] Warning: Could not activate .venv. Using global environment.
)

echo [3/3] Building executable...
pyinstaller --noconfirm --clean --distpath=dist --workpath=build\onefile_build onefile_build.spec >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   BUILD SUCCESSFUL!
    echo   Output: dist\1609Manager.exe
    echo ========================================
    echo Closing in 5 seconds...
    ping -n 6 127.0.0.1 > nul
) else (
    echo.
    echo [!] BUILD FAILED! Check build\onefile_build for logs.
    pause
)
exit
