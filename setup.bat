@echo off
REM Setup script for Lightweight Collaboration Platform (Windows)
REM Creates virtual environment, installs dependencies, and initializes directories

setlocal enabledelayedexpansion

echo.
echo ^| ^| __ ___
echo ^| \/ / __^|
echo ^|    \__ \
echo ^|    ^|___/
echo.
echo Lightweight Collaboration Platform - Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed. Please install Python 3.8 or higher.
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo [OK] Python %python_version% detected

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
echo [OK] Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

REM Install dependencies
echo.
echo Installing dependencies...
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo [OK] Dependencies installed

REM Create data directories
echo.
echo Creating data directories...
if not exist "data\documents" mkdir data\documents
if not exist "data\logs" mkdir data\logs
if not exist "templates" mkdir templates
if not exist "static" mkdir static
echo [OK] Data directories created

REM Verify structure
echo.
echo Project structure:
dir /s /b

echo.
echo [DONE] Setup complete!
echo.
echo Next steps:
echo   1. Activate environment: venv\Scripts\activate.bat
echo   2. Run the server: python app.py
echo   3. Open browser: http://localhost:5000
echo   4. Run tests: python test_suite.py
echo.
pause
