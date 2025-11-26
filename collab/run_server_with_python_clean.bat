@echo off
REM Clean Start server using the specified python executable (path to python.exe)
REM Usage: run_server_with_python_clean.bat "D:\package\venv310\Scripts\python.exe"

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

if not exist .venv (
  echo Creating venv using %PYTHON%
  "%PYTHON%" -m venv .venv || (
    echo Failed to create venv; ensure Python is functional and try again.
    exit /b 1
  )
  call .venv\Scripts\activate
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)

echo Starting server using the venv python
.venv\Scripts\python.exe server.py
pause

