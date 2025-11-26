# PowerShell start server using specified Python executable
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
.venv\Scripts\python.exe server.py
