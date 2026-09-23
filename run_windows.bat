@echo off
REM BioVault startup script for Windows.
REM Double-click this file (or run it from a terminal) to set up and
REM launch BioVault. Safe to run multiple times.

echo ============================================
echo  BioVault - DNA Digital Data Storage Platform
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this computer.
    echo Please install Python 3.9 or newer from https://www.python.org/downloads/
    echo and make sure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

if not exist venv (
    echo Creating a virtual environment in .\venv ...
    python -m venv venv
)

echo Installing/updating dependencies from requirements.txt ...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

echo.
echo Starting BioVault. A browser tab should open automatically.
echo Press CTRL+C in this window to stop the app.
echo.
streamlit run app.py

pause
