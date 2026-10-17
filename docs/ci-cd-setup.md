# CI/CD Setup Documentation

> [!WARNING]
> **Legacy and unsupported.** The CI/CD workflows described here were removed or replaced. Zakera does not operate a hosted service or supported deployment pipeline; see `docs/vnext/CI_CD_AUDIT.md`.

## Overview

Zakera uses a comprehensive CI/CD pipeline built with GitHub Actions to ensure code quality, security, and reliable deployments. The pipeline consists of two main workflows:

1. **CI Pipeline** (`.github/workflows/ci.yml`) - Runs on every push and pull request
2. **CD Pipeline** (`.github/workflows/cd.yml`) - Runs after successful CI for deployments

## Architecture

### CI Pipeline Jobs

The CI pipeline runs multiple jobs in parallel for faster feedback:

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Backend Jobs          Frontend Jobs        Docker Jobs      │
│  ├─ Linting            ├─ Linting           ├─ Build         │
│  ├─ Security Scan      ├─ Security Scan     ├─ Security Scan │
│  ├─ Tests (Matrix)     ├─ Tests             └─ Compose Test  │
│  └─ Coverage           └─ Build                              │
│                                                               │
│  Code Quality          Integration                           │
│  ├─ SonarCloud         └─ E2E Tests                          │
│  └─ CodeQL                                                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### CD Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   CD Pipeline Flow                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Prepare Deployment                                       │
│     └─ Determine environment (staging/production)            │
│     └─ Generate version tag                                  │
│                                                               │
│  2. Build & Push Images                                      │
│     └─ Build Docker images                                   │
│     └─ Push to Amazon ECR                                    │
│     └─ Scan with Trivy                                       │
│                                                               │
│  3. Deploy to Environment                                    │
│     └─ Apply Terraform configuration                         │
│     └─ Update ECS service                                    │
│     └─ Wait for deployment                                   │
│     └─ Run smoke tests                                       │
│                                                               │
│  4. Post-Deployment                                          │
│     └─ Run migrations                                        │
│     └─ Clear CDN cache                                       │
│     └─ Send notifications                                    │
│     └─ Create GitHub release (production only)               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Setup Instructions

### Prerequisites

1. **GitHub Repository Secrets**

   Configure the following secrets in your GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

   ```
   AWS_ACCESS_KEY_ID          # AWS credentials for deployment
   AWS_SECRET_ACCESS_KEY      # AWS secret key
   SONAR_TOKEN               # SonarCloud token (optional)
   CODECOV_TOKEN             # Codecov token (optional)
   SLACK_WEBHOOK             # Slack webhook for notifications (optional)
   ```

2. **GitHub Environments**

   Create two environments in `Settings` → `Environments`:
   
   - **staging**: For staging deployments
   - **production**: For production deployments (with protection rules)
   
   Protection rules for production:
   - Required reviewers: 1+ team members
   - Wait timer: 5 minutes (optional)
   - Deployment branches: `main` only

### Required Dependencies

#### Backend Dependencies

Add to `requirements.txt`:
```
safety==2.3.5
bandit==1.7.5
```

#### Frontend Dependencies

Add to `src/frontend/package.json`:
```json
{
  "devDependencies": {
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/react": "^14.1.2",
    "@testing-library/user-event": "^14.5.1",
    "@types/jest": "^29.5.11",
    "@typescript-eslint/eslint-plugin": "^6.16.0",
    "@typescript-eslint/parser": "^6.16.0",
    "eslint": "^8.56.0",
    "eslint-config-next": "14.0.4",
    "eslint-config-prettier": "^9.1.0",
    "eslint-plugin-jsx-a11y": "^6.8.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "next-router-mock": "^0.9.10",
    "prettier": "^3.1.1"
  },
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint . --ext .js,.jsx,.ts,.tsx --fix",
    "format": "prettier --write \"**/*.{js,jsx,ts,tsx,json,css,md}\"",
    "format:check": "prettier --check \"**/*.{js,jsx,ts,tsx,json,css,md}\""
  }
}
```

## Running CI/CD Locally

### Backend Checks

```bash
# Install dependencies
pip install -r requirements.txt
pip install black isort flake8 mypy bandit safety pytest pytest-cov

# Run linting
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
mypy src/

# Run security scans
bandit -r src/ -ll
safety check

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html
```

### Frontend Checks

```bash
cd src/frontend

# Install dependencies
npm install

# Run linting
npm run lint

# Run formatting check
npm run format:check

# Run tests
npm test

# Build
npm run build
```

### Docker Validation

```bash
# Build image
docker build -t zakera:test .

# Scan with Trivy (install first: https://github.com/aquasecurity/trivy)
trivy image zakera:test

# Test docker-compose
docker-compose up -d
docker-compose ps
docker-compose logs
docker-compose down
```

## Test Coverage Requirements

### Backend Coverage Targets

- **Minimum**: 70% overall coverage
- **Recommended**: 80%+ coverage
- **Critical paths**: 90%+ coverage (authentication, database operations)

### Frontend Coverage Targets

- **Branches**: 70%
- **Functions**: 70%
- **Lines**: 70%
- **Statements**: 70%

## CI/CD Workflow Triggers

### CI Pipeline Triggers

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual trigger via `workflow_dispatch`

### CD Pipeline Triggers

- Successful completion of CI pipeline on `main` (production) or `develop` (staging)
- Manual trigger with environment selection

## Testing Strategy

### Test Types

1. **Unit Tests**
   - Individual function/component testing
   - Fast execution
   - No external dependencies
   - Run on every commit

