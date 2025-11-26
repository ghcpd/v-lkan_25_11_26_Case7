@echo off
REM Windows-friendly setup script for dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Setup complete.
