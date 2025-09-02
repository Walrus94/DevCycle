# Contributing to DevCycle

Thank you for your interest in contributing to DevCycle! This guide will help you get started with contributing to our AI-powered development lifecycle automation system.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.9+
- Poetry (recommended) or pip
- Docker and Docker Compose
- Git

### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/devcycle.git
   cd devcycle
   ```

2. **Install Dependencies**
   ```bash
   poetry install --with dev
   ```

3. **Set Up Environment**
   ```bash
   export ENVIRONMENT=development
   ```

4. **Start Services**
   ```bash
   docker-compose up -d
   ```

5. **Run Migrations**
   ```bash
   poetry run alembic upgrade head
   ```

6. **Run Tests**
   ```bash
   poetry run pytest
   ```

## Development Workflow

### Branch Naming

Use descriptive branch names without personal identifiers:
- ✅ `feature/agent-orchestration`
- ✅ `fix/authentication-bug`
- ✅ `docs/api-documentation`
- ❌ `john/feature-123`
- ❌ `arsnazarov94/fix`

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

**Examples:**
```
feat(auth): add JWT token blacklisting
fix(api): resolve rate limiting issue
docs(api): update authentication guide
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

## Coding Standards

### Python Code Style

We use Black for code formatting and Flake8 for linting:

```bash
# Format code
poetry run black .

# Check linting
poetry run flake8

# Type checking
poetry run mypy .
```

### Code Organization

- **Modules**: Use clear, descriptive module names
- **Classes**: Follow PascalCase naming
- **Functions**: Use snake_case naming
- **Constants**: Use UPPER_CASE naming
- **Imports**: Group imports (standard, third-party, local)

### Documentation

- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Include type hints for all functions
- **Comments**: Explain complex logic, not obvious code

**Example:**
```python
def process_agent_message(
    agent_id: str,
    message: str,
    priority: int = 1
) -> AgentResult:
    """
    Process a message for a specific agent.

    Args:
        agent_id: Unique identifier for the agent
        message: Message content to process
        priority: Message priority (1-5, default: 1)

    Returns:
        AgentResult containing processing results

    Raises:
        AgentNotFoundError: If agent doesn't exist
        ValidationError: If message format is invalid
    """
    # Implementation here
    pass
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── conftest.py    # Test configuration
```

### Writing Tests

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete workflows

**Example Unit Test:**
```python
import pytest
from devcycle.core.agents.base import BaseAgent

class TestBaseAgent:
    def test_agent_initialization(self):
        """Test agent initializes with correct properties."""
        agent = BaseAgent("test-agent")

        assert agent.name == "test-agent"
        assert agent.status == AgentStatus.IDLE
        assert len(agent.execution_history) == 0
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test type
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/

# Run with coverage
poetry run pytest --cov=devcycle

# Run specific test
poetry run pytest tests/unit/test_agent.py::TestBaseAgent::test_initialization
```

### Test Requirements

- **Coverage**: Maintain >80% test coverage
- **Naming**: Use descriptive test names
- **Isolation**: Tests should be independent
- **Speed**: Unit tests should be fast (<1s each)

## Documentation

### Documentation Standards

- **Markdown**: Use Markdown for all documentation
- **Structure**: Follow the established documentation structure
- **Examples**: Include code examples where helpful
- **Links**: Use relative links for internal documentation

### Documentation Types

- **API Documentation**: Auto-generated from code
- **User Guides**: Step-by-step instructions
- **Architecture Docs**: System design and decisions
- **Development Docs**: Setup and contribution guides

## Pull Request Process

### Before Submitting

1. **Run Tests**: Ensure all tests pass
2. **Check Coverage**: Maintain test coverage
3. **Update Documentation**: Update relevant docs
4. **Rebase**: Rebase on latest main branch

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs
2. **Code Review**: At least one maintainer review
3. **Testing**: Manual testing if needed
4. **Approval**: Maintainer approval required

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g. Windows 10]
- Python version: [e.g. 3.11]
- DevCycle version: [e.g. 0.1.0]

**Additional context**
Any other context about the problem.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
A clear description of what the problem is.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other context or screenshots about the feature request.
```

## Getting Help

- **Documentation**: Check the [documentation](../index.md)
- **Issues**: Search [existing issues](https://github.com/devcycle/devcycle/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/devcycle/devcycle/discussions)
- **Discord**: Join our community Discord (if available)

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to DevCycle! 🚀
