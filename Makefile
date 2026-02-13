# Zakefile - Build automation for Zakera AI Chat Agent

.PHONY: help install dev test lint format clean docker monitoring

# Default target
help:
	@echo "Zakera AI Chat Agent - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install          Install dependencies"
	@echo "  make dev              Run development server"
	@echo "  make test             Run tests"
	@echo "  make test-cov         Run tests with coverage"
	@echo "  make lint             Run linters"
	@echo "  make format           Format code"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitoring-start Start monitoring stack (Prometheus, Grafana, AlertManager)"
	@echo "  make monitoring-stop  Stop monitoring stack"
	@echo "  make monitoring-logs  View monitoring logs"
	@echo "  make metrics          View current metrics"
	@echo "  make health           Check application health"
	@echo "  make alerts           View active alerts"
	@echo ""
	@echo "Models:"
	@echo "  make ollama-install   Install and setup Ollama"
	@echo "  make ollama-pull      Pull recommended Ollama models"
	@echo "  make models-list      List available models"
	@echo "  make models-health    Check model provider health"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-run       Run Docker container"
	@echo "  make docker-stop      Stop Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Clean temporary files"
	@echo "  make clean-all        Clean everything including data"

# =============================================================================
# Development
# =============================================================================

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	cd src/frontend && npm install
	@echo "✅ Dependencies installed"

dev:
	@echo "🚀 Starting development server..."
	python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "🧪 Running tests..."
	pytest tests/ -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "📊 Coverage report: htmlcov/index.html"

lint:
	@echo "🔍 Running linters..."
	flake8 src/
	mypy src/
	@echo "✅ Linting complete"

format:
	@echo "✨ Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "✅ Formatting complete"

# =============================================================================
# Monitoring
# =============================================================================

monitoring-start:
	@echo "📊 Starting monitoring stack..."
	cd monitoring && docker-compose up -d
	@echo "✅ Monitoring stack started:"
	@echo "   - Prometheus: http://localhost:9090"
	@echo "   - Grafana: http://localhost:3001 (admin/admin)"
	@echo "   - AlertManager: http://localhost:9093"

monitoring-stop:
	@echo "🛑 Stopping monitoring stack..."
	cd monitoring && docker-compose down
	@echo "✅ Monitoring stack stopped"

monitoring-logs:
	@echo "📋 Monitoring stack logs:"
	cd monitoring && docker-compose logs -f

metrics:
	@echo "📈 Current metrics:"
	curl -s http://localhost:8000/api/v1/monitoring/metrics | head -50

health:
	@echo "💚 Health check:"
	curl -s http://localhost:8000/api/v1/monitoring/health?detailed=true | jq .

alerts:
	@echo "🚨 Active alerts:"
	curl -s http://localhost:8000/api/v1/monitoring/alerts | jq .

performance:
	@echo "⚡ Performance statistics:"
	curl -s http://localhost:8000/api/v1/monitoring/performance | jq .

# =============================================================================
# Models
# =============================================================================

ollama-install:
	@echo "🦙 Installing Ollama..."
	@if command -v brew >/dev/null 2>&1; then \
		brew install ollama; \
	else \
		curl -fsSL https://ollama.ai/install.sh | sh; \
	fi
	@echo "✅ Ollama installed"
	@echo "Run 'ollama serve' to start the Ollama service"

ollama-pull:
	@echo "⬇️  Pulling recommended Ollama models..."
	ollama pull llama3:8b
	ollama pull mistral:7b
	@echo "✅ Models downloaded"

models-list:
	@echo "🤖 Available models:"
	curl -s http://localhost:8000/api/v1/models/ | jq .

models-health:
	@echo "💊 Model provider health:"
	curl -s http://localhost:8000/api/v1/models/health | jq .

# =============================================================================
# Docker
# =============================================================================

docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t zakera:latest .
	@echo "✅ Docker image built"

docker-run:
	@echo "🐳 Running Docker container..."
	docker run -d -p 8000:8000 --name zakera zakera:latest
	@echo "✅ Container started: http://localhost:8000"

docker-stop:
	@echo "🛑 Stopping Docker container..."
	docker stop zakera && docker rm zakera
	@echo "✅ Container stopped"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Cleaning all generated files..."
	rm -rf data/*.db
	rm -rf logs/*.log
	@echo "✅ Full cleanup complete"
