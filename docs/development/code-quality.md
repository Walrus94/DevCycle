# Code Quality Guidelines

This document describes the code quality standards and tools used in the DevCycle project.

## Overview

DevCycle maintains high code quality through automated checks and consistent formatting. All code must pass quality checks before being committed.

## Quality Tools

### 1. Code Formatting
- **Black**: Automatic code formatting
- **isort**: Import statement sorting
- **Line length**: 88 characters (Black default)

### 2. Linting
- **Flake8**: Style guide enforcement
- **Configuration**: Extended ignore for Black compatibility

### 3. Type Checking
- **MyPy**: Static type checking
- **Configuration**: Strict type checking enabled
- **Exclusions**: Third-party libraries with missing type stubs

### 4. Security
- **Safety**: Dependency vulnerability scanning
- **Bandit**: Static security analysis

## Quick Start

### Install Pre-commit Hooks
```bash
# Install development dependencies
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install
```

### Run Quality Checks
```bash
# Run individual checks
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 .
poetry run mypy .
poetry run safety check
poetry run bandit -r devcycle/
```

### Fix Formatting Issues
```bash
# Auto-fix formatting
poetry run black .
poetry run isort .

# Then run checks again
poetry run black --check .
poetry run isort --check-only .
```

## Pre-commit Hooks

Pre-commit hooks automatically run quality checks before each commit:

- **Code formatting** (Black, isort)
- **Linting** (Flake8)
- **Type checking** (MyPy)
- **Security scanning** (Bandit)
- **General checks** (trailing whitespace, file size, etc.)
- **Poetry validation** (lock file, dependencies)

## Configuration Files

- `.pre-commit-config.yaml`: Pre-commit hook configuration
- `pyproject.toml`: Tool configurations (Black, isort, MyPy, Flake8)

## Code Standards

### Python Style
- **PEP 8** compliance (via Flake8)
- **Black** formatting (88 character line length)
- **Type hints** required (via MyPy)
- **Docstrings** for public functions and classes

### Import Organization
- **isort** with Black profile
- **First-party** imports: `devcycle`
- **Third-party** imports: Standard libraries, then external packages

### Type Hints
- **Required** for all function parameters and return values
- **Strict mode** enabled in MyPy
- **Exclusions** for third-party libraries without type stubs

## CI/CD Integration

The CI/CD pipeline runs the same quality checks:

1. **Code Quality Job**: Black, isort, Flake8, MyPy
2. **Security Job**: Safety, Bandit
3. **All jobs must pass** before merging

## Best Practices

### 1. Before Committing
```bash
# Run quality checks
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 .
poetry run mypy .

# Fix any issues
poetry run black .
poetry run isort .

# Commit with pre-commit hooks
git commit -m "feat: add new feature"
```

### 2. IDE Integration
- **VS Code**: Install Python extension with Black, isort, MyPy support
- **PyCharm**: Enable Black and MyPy in settings
- **Vim/Neovim**: Use ALE or similar plugin

### 3. Common Issues

**Black/Flake8 conflicts**:
- Flake8 is configured to ignore Black's formatting choices
- Use `--extend-ignore=E203,W503` in Flake8

**MyPy errors**:
- Add type hints to function signatures
- Use `# type: ignore` for unavoidable issues
- Check third-party library exclusions

**Import sorting**:
- isort uses Black profile for compatibility
- Run `poetry run isort .` to fix import order

## Troubleshooting

### Pre-commit Hooks Not Running
```bash
# Reinstall hooks
poetry run pre-commit uninstall
poetry run pre-commit install
```

### MyPy Type Errors
```bash
# Check specific file
poetry run mypy devcycle/specific_file.py

# Ignore missing imports
poetry run mypy --ignore-missing-imports .
```

### Black Formatting Issues
```bash
# Check what would be changed
poetry run black --diff .

# Apply formatting
poetry run black .
```

## Quality Metrics

The project aims for:
- **100%** type coverage (where possible)
- **0** Flake8 violations
- **0** security vulnerabilities
- **Consistent** code formatting

## Contributing

1. **Install pre-commit hooks** before making changes
2. **Run quality checks** before committing
3. **Fix all issues** before pushing
4. **Follow** the established code style

Quality checks are enforced in CI/CD, so all code must pass these standards before being merged.
