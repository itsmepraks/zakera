#!/bin/bash

# Zakera Setup Script
echo "🚀 Setting up Zakera AI Chat Agent..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python dependencies installed"

# Setup configuration
if [ ! -f config/.env ]; then
    echo "⚙️ Creating configuration file..."
    cp config/.env.example config/.env
    echo "⚠️  Please edit config/.env with your API keys"
else
    echo "✅ Configuration file already exists"
fi

# Create data directory
mkdir -p data
echo "✅ Data directory created"

# Frontend setup
echo "📦 Setting up frontend..."
cd src/frontend

if command -v npm &> /dev/null; then
    echo "📥 Installing frontend dependencies..."
    npm install
    echo "✅ Frontend dependencies installed"
else
    echo "⚠️  npm not found. Please install Node.js to setup the frontend."
fi

cd ../..

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config/.env with your API keys"
echo "2. Run 'python -m uvicorn src.api.main:app --reload' to start the backend"
echo "3. Run 'cd src/frontend && npm run dev' to start the frontend"
echo ""
echo "📚 Check the documentation in docs/ for more information"
