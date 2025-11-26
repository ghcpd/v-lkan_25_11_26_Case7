@echo off
REM Test runner script for Lightweight Collaboration Platform (Windows)
REM Runs complete test suite with report generation

setlocal enabledelayedexpansion

echo.
echo Testing Lightweight Collaboration Platform
echo ===========================================
echo.

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo Virtual environment not activated. Activating...
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
    ) else (
        echo ERROR: Could not find virtual environment. Run setup.bat first.
        pause
        exit /b 1
    )
)

echo [OK] Virtual environment: %VIRTUAL_ENV%

REM Clean previous test data
echo.
echo Cleaning test data...
if exist "data\documents" (
    for /f %%i in ('dir /b data\documents') do del "data\documents\%%i"
)
if exist "data\logs" (
    for /f %%i in ('dir /b data\logs') do del "data\logs\%%i"
)
echo [OK] Test data cleaned

REM Run unit tests
echo.
echo Running unit tests...
echo ===========================================
python test_suite.py

REM Check if test report was generated
if exist "test_report.json" (
    echo.
    echo Test Report:
    echo ===========================================
    type test_report.json
)

echo.
echo [DONE] Test suite completed!
echo.
echo To view detailed results, check: test_report.json
echo To run the server: python app.py
echo.
pause
