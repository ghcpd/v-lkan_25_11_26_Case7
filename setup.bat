@echo off
REM Collaborative Document Editor Setup Script for Windows

echo ==========================================
echo Collaborative Document Editor Setup
echo ==========================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists, removing...
    rmdir /s /q venv
)

python -m venv venv
echo Virtual environment created
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Create data directory
echo Creating data directory...
if not exist "data\logs" mkdir data\logs
echo Data directory created
echo.

REM Run verification test
echo Running verification tests...
echo Note: This will start the server in the background
echo.

python -m pytest test_collaboration.py -v --tb=short -k "test_create_document_api"

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo Setup completed successfully!
    echo ==========================================
    echo.
    echo To run the application:
    echo   1. Activate virtual environment: venv\Scripts\activate
    echo   2. Run server: python app.py
    echo   3. Open browser: http://localhost:5000
    echo.
    echo To run tests:
    echo   run_test.bat
    echo.
) else (
    echo.
    echo Setup completed but verification test failed
    echo You may still be able to run the application manually
)

pause
