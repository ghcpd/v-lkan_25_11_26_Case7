#!/bin/bash
# Test runner script for Lightweight Collaboration Platform
# Runs complete test suite with report generation

set -e

echo "🧪 Lightweight Collaboration Platform - Test Suite"
echo "===================================================="

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated. Attempting activation..."
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    elif [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
    else
        echo "❌ Could not find virtual environment. Run setup.sh first."
        exit 1
    fi
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"

# Clean previous test data
echo ""
echo "🧹 Cleaning test data..."
rm -rf data/documents/* data/logs/* 2>/dev/null || true
mkdir -p data/documents data/logs
echo "✓ Test data cleaned"

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
echo "================================================"

python test_suite.py

# Check if test report was generated
if [[ -f "test_report.json" ]]; then
    echo ""
    echo "📊 Test Report:"
    echo "================================================"
    cat test_report.json | python -m json.tool
fi

# Run server health check (optional)
if command -v curl &> /dev/null; then
    echo ""
    echo "🔍 Running server connectivity check..."
    timeout 5 python app.py &
    SERVER_PID=$!
    sleep 2
    
    if curl -s http://localhost:5000 > /dev/null; then
        echo "✓ Server is responding"
    else
        echo "⚠️  Server not responding (expected if not fully started)"
    fi
    
    kill $SERVER_PID 2>/dev/null || true
fi

echo ""
echo "✅ Test suite completed!"
echo ""
echo "📝 To view detailed results, check: test_report.json"
echo "🚀 To run the server: python app.py"
