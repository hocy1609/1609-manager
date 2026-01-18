@echo off
echo === 1609 Manager Build Script ===
echo.

REM Clean previous builds
echo Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "release" rmdir /s /q release
del /q *.spec.bak 2>nul
echo Done cleaning.
echo.

REM Build
echo Building 1609Manager.exe...
python -m PyInstaller --clean --noconfirm onefile_build.spec
if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)
echo.

REM Create release folder
echo Creating release folder...
mkdir release 2>nul
copy dist\1609Manager.exe release\ >nul
copy nwn_settings.example.json release\ >nul
copy logo.ico release\ >nul
echo.

echo === Build Complete ===
echo Output: release\1609Manager.exe
echo.
dir release
pause
