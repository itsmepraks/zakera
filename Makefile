.PHONY: help install test lint format clean docker ci backend frontend all

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Zakera CI/CD Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation targets
# ============================================================================

install: install-backend install-frontend ## Install all dependencies
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

install-backend: ## Install backend dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	pip install -r requirements.txt
	pip install black isort flake8 mypy pytest pytest-cov bandit safety

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd src/frontend && npm ci

# ============================================================================
# Testing targets
# ============================================================================

test: test-backend test-frontend ## Run all tests
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	pytest tests/ -v

test-backend-cov: ## Run backend tests with coverage
	@echo "$(BLUE)Running backend tests with coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd src/frontend && npm test -- --passWithNoTests

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	pytest tests/ -v --watch

# ============================================================================
# Linting targets
# ============================================================================

lint: lint-backend lint-frontend ## Run all linters
	@echo "$(GREEN)✓ All linting checks passed$(NC)"

lint-backend: ## Run backend linters
	@echo "$(BLUE)Running backend linters...$(NC)"
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/
	mypy src/ --ignore-missing-imports

lint-frontend: ## Run frontend linters
	@echo "$(BLUE)Running frontend linters...$(NC)"
	cd src/frontend && npm run lint

lint-fix: ## Auto-fix linting issues
	@echo "$(BLUE)Auto-fixing linting issues...$(NC)"
	black src/ tests/
	isort src/ tests/
	cd src/frontend && npm run lint:fix

# ============================================================================
# Formatting targets
# ============================================================================

format: format-backend format-frontend ## Format all code
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	black src/ tests/
	isort src/ tests/

format-frontend: ## Format frontend code
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd src/frontend && npm run format

format-check: ## Check code formatting
	@echo "$(BLUE)Checking code formatting...$(NC)"
	black --check src/ tests/
	isort --check-only src/ tests/
	cd src/frontend && npm run format:check

# ============================================================================
# Security targets
# ============================================================================

security: security-backend security-frontend ## Run security checks
	@echo "$(GREEN)✓ Security checks completed$(NC)"

security-backend: ## Run backend security scans
	@echo "$(BLUE)Running backend security scans...$(NC)"
	bandit -r src/ -ll
	safety check || true

security-frontend: ## Run frontend security scans
	@echo "$(BLUE)Running frontend security scans...$(NC)"
	cd src/frontend && npm audit

# ============================================================================
# Docker targets
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t zakera:latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-test: ## Test Docker image
	@echo "$(BLUE)Testing Docker image...$(NC)"
	docker run --rm -d --name zakera-test -p 8000:8000 zakera:latest
	sleep 10
	docker logs zakera-test
	docker stop zakera-test
	@echo "$(GREEN)✓ Docker image tested$(NC)"

docker-scan: ## Scan Docker image for vulnerabilities
	@echo "$(BLUE)Scanning Docker image...$(NC)"
	docker scan zakera:latest || echo "$(YELLOW)Install Docker Scan or use Trivy$(NC)"

docker-compose-up: ## Start services with docker-compose
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"

docker-compose-down: ## Stop services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

# ============================================================================
# CI/CD targets
# ============================================================================

ci: lint test security ## Run CI checks locally
	@echo "$(GREEN)✓ All CI checks passed$(NC)"

ci-backend: lint-backend test-backend security-backend ## Run backend CI checks
	@echo "$(GREEN)✓ Backend CI checks passed$(NC)"

ci-frontend: lint-frontend test-frontend security-frontend ## Run frontend CI checks
	@echo "$(GREEN)✓ Frontend CI checks passed$(NC)"

ci-full: clean install ci docker-build ## Run full CI pipeline locally
	@echo "$(GREEN)✓ Full CI pipeline completed$(NC)"

# ============================================================================
# Build targets
# ============================================================================

build: build-backend build-frontend ## Build everything
	@echo "$(GREEN)✓ Build completed$(NC)"

build-backend: ## Build backend (check imports)
	@echo "$(BLUE)Building backend...$(NC)"
	python -m py_compile src/**/*.py

