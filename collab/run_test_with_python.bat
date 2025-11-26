@echo off
REM Run tests with a specified python executable (path to python.exe) on Windows
REM Usage: run_test_with_python.bat "D:\package\venv310\Scripts\python.exe"

if "%~1"=="" (
  echo Please provide a Python executable path as the first argument, e.g. "D:\package\venv310\Scripts\python.exe"
  echo Using default python from PATH...
  set "PYTHON=python"
) else (
  set "PYTHON=%~1"
  @echo off
  REM Run tests with a specified python executable (path to python.exe) on Windows
  REM Usage: run_test_with_python.bat "D:\package\venv310\Scripts\python.exe"

  if "%~1"=="" (
    echo Please provide a Python executable path as the first argument, e.g. "D:\package\venv310\Scripts\python.exe"
    echo Using default python from PATH...
    set "PYTHON=python"
  ) else (
    set "PYTHON=%~1"
    if not exist "%PYTHON%" (
      echo ERROR: Python executable not found at %PYTHON%
      exit /b 1
    )
  )

  "%PYTHON%" -m venv .venv
  call .venv\Scripts\activate
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  .venv\Scripts\python.exe -m pytest -q
  pause