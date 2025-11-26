@echo off
REM Test runner for Windows

echo ==========================================
echo Running Collaborative Editor Tests
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Error: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Create test report directory
set REPORT_DIR=test_reports
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set REPORT_FILE=%REPORT_DIR%\test_report_%TIMESTAMP%.txt

if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"

echo Running tests and generating report...
echo Report will be saved to: %REPORT_FILE%
echo.

REM Run tests with detailed output
python -m pytest test_collaboration.py -v --tb=short > "%REPORT_FILE%" 2>&1

set TEST_EXIT_CODE=%errorlevel%

REM Display the report
type "%REPORT_FILE%"

echo.
echo ==========================================
if %TEST_EXIT_CODE% equ 0 (
    echo All tests passed! ✓
) else (
    echo Some tests failed ✗
)
echo ==========================================
echo.
echo Test report saved to: %REPORT_FILE%
echo.

REM Generate HTML summary
echo Generating test summary...
python -c "import re; from datetime import datetime; content = open('%REPORT_FILE%', 'r').read(); passed = len(re.findall(r'PASSED', content)); failed = len(re.findall(r'FAILED', content)); errors = len(re.findall(r'ERROR', content)); total = passed + failed + errors; html = f'''<!DOCTYPE html><html><head><title>Test Report</title><style>body{{font-family:Arial;margin:40px;background:#f5f5f5}}.container{{background:white;padding:30px;border-radius:8px}}.summary{{display:flex;gap:20px;margin:20px 0}}.stat{{flex:1;padding:20px;border-radius:6px;text-align:center}}.stat h2{{margin:0;font-size:36px}}.stat p{{margin:10px 0 0 0;color:#666}}.passed{{background:#d4edda;color:#155724}}.failed{{background:#f8d7da;color:#721c24}}.total{{background:#d1ecf1;color:#0c5460}}pre{{background:#f8f9fa;padding:15px;border-radius:4px;overflow-x:auto}}</style></head><body><div class=\"container\"><h1>Test Report</h1><p>Generated: {datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S')}</p><div class=\"summary\"><div class=\"stat total\"><h2>{total}</h2><p>Total Tests</p></div><div class=\"stat passed\"><h2>{passed}</h2><p>Passed</p></div><div class=\"stat failed\"><h2>{failed+errors}</h2><p>Failed</p></div></div><h2>Test Output</h2><pre>{content}</pre></div></body></html>'''; open('%REPORT_DIR%/test_summary_%TIMESTAMP%.html', 'w').write(html)"

echo HTML summary generated: %REPORT_DIR%\test_summary_%TIMESTAMP%.html
echo.

pause
exit /b %TEST_EXIT_CODE%
