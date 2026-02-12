# CI/CD Quick Reference

A quick reference guide for common CI/CD tasks and commands.

## 🚀 Quick Commands

### Local Development

```bash
# Run all backend checks
make backend-check  # or:
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
mypy src/
pytest tests/ --cov=src

# Run all frontend checks
make frontend-check  # or:
cd src/frontend
npm run lint
npm run format:check
npm test
npm run build

# Fix formatting issues
make format  # or:
black src/ tests/
isort src/ tests/
cd src/frontend && npm run format
```

### GitHub Actions

```bash
# View workflow status
gh workflow list
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Re-run failed jobs
gh run rerun <run-id> --failed

# Watch workflow in real-time
gh run watch
```

## 📊 Pipeline Status

### Check CI Status

```bash
# Via GitHub CLI
gh workflow view ci.yml

# Via curl
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/itsmepraks/zakera/actions/workflows/ci.yml/runs
```

### Check Deployment Status

```bash
# List recent deployments
gh api repos/itsmepraks/zakera/deployments

# Check deployment status
gh api repos/itsmepraks/zakera/deployments/<deployment-id>/statuses
```

## 🔧 Troubleshooting

### Failed Tests

```bash
# Run specific test file
pytest tests/test_auth.py -v

# Run tests with debugging
pytest tests/ -v --tb=long --log-cli-level=DEBUG

# Run only failed tests
pytest --lf

# Skip slow tests
pytest -m "not slow"
```

### Linting Errors

```bash
# Auto-fix Python issues
black src/ tests/
isort src/ tests/

# Show specific flake8 errors
flake8 src/ --show-source

# Fix TypeScript issues
cd src/frontend
npm run lint:fix
```

### Docker Issues

```bash
# Build without cache
docker build --no-cache -t zakera:test .

# Check container logs
docker logs <container-id>

# Inspect running container
docker exec -it <container-id> /bin/bash

# Clean up
docker system prune -a
```

## 🔐 Secrets Management

### Add/Update Secrets

```bash
# Via GitHub CLI
gh secret set AWS_ACCESS_KEY_ID < aws_key.txt
gh secret set AWS_SECRET_ACCESS_KEY < aws_secret.txt

# List secrets
gh secret list

# Delete secret
gh secret delete SECRET_NAME
```

### Test with Secrets Locally

```bash
# Create .env file for local testing
cp .env.example .env
# Edit .env with test values

# Run with environment
export $(cat .env | xargs)
pytest tests/
```

## 📦 Deployment

### Trigger Staging Deployment

```bash
# Push to develop branch
git push origin develop

# Or trigger manually
gh workflow run cd.yml -f environment=staging
```

### Trigger Production Deployment

```bash
# Push to main branch
git push origin main

# Or trigger manually (requires approval)
gh workflow run cd.yml -f environment=production
```

### Rollback Deployment

```bash
# Via Terraform
cd terraform
terraform apply -var="image_tag=<previous-version>"

# Via AWS CLI
aws ecs update-service \
  --cluster zakera-cluster-production \
  --service zakera-service \
  --force-new-deployment
```

## 📈 Monitoring

### View CI/CD Metrics

```bash
# Workflow run duration
gh run list --workflow=ci.yml --json conclusion,updatedAt,createdAt

# Success rate
gh api repos/itsmepraks/zakera/actions/workflows/ci.yml | jq '.success_rate'
```

### Check Test Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# View coverage summary
pytest --cov=src --cov-report=term-missing
```

## 🏷️ Badges

Add these to README.md:

```markdown
![CI/CD](https://github.com/itsmepraks/zakera/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/itsmepraks/zakera/branch/main/graph/badge.svg)](https://codecov.io/gh/itsmepraks/zakera)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
[![Docker](https://img.shields.io/badge/docker-enabled-2496ED.svg?logo=docker)](https://www.docker.com/)
```

## 🛠️ Maintenance Tasks

### Update Dependencies

```bash
# Backend
pip list --outdated
pip install --upgrade package-name
pip freeze > requirements.txt

# Frontend
npm outdated
npm update
npm audit fix
```

### Cache Management

```bash
# Clear GitHub Actions cache
gh cache list
gh cache delete <cache-id>

# Clear all caches
gh cache delete --all
```

### Workflow Updates

```bash
# Validate workflow syntax
gh workflow view ci.yml

# Disable workflow
gh workflow disable ci.yml

# Enable workflow
gh workflow enable ci.yml
```

## 📝 Common Patterns

### Skip CI on Commit

```bash
git commit -m "docs: update README [skip ci]"
```

### Tag Release

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### Create Hotfix

```bash
git checkout -b hotfix/critical-bug main
# Make fixes
git commit -m "fix: critical bug"
git push origin hotfix/critical-bug
# Create PR to main
```

## 🔍 Debug Mode

### Enable Debug Logging

Add to workflow file:

```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

### Run with Verbose Output

```bash
# Pytest
pytest -vv --tb=long

# npm
npm run test -- --verbose

# Docker
docker build --progress=plain .
```

## 📞 Getting Help

```bash
# GitHub Actions documentation
open https://docs.github.com/en/actions

# View workflow file
gh workflow view ci.yml --web

# Check action logs
gh run view --log

# Open issue
gh issue create
```

## 🎯 Best Practices Checklist

- [ ] All tests pass locally before pushing
- [ ] Code is formatted (black, prettier)
- [ ] No linting errors
- [ ] Test coverage > 70%
- [ ] Secrets not committed
- [ ] Branch is up to date with main/develop
- [ ] Commit messages follow convention
- [ ] PR description is clear
- [ ] CI checks pass
- [ ] Code reviewed by team member

## 🔗 Useful Links

- [CI Workflow](.github/workflows/ci.yml)
- [CD Workflow](.github/workflows/cd.yml)
- [Full Documentation](./ci-cd-setup.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)

---

**Pro Tip**: Add `alias gha='gh run list --limit 5'` to your shell for quick status checks!
