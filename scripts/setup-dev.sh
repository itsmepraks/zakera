#!/bin/bash
# Development environment setup script

set -e  # Exit on error

echo "===================================="
echo "Zakera Development Environment Setup"
echo "===================================="
echo ""

# Check Python version
echo "[1/8] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MINIMUM_VERSION="3.9"
if [ "$(printf '%s\n' "$MINIMUM_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$MINIMUM_VERSION" ]; then
    echo "Error: Python 3.9+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "[2/8] Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "[3/8] Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "[4/8] Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✓ Pip upgraded"
echo ""

# Install dependencies
echo "[5/8] Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Install pre-commit hooks
echo "[6/8] Installing pre-commit hooks..."
pip install pre-commit
pre-commit install
echo "✓ Pre-commit hooks installed"
echo ""

# Setup environment file
echo "[7/8] Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ .env file created from .env.example"
    echo "⚠ Please edit .env and add your API keys"
else
    echo "✓ .env file already exists"
fi
echo ""

# Initialize database
echo "[8/8] Initializing database..."
python -c "from src.database import init_db; init_db()" 2>/dev/null || true
echo "✓ Database initialized"
echo ""

echo "===================================="
echo "Setup Complete! 🎉"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run 'source .venv/bin/activate' to activate virtual environment"
echo "3. Run 'make dev' to start development server"
echo "4. Visit http://localhost:8000/api/docs for API documentation"
echo ""
echo "Useful commands:"
echo "  make dev     - Start development server"
echo "  make test    - Run tests"
echo "  make format  - Format code"
echo "  make lint    - Run linters"
echo ""
