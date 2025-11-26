#!/bin/bash

echo "=========================================="
echo "Running Collaborative Editor Tests"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Create test report directory
REPORT_DIR="test_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.txt"

mkdir -p "$REPORT_DIR"

echo "Running tests and generating report..."
echo "Report will be saved to: $REPORT_FILE"
echo ""

# Run tests with detailed output
python -m pytest test_collaboration.py \
    -v \
    --tb=short \
    --color=yes \
    | tee "$REPORT_FILE"

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed! ✓"
else
    echo "Some tests failed ✗"
fi
echo "=========================================="
echo ""
echo "Test report saved to: $REPORT_FILE"
echo ""

# Generate summary
echo "Generating test summary..."
python3 << EOF
import re
import os
from datetime import datetime

report_file = "$REPORT_FILE"
summary_file = "$REPORT_DIR/test_summary_$TIMESTAMP.html"

# Read test report
with open(report_file, 'r') as f:
    content = f.read()

# Extract test results
passed = len(re.findall(r'PASSED', content))
failed = len(re.findall(r'FAILED', content))
errors = len(re.findall(r'ERROR', content))
total = passed + failed + errors

# Generate HTML summary
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ flex: 1; padding: 20px; border-radius: 6px; text-align: center; }}
        .stat h2 {{ margin: 0; font-size: 36px; }}
        .stat p {{ margin: 10px 0 0 0; color: #666; }}
        .passed {{ background: #d4edda; color: #155724; }}
        .failed {{ background: #f8d7da; color: #721c24; }}
        .total {{ background: #d1ecf1; color: #0c5460; }}
        .timestamp {{ color: #666; font-size: 14px; margin-top: 20px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Collaborative Editor Test Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="stat total">
                <h2>{total}</h2>
                <p>Total Tests</p>
            </div>
            <div class="stat passed">
                <h2>{passed}</h2>
                <p>Passed</p>
            </div>
            <div class="stat failed">
                <h2>{failed + errors}</h2>
                <p>Failed</p>
            </div>
        </div>
        
        <h2>Test Categories</h2>
        <ul>
            <li>Document Creation & Retrieval</li>
            <li>Real-time Collaboration</li>
            <li>Persistent Storage & Edit Logging</li>
            <li>Conflict Detection & Visualization</li>
            <li>Multi-Document Support</li>
            <li>Version History</li>
            <li>Last-Write-Wins Strategy</li>
        </ul>
        
        <h2>Full Test Output</h2>
        <pre>{content}</pre>
    </div>
</body>
</html>
"""

with open(summary_file, 'w') as f:
    f.write(html)

print(f"HTML summary generated: {summary_file}")
EOF

echo ""
echo "Test summary: $REPORT_DIR/test_summary_$TIMESTAMP.html"
echo ""

exit $TEST_EXIT_CODE