2. **Integration Tests**
   - Test interactions between components
   - Use test database and Redis
   - Run in CI pipeline
   - Mark with `@pytest.mark.integration`

3. **E2E Tests**
   - Full user workflow testing
   - Browser automation (future implementation)
   - Run before deployment

4. **Security Tests**
   - Dependency scanning (Safety, npm audit)
   - Code security analysis (Bandit)
   - Container scanning (Trivy)
   - Run on every commit

### Test Organization

```python
# tests/test_example.py

import pytest

@pytest.mark.unit
def test_user_creation():
    """Unit test for user creation"""
    pass

@pytest.mark.integration
def test_user_api_endpoint():
    """Integration test for API"""
    pass

@pytest.mark.slow
def test_large_dataset_processing():
    """Slow-running test"""
    pass
```

## Deployment Process

### Automatic Deployment

1. **Staging**: Automatically deployed when changes are pushed to `develop`
2. **Production**: Automatically deployed when changes are pushed to `main`

### Manual Deployment

1. Go to `Actions` tab in GitHub
2. Select "CD Pipeline - Deployment"
3. Click "Run workflow"
4. Select environment (staging/production)
5. Click "Run workflow"

### Deployment Steps

1. **Pre-Deployment**
   - Version tagging
   - Database backup (production only)
   - Terraform state validation

2. **Deployment**
   - Docker image build and push
   - Terraform apply
   - ECS service update
   - Wait for service stability

3. **Post-Deployment**
   - Smoke tests
   - Database migrations
   - CDN cache clear
   - Notification

4. **Verification**
   - Health check endpoints
   - API status checks
   - Error rate monitoring

## Rollback Procedures

### Automatic Rollback

The CD pipeline includes automatic rollback on failure:
- Failed smoke tests trigger rollback
- Health check failures trigger rollback
- Deployment timeout triggers rollback

### Manual Rollback

If manual rollback is needed:

```bash
# Via AWS CLI
aws ecs update-service \
  --cluster zakera-cluster-production \
  --service zakera-service \
  --task-definition zakera-task:PREVIOUS_VERSION

# Via Terraform
cd terraform
terraform apply -var="image_tag=PREVIOUS_VERSION"
```

### Database Rollback

```bash
# Restore from RDS snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier zakera-production \
  --db-snapshot-identifier SNAPSHOT_ID
```

## Monitoring and Alerts

### What's Monitored

- **CI/CD Pipeline Status**: Success/failure notifications
- **Deployment Status**: Real-time deployment progress
- **Test Coverage**: Coverage reports and trends
- **Security Vulnerabilities**: Critical and high severity issues
- **Build Time**: Pipeline execution duration

### Notification Channels

1. **GitHub Actions UI**: Built-in status and logs
2. **Slack** (optional): Real-time notifications
3. **Email**: GitHub default notifications

## Troubleshooting

### Common CI Issues

#### "Tests Failed"

```bash
# Check test logs in GitHub Actions
# Run tests locally to reproduce
pytest tests/ -v --tb=short

# Check for missing dependencies
pip install -r requirements.txt
```

#### "Linting Failed"

```bash
# Auto-fix most issues
black src/ tests/
isort src/ tests/

# Check remaining issues
flake8 src/ tests/
```

#### "Docker Build Failed"

```bash
# Check Dockerfile syntax
docker build -t zakera:test .

# Verify base images
docker pull python:3.11-slim
```

### Common CD Issues

#### "Deployment Failed"

1. Check AWS credentials are valid
2. Verify ECS cluster exists
3. Check ECR repository permissions
4. Review Terraform state

#### "Smoke Tests Failed"

1. Check application logs in CloudWatch
2. Verify load balancer health checks
3. Test endpoints manually
4. Check database connectivity

#### "Terraform Apply Failed"

```bash
# Validate configuration
terraform validate

# Check state
terraform state list

# Import existing resources if needed
terraform import aws_ecs_cluster.main zakera-cluster-production
```

## Performance Optimization

### Pipeline Speed

Current average execution times:
- **CI Pipeline**: ~8-12 minutes
- **CD Pipeline**: ~10-15 minutes

### Optimization Strategies

1. **Caching**
   - pip packages cached
   - npm packages cached
   - Docker layers cached

2. **Parallel Execution**
   - Backend and frontend tests run in parallel
   - Multiple Python versions tested concurrently
   - Linting and security scans run in parallel

3. **Resource Allocation**
   - Use GitHub-hosted runners
   - Consider self-hosted runners for faster builds

## Security Best Practices

### Secret Management

- Never commit secrets to repository
- Use GitHub Secrets for sensitive data
- Rotate credentials regularly
- Use least-privilege IAM policies

### Dependency Management

- Automated dependency scanning
- Security vulnerability alerts
- Regular dependency updates
- Pin dependency versions

### Container Security

- Scan images with Trivy
- Use minimal base images
- Non-root user in containers
- Regular base image updates

## Maintenance

### Regular Tasks

- **Weekly**: Review failed builds and flaky tests
- **Monthly**: Update dependencies and base images
- **Quarterly**: Review and optimize pipeline performance

### Updating Workflows

When modifying workflows:

1. Test changes in a feature branch
2. Review logs carefully
3. Update documentation
4. Notify team of changes

## Support and Resources

### Documentation

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Terraform AWS Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)

### Getting Help

1. Check GitHub Actions logs
2. Review this documentation
3. Search existing issues
4. Create new issue with logs and error messages

---

**Last Updated**: February 2026  
**Maintained By**: DevOps Team
