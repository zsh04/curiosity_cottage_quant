#!/bin/bash
# Switch to Python 3.11 Environment

echo "🔄 Switching to Python 3.11..."

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install it first:"
    echo "   brew install python@3.11"
    exit 1
fi

# Create or update virtual environment with Python 3.11
echo "📦 Creating/updating virtual environment with Python 3.11..."
python3.11 -m venv .venv

echo "✅ Activating environment..."
source .venv/bin/activate

echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo ""
echo "✅ Environment ready!"
echo ""
echo "📋 To activate this environment in the future:"
echo "   source .venv/bin/activate"
echo ""
echo "🚀 To start services:"
echo "   python -m app.services.brain_service"
