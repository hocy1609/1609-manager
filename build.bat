@echo off
REM === 1609 Manager Build Script ===

:: --- Auto-Elevation to Administrator ---
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Requesting Administrator privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)
:: ---------------------------------------

cd /d "%~dp0"

echo [1/3] Closing running instances...
taskkill /F /IM 1609Manager.exe /T 2>nul >nul

echo [2/3] Checking environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Warning: 'python' not found in PATH. Trying 'py' launcher...
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo [3/3] Building executable...
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --distpath=dist --workpath=build\onefile_build onefile_build.spec >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   BUILD SUCCESSFUL!
    echo   Output: dist\1609Manager.exe
    echo ========================================
) else (
    echo.
    echo [!] BUILD FAILED! Check build\onefile_build for logs.
    pause
)
exit
