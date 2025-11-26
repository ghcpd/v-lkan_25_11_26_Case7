@echo off
setlocal enabledelayedexpansion

REM Usage:
REM   run_test_windows.bat "D:\package\venv310\Scripts\python.exe"
REM If you omit the python path it will try to use the current "python" in PATH.

if "%1"=="" (
  set "PY=%~dp0\.venv\Scripts\python.exe"
  REM if .venv exists and has python, prefer that. Otherwise just use python from PATH
  if exist "%~dp0\.venv\Scripts\python.exe" (
    set "PY=%~dp0\.venv\Scripts\python.exe"
  ) else (
    set "PY=python"
  )
) else (
  set "PY=%~1"
)

echo Using Python: %PY%

REM Create a local venv with the specified Python interpreter if .venv doesn't exist
if not exist "%~dp0\.venv" (
  echo Creating venv at .venv using %PY%
  "%PY%" -m venv "%~dp0\.venv"
)

REM Install dependencies in the .venv
echo Activating venv and installing dependencies...
call "%~dp0\.venv\Scripts\activate.bat"
pip install --upgrade pip
pip install -r "%~dp0\requirements.txt"

echo Running pytest
pytest -q

endlocal
