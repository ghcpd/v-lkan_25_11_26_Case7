#!/bin/bash

echo "=========================================="
echo "Collaborative Document Editor Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, removing..."
    rm -rf venv
fi

python3 -m venv venv
echo "Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""

# Create data directory
echo "Creating data directory..."
mkdir -p data/logs
echo "Data directory created"
echo ""

# Run tests to verify setup
echo "Running verification tests..."
echo "Note: This will start the server in the background"
echo ""

python -m pytest test_collaboration.py -v --tb=short -k "test_create_document_api"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "To run the application:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Run server: python app.py"
    echo "  3. Open browser: http://localhost:5000"
    echo ""
    echo "To run tests:"
    echo "  ./run_test.sh"
    echo ""
else
    echo ""
    echo "Setup completed but verification test failed"
    echo "You may still be able to run the application manually"
fi
