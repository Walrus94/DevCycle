# CI/CD Pipeline

This document describes the CI/CD pipeline setup for the DevCycle project.

## Overview

The CI/CD pipeline uses a **tiered testing strategy** to balance speed with thoroughness. It runs different test suites based on the target branch, ensuring fast feedback for feature development while maintaining comprehensive validation for production branches.

## Testing Strategy

### 🚀 Feature Branch PRs
- **Unit tests only** (fast feedback ~2-3 minutes)
- **Code quality checks** (formatting, linting, type checking)
- **Security scan** (quick safety check)

### 🔄 Develop Branch PRs  
- **Unit + Integration tests** (medium thoroughness ~5-8 minutes)
- **All code quality checks**
- **Security scan**

### 🎯 Main Branch PRs
- **Full test suite** (unit + integration + e2e ~10-15 minutes)
- **All code quality checks**
- **Security scan**
- **Build validation**

## Pipeline Stages

### 1. Code Quality Checks
- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **MyPy**: Type checking

### 2. Testing
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests that verify component interactions
- **End-to-End Tests**: Full workflow tests using testcontainers

### 3. Security Scanning
- **Safety**: Check for known security vulnerabilities in dependencies
- **Bandit**: Static analysis for common security issues

### 4. Build Validation
- **Package Build**: Ensure the package can be built successfully
- **Import Validation**: Verify all imports work correctly

## Local Development

### Prerequisites
- Python 3.11+
- Poetry
- Docker (for testcontainers)

### Setup
```bash
# Install dependencies
make install-dev

# Run all CI checks locally
make ci

# Run specific checks
make lint
make format
make type-check
make security-check
make test
```

### Pre-commit Hooks
Pre-commit hooks are automatically installed with `make install-dev`. They run:
- Code formatting (Black, isort)
- Linting (Flake8)
- Type checking (MyPy)
- Security checks (Bandit)
- General code quality checks

### Running Tests
```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration
make test-e2e

# With coverage
make test-coverage
```

## GitHub Actions

The pipeline runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Smart Test Execution
The pipeline automatically determines which tests to run based on the target branch:

```yaml
# Feature branch → main: Full test suite
# Feature branch → develop: Unit + Integration tests  
# Feature branch → feature: Unit tests only
```

### Workflow Files
- `.github/workflows/ci.yml`: Main CI/CD pipeline with tiered testing

### Coverage Reporting
Test coverage is reported to Codecov with separate flags for:
- Unit tests
- Integration tests  
- End-to-end tests

### Performance Benefits
- **Feature development**: Fast feedback in 2-3 minutes
- **Integration testing**: Medium validation in 5-8 minutes
- **Production readiness**: Full validation in 10-15 minutes

## Configuration Files

- `pytest.ini`: Pytest configuration
- `pyproject.toml`: Poetry and tool configurations
- `.pre-commit-config.yaml`: Pre-commit hooks
- `Makefile`: Development commands
- `.github/workflows/ci.yml`: GitHub Actions workflow

## Best Practices

1. **Run checks locally** before pushing: `make ci`
2. **Fix formatting issues** automatically: `make format`
3. **Write tests** for new functionality
4. **Keep dependencies updated** and run security checks
5. **Use meaningful commit messages** and PR descriptions

## Troubleshooting

### Common Issues

1. **Formatting errors**: Run `make format` to fix automatically
2. **Import errors**: Run `make type-check` to identify issues
3. **Test failures**: Check test logs and ensure testcontainers are working
4. **Security warnings**: Review and address security scan results

### Getting Help

- Check the test logs in GitHub Actions
- Run tests locally to reproduce issues
- Review the configuration files for custom settings