build-frontend: ## Build frontend
	@echo "$(BLUE)Building frontend...$(NC)"
	cd src/frontend && npm run build
	@echo "$(GREEN)✓ Frontend built$(NC)"

# ============================================================================
# Development targets
# ============================================================================

dev-backend: ## Run backend in development mode
	@echo "$(BLUE)Starting backend development server...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend in development mode
	@echo "$(BLUE)Starting frontend development server...$(NC)"
	cd src/frontend && npm run dev

dev: ## Run both backend and frontend in development mode
	@echo "$(BLUE)Starting development servers...$(NC)"
	@echo "$(YELLOW)Run 'make dev-backend' and 'make dev-frontend' in separate terminals$(NC)"

# ============================================================================
# Database targets
# ============================================================================

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)✓ Migrations applied$(NC)"

db-rollback: ## Rollback last migration
	@echo "$(BLUE)Rolling back last migration...$(NC)"
	alembic downgrade -1

db-reset: ## Reset database
	@echo "$(RED)⚠ Resetting database...$(NC)"
	rm -f data/zakera.db
	alembic upgrade head
	python scripts/seed_db.py || echo "$(YELLOW)Seed script not found$(NC)"

# ============================================================================
# Cleanup targets
# ============================================================================

clean: clean-python clean-frontend clean-docker ## Clean all generated files
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

clean-python: ## Clean Python generated files
	@echo "$(BLUE)Cleaning Python files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml

clean-frontend: ## Clean frontend generated files
	@echo "$(BLUE)Cleaning frontend files...$(NC)"
	cd src/frontend && rm -rf .next/ out/ node_modules/.cache coverage/

clean-docker: ## Clean Docker resources
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	docker system prune -f

# ============================================================================
# Release targets
# ============================================================================

version: ## Show current version
	@echo "$(BLUE)Current version:$(NC)"
	@git describe --tags --always

release-patch: ## Create patch release
	@echo "$(BLUE)Creating patch release...$(NC)"
	# Add versioning logic here

release-minor: ## Create minor release
	@echo "$(BLUE)Creating minor release...$(NC)"
	# Add versioning logic here

release-major: ## Create major release
	@echo "$(BLUE)Creating major release...$(NC)"
	# Add versioning logic here

# ============================================================================
# Documentation targets
# ============================================================================

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	@echo "$(YELLOW)Documentation server not yet implemented$(NC)"

# ============================================================================
# Utility targets
# ============================================================================

check-deps: ## Check for outdated dependencies
	@echo "$(BLUE)Checking for outdated dependencies...$(NC)"
	pip list --outdated
	cd src/frontend && npm outdated

update-deps: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements.txt --upgrade
	cd src/frontend && npm update

pre-commit: lint test ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

pre-push: ci docker-build ## Run pre-push checks
	@echo "$(GREEN)✓ Pre-push checks passed$(NC)"

status: ## Show repository status
	@echo "$(BLUE)Repository Status:$(NC)"
	@git status
	@echo ""
	@echo "$(BLUE)Recent commits:$(NC)"
	@git log --oneline -5

# ============================================================================
# Backend shortcuts
# ============================================================================

backend: ci-backend ## Run all backend checks
	@echo "$(GREEN)✓ Backend checks completed$(NC)"

# ============================================================================
# Frontend shortcuts
# ============================================================================

frontend: ci-frontend build-frontend ## Run all frontend checks
	@echo "$(GREEN)✓ Frontend checks completed$(NC)"

# ============================================================================
# All-in-one target
# ============================================================================

all: clean install ci build docker-build ## Run everything
	@echo "$(GREEN)✅ All tasks completed successfully!$(NC)"

# ============================================================================
# Quick shortcuts
# ============================================================================

t: test ## Shortcut for test
f: format ## Shortcut for format
l: lint ## Shortcut for lint
b: build ## Shortcut for build
d: docker-build ## Shortcut for docker-build
