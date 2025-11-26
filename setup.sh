#!/bin/bash
# Setup script for Lightweight Collaboration Platform
# Creates virtual environment, installs dependencies, and initializes directories

set -e

echo "🚀 Lightweight Collaboration Platform - Setup"
echo "================================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $python_version detected"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Virtual environment created"

# Determine activation command based on OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create data directories
echo ""
echo "📁 Creating data directories..."
mkdir -p data/documents
mkdir -p data/logs
mkdir -p templates
mkdir -p static
echo "✓ Data directories created"

# Verify structure
echo ""
echo "📋 Project structure:"
ls -la

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate environment: source venv/bin/activate (or venv\\Scripts\\activate on Windows)"
echo "  2. Run the server: python app.py"
echo "  3. Open browser: http://localhost:5000"
echo "  4. Run tests: python -m pytest test_suite.py -v (or python test_suite.py)"
