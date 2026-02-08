@echo off
REM === 1609 Manager Build Script ===
REM Builds to dist/ and preserves "1609 settings" folder

cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Build with PyInstaller
REM --distpath: output directory for the exe
REM --workpath: build temp files
REM --noconfirm: overwrite without asking
REM --clean: clean PyInstaller cache before building

pyinstaller --noconfirm --clean --distpath=dist --workpath=build\onefile_build onefile_build.spec

echo.
echo Build complete! Output: dist\1609Manager.exe
pause
