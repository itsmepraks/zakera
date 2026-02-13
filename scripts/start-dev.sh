#!/bin/bash

# Zakera Development Startup Script
# This script starts all necessary services for development

set -e

echo "🚀 Starting Zakera AI Chat Agent - Development Environment"
echo "========================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Checking dependencies..."
if [ ! -f "venv/.dependencies_installed" ] || [ requirements.txt -nt venv/.dependencies_installed ]; then
    echo -e "${YELLOW}📥 Installing/updating dependencies...${NC}"
    pip install -q -r requirements.txt
    touch venv/.dependencies_installed
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies up to date${NC}"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs
echo -e "${GREEN}✅ Directories ready${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  Please edit .env file with your configuration!${NC}"
    echo -e "${YELLOW}   Run: nano .env${NC}"
fi

# Check if Ollama is running (optional)
echo "🦙 Checking Ollama status..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
    
    # List installed models
    echo "📋 Installed Ollama models:"
    curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for model in data.get('models', []):
    print(f'   - {model["name"]}')
" 2>/dev/null || echo "   (none)"
else
    echo -e "${YELLOW}⚠️  Ollama not running (local models won't work)${NC}"
    echo -e "${YELLOW}   To install: make ollama-install${NC}"
    echo -e "${YELLOW}   To start: ollama serve${NC}"
fi

# Start monitoring stack
echo ""
echo "📊 Starting monitoring stack..."
if command -v docker-compose &> /dev/null; then
    cd monitoring
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Monitoring stack already running${NC}"
    else
        echo "   Starting Prometheus, Grafana, and AlertManager..."
        docker-compose up -d > /dev/null 2>&1
        echo -e "${GREEN}✅ Monitoring stack started${NC}"
    fi
    cd ..
else
    echo -e "${YELLOW}⚠️  Docker Compose not found (monitoring unavailable)${NC}"
fi

# Display access information
echo ""
echo "🎉 Zakera Development Environment Ready!"
echo "========================================================"
echo ""
echo "🌐 Access Points:"
echo -e "   ${GREEN}API Server:${NC}      http://localhost:8000"
echo -e "   ${GREEN}API Docs:${NC}        http://localhost:8000/api/docs"
echo -e "   ${GREEN}Grafana:${NC}         http://localhost:3001 (admin/admin)"
echo -e "   ${GREEN}Prometheus:${NC}      http://localhost:9090"
echo -e "   ${GREEN}AlertManager:${NC}    http://localhost:9093"
echo ""
echo "📊 Monitoring Commands:"
echo "   make health          - Check application health"
echo "   make metrics         - View current metrics"
echo "   make alerts          - View active alerts"
echo "   make performance     - View performance stats"
echo ""
echo "🤖 Model Commands:"
echo "   make models-list     - List available models"
echo "   make models-health   - Check provider health"
echo ""
echo "🧪 Development Commands:"
echo "   make test            - Run tests"
echo "   make format          - Format code"
echo "   make lint            - Run linters"
echo ""
echo "🚀 Starting API server..."
echo "========================================================"
echo ""

# Start the API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
