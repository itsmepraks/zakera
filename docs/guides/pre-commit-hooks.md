# Pre-commit Hooks Guide

## Overview

Pre-commit hooks automatically check and fix code quality issues before commits are made.

## Installation

### 1. Install pre-commit

```bash
# Using pip
pip install pre-commit

# Using homebrew (macOS)
brew install pre-commit

# Using apt (Ubuntu/Debian)
sudo apt install pre-commit
```

### 2. Install hooks in repository

```bash
# Install git hooks
pre-commit install

# Install commit-msg hook (optional)
pre-commit install --hook-type commit-msg
```

## Usage

### Automatic Execution

Hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
# Hooks run automatically
```

### Manual Execution

```bash
# Run on staged files only
pre-commit run

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Skip hooks for a commit (use sparingly!)
git commit -m "message" --no-verify
```

## Configured Hooks

### Code Formatting

#### Black (Python)
- **Purpose**: Automatic Python code formatting
- **Config**: 88 character line length
- **Auto-fix**: Yes

```bash
# Run manually
black src/ tests/
```

#### Prettier (JS/TS)
- **Purpose**: JavaScript/TypeScript formatting
- **Config**: 100 character line length, single quotes
- **Auto-fix**: Yes

```bash
# Run manually
npx prettier --write "src/frontend/**/*.{js,jsx,ts,tsx}"
```

### Import Sorting

#### isort (Python)
- **Purpose**: Sort and organize imports
- **Config**: Compatible with Black
- **Auto-fix**: Yes

```bash
# Run manually
isort src/ tests/
```

### Linting

#### Flake8 (Python)
- **Purpose**: Style guide enforcement
- **Config**: PEP 8 compliance with Black compatibility
- **Auto-fix**: No (manual fixes required)

**Common Issues:**
```python
# E501: Line too long (fixed by Black)
# W503: Line break before binary operator (ignored)
# E203: Whitespace before ':' (Black style, ignored)
```

#### ESLint (JavaScript/TypeScript)
- **Purpose**: JavaScript linting
- **Auto-fix**: Yes (most issues)

### Type Checking

#### mypy (Python)
- **Purpose**: Static type checking
- **Config**: Ignore missing imports
- **Auto-fix**: No

**Example:**
```python
# Add type hints to pass mypy
def process_data(data: dict) -> str:
    return str(data)
```

### Security

#### Bandit (Python)
- **Purpose**: Security vulnerability detection
- **Config**: Configured via pyproject.toml
- **Auto-fix**: No

#### detect-secrets
- **Purpose**: Prevent committing secrets
- **Config**: Uses baseline file
- **Auto-fix**: No

**If secrets are detected:**
```bash
# Add to baseline if false positive
detect-secrets scan --baseline .secrets.baseline
```

### File Checks

- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with newline
- **check-yaml**: Validate YAML syntax
- **check-json**: Validate JSON syntax
- **check-merge-conflict**: Detect merge conflict markers
- **check-added-large-files**: Prevent large files (>500KB)
- **debug-statements**: Detect debug statements (print, debugger)

### Dockerfile

#### Hadolint
- **Purpose**: Dockerfile linting
- **Auto-fix**: No

### Shell Scripts

#### ShellCheck
- **Purpose**: Shell script linting
- **Auto-fix**: No

## Troubleshooting

### Hooks Fail

**Problem**: Pre-commit hooks fail

**Solutions**:
```bash
# Update hooks to latest version
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install

# Run with verbose output
pre-commit run --verbose --all-files
```

### Slow Execution

**Problem**: Hooks take too long

**Solutions**:
```bash
# Run only on changed files
pre-commit run --files $(git diff --name-only HEAD)

# Skip expensive hooks for quick commits
SKIP=mypy git commit -m "Quick fix"
```

### Hook Conflicts

**Problem**: Hook changes conflict with manual changes

**Solution**:
```bash
# Let hooks fix files, then stage and commit
pre-commit run --all-files
git add .
git commit -m "message"
```

## Configuration

### Skipping Specific Hooks

```bash
# Skip specific hook for one commit
SKIP=flake8 git commit -m "message"

# Skip multiple hooks
SKIP=flake8,mypy git commit -m "message"
```

### Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Update specific hook
pre-commit autoupdate --repo https://github.com/psf/black
```

### Adding Custom Hooks

Edit `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: custom-check
        name: Custom Check
        entry: ./scripts/custom-check.sh
        language: system
        pass_filenames: false
```

## Best Practices

1. **Run before pushing**: `pre-commit run --all-files`
2. **Keep hooks updated**: `pre-commit autoupdate` monthly
3. **Fix issues locally**: Don't bypass hooks
4. **Add type hints**: Helps mypy and improves code quality
5. **Review hook output**: Understand what changed
6. **Stage incrementally**: Easier to review hook changes

## Integration with CI/CD

Hooks also run in CI/CD pipeline:

```yaml
# .github/workflows/ci.yml
- name: Run pre-commit
  run: pre-commit run --all-files
```

## Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Supported Hooks](https://pre-commit.com/hooks.html)
- [Writing Custom Hooks](https://pre-commit.com/#creating-new-hooks)

---

**Last Updated**: February 2026
