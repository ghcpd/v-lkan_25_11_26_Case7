# PowerShell script for running tests with a specified Python executable
# Usage: ./run_test_with_python.ps1 -PythonPath 'D:\package\venv310\Scripts\python.exe'
param(
    [string]$PythonPath = "python"
)
if(-not (Test-Path -Path $PythonPath)){
    Write-Host "Python executable not found: $PythonPath"
    exit 1
}
& $PythonPath -m venv .venv
. .venv\Scripts\Activate.ps1
& $PythonPath -m pip install --upgrade pip
& $PythonPath -m pip install -r requirements.txt
& $PythonPath -m pytest -q
