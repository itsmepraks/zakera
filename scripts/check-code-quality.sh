#!/bin/bash
# Code quality check script

set -e

echo "===================================="
echo "Code Quality Checks"
echo "===================================="
echo ""

# Formatting check
echo "[1/5] Checking code formatting (Black)..."
black --check src/ tests/ || {
    echo "❌ Code formatting issues found"
    echo "Run 'black src/ tests/' to fix"
    exit 1
}
echo "✓ Code formatting OK"
echo ""

# Import sorting check
echo "[2/5] Checking import sorting (isort)..."
isort --check-only src/ tests/ || {
    echo "❌ Import sorting issues found"
    echo "Run 'isort src/ tests/' to fix"
    exit 1
}
echo "✓ Import sorting OK"
echo ""

# Linting
echo "[3/5] Running linter (Flake8)..."
flake8 src/ tests/ || {
    echo "❌ Linting issues found"
    exit 1
}
echo "✓ Linting OK"
echo ""

# Type checking
echo "[4/5] Running type checker (mypy)..."
mypy src/ || {
    echo "❌ Type checking issues found"
    exit 1
}
echo "✓ Type checking OK"
echo ""

# Security check
echo "[5/5] Running security check (Bandit)..."
bandit -r src/ -c pyproject.toml || {
    echo "❌ Security issues found"
    exit 1
}
echo "✓ Security check OK"
echo ""

echo "===================================="
echo "All Checks Passed! ✅"
echo "===================================="
