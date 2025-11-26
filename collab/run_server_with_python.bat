@echo off
REM Start server using the specified python executable (path to python.exe)
REM Usage: run_server_with_python.bat "D:\package\venv310\Scripts\python.exe"

if "%~1"=="" (
  set "PYTHON=python"
) else (
  set "PYTHON=%~1"
  if not exist "%PYTHON%" (
    echo ERROR: Python executable not found at %PYTHON%
    exit /b 1
  )
)

if not exist .venv (
  "%PYTHON%" -m venv .venv
  call .venv\Scripts\activate
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)

.venv\Scripts\python.exe server.py
pause

@echo off
REM Start server using the specified python executable (path to python.exe)
REM Usage: run_server_with_python.bat "D:\package\venv310\Scripts\python.exe"

if "%~1"=="" (
  set PYTHON=python
) else (
  set PYTHON=%~1
)












pause
nREM Start server using venv python to ensure packages come from virtual env
n.venv\Scripts\python.exe server.py)  call .venv\Scripts\activate) else (  "%PYTHON%" -m pip install -r requirements.txt  "%PYTHON%" -m pip install --upgrade pip  call .venv\Scripts\activate  "%PYTHON%" -m venv .venvif not exist .venv (nREM Create venv if missing and install dependencies once