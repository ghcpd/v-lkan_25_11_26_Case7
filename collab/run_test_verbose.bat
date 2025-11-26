@echo off
REM Verbose test run generating JUnit XML and HTML report using venv
REM Usage: run_test_verbose.bat "D:\package\venv310\Scripts\python.exe" (optional)

SET PYTHON=%~1
if "%PYTHON%"=="" set PYTHON=python

"%PYTHON%" -m venv .venv
call .venv\Scripts\activate
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install pytest-html
.venv\Scripts\python.exe -m pytest -vv --junitxml=pytest-report.xml --html=pytest-report.html --self-contained-html --tb=short
pause
