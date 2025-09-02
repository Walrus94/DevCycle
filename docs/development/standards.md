# Coding Standards

This document outlines the coding standards and conventions used in the DevCycle project to ensure consistency, readability, and maintainability across the codebase.

## Table of Contents

- [Python Standards](#python-standards)
- [Type Hints](#type-hints)
- [Documentation](#documentation)
- [Error Handling](#error-handling)
- [Testing Standards](#testing-standards)
- [Code Organization](#code-organization)
- [Performance Guidelines](#performance-guidelines)
- [Security Standards](#security-standards)

## Python Standards

### Code Style

We follow [PEP 8](https://pep8.org/) with the following specific guidelines:

#### Line Length
- **Maximum line length**: 88 characters (Black formatter default)
- **Use line continuation** for long lines:
  ```python
  # Good
  result = some_function(
      argument1,
      argument2,
      argument3
  )

  # Bad
  result = some_function(argument1, argument2, argument3)
  ```

#### Naming Conventions
- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private attributes**: `_leading_underscore`
- **Module names**: `snake_case`

```python
# Good
class UserManager:
    MAX_RETRY_ATTEMPTS = 3

    def __init__(self):
        self._user_cache = {}

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        pass

# Bad
class userManager:
    maxRetryAttempts = 3

    def __init__(self):
        self.userCache = {}

    def GetUserById(self, userId: str):
        pass
```

#### Imports
- **Order**: Standard library, third-party, local imports
- **Group**: Separate groups with blank lines
- **Style**: One import per line

```python
# Good
import os
import sys
from typing import Dict, List, Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from devcycle.core.config import Settings
from devcycle.api.routes import agents
```

### Code Formatting

We use **Black** for automatic code formatting with specific configuration:

```bash
# Format all Python files
poetry run black .

# Check formatting without changes
poetry run black --check .
```

**Black Configuration** (from `pyproject.toml`):
- **Line length**: 88 characters
- **Target version**: Python 3.9+
- **Excludes**: `.eggs`, `.git`, `.hg`, `.mypy_cache`, `.tox`, `.venv`, `build`, `dist`

### Import Sorting

We use **isort** for import organization with Black compatibility:

```bash
# Sort imports
poetry run isort .

# Check import sorting
poetry run isort --check-only .
```

**isort Configuration** (from `pyproject.toml`):
- **Profile**: `black` (compatible with Black formatting)
- **Multi-line output**: 3 (Black-compatible)
- **Line length**: 88 characters
- **First-party modules**: `["devcycle"]`
- **Third-party modules**: `["pytest", "black", "isort", "flake8", "mypy"]`

### Import Organization

Follow the isort configuration for proper import ordering:

```python
# Good - follows isort configuration
import os
import sys
from typing import Dict, List, Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from devcycle.core.config import Settings
from devcycle.api.routes import agents

# Bad - incorrect import order
from devcycle.core.config import Settings
import requests
from typing import Dict, List, Optional
import os
```

## Type Hints

### Required Type Hints

All function signatures must include complete type hints. The project uses strict mypy configuration:

```python
# Good - complete type hints
def process_message(
    message: Message,
    agent_id: str,
    timeout: int = 30
) -> ProcessingResult:
    pass

# Bad - missing type hints (will fail mypy)
def process_message(message, agent_id, timeout=30):
    pass

# Bad - incomplete type hints (will fail mypy)
def process_message(message: Message, agent_id, timeout: int = 30):
    pass
```

### Type Hint Guidelines

Based on the project's mypy configuration:

- **All function parameters** must have type hints
- **All return types** must be specified
- **Use `typing` module** for complex types (Python 3.9 compatibility)
- **Use `Optional[T]`** for nullable values (not `T | None`)
- **Use `Union[T, U]`** for multiple possible types (not `T | U`)
- **No implicit Optional** - explicitly use `Optional[T]` instead of `T = None`

```python
from typing import Dict, List, Optional, Union, Any

# Good - follows project mypy configuration
def get_agents(
    agent_type: Optional[str] = None,
    status: Union[str, List[str]] = None,
    limit: int = 100
) -> List[Agent]:
    pass

# Bad - implicit Optional (will fail mypy)
def get_agents(agent_type: str = None) -> List[Agent]:
    pass

# Good - explicit Optional
def get_agents(agent_type: Optional[str] = None) -> List[Agent]:
    pass

# Good - complex types with proper typing
def process_data(
    data: Dict[str, Any],
    filters: Optional[List[str]] = None
) -> Union[ProcessingResult, ErrorResult]:
    pass
```

### Mypy Configuration Compliance

The project uses strict mypy settings. Ensure your code follows these rules:

- **`disallow_untyped_defs = True`**: All functions must have type hints
- **`disallow_incomplete_defs = True`**: All parameters must be typed
- **`no_implicit_optional = True`**: Use `Optional[T]` instead of `T = None`
- **`warn_return_any = True`**: Avoid returning `Any` type
- **`strict_equality = True`**: Use `is`/`is not` for None comparisons

```python
# Good - follows strict mypy rules
def create_agent(
    name: str,
    agent_type: str,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Agent:
    if description is None:  # Use 'is' for None comparison
        description = "Default description"
    return Agent(name=name, type=agent_type, description=description)

# Bad - violates mypy rules
def create_agent(name, agent_type, description=None):  # Missing types
    return Agent(name=name, type=agent_type, description=description)
```

### Pydantic Models

Use Pydantic for data validation and serialization:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., regex=r'^[a-z_]+$')
    description: Optional[str] = Field(None, max_length=500)
    version: str = Field(default="1.0.0", regex=r'^\d+\.\d+\.\d+$')

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Name must contain only alphanumeric characters and underscores')
        return v

class AgentResponse(AgentCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## Documentation

### Docstrings

Use Google-style docstrings for all public functions, classes, and modules:

```python
def send_message(
    agent_id: str,
    action: str,
    data: Dict[str, Any],
    priority: str = "normal"
) -> MessageResponse:
    """Send a message to a specific agent.

    Args:
        agent_id: Unique identifier of the target agent
        action: Action to be performed by the agent
        data: Message payload data
        priority: Message priority level (normal, high, urgent)

    Returns:
        MessageResponse object containing message details

    Raises:
        AgentNotFoundError: If the specified agent doesn't exist
        ValidationError: If message data is invalid
        TimeoutError: If message sending times out

    Example:
        >>> response = send_message(
        ...     agent_id="agent_123",
        ...     action="analyze_requirement",
        ...     data={"requirement": "User authentication"}
        ... )
        >>> print(response.message_id)
        msg_456
    """
    pass
```

### Inline Comments

Use inline comments sparingly and only for complex logic:

```python
# Good - explains why, not what
# Skip validation for system messages to avoid circular dependencies
if message.source == "system":
    return process_system_message(message)

# Bad - obvious comment
# Increment counter by 1
counter += 1
```

## Error Handling

### Exception Types

Use specific exception types and create custom exceptions when needed:

```python
# Custom exceptions
class DevCycleError(Exception):
    """Base exception for DevCycle application."""
    pass

class AgentNotFoundError(DevCycleError):
    """Raised when an agent cannot be found."""
    pass

class MessageValidationError(DevCycleError):
    """Raised when message validation fails."""
    pass

# Usage
def get_agent(agent_id: str) -> Agent:
    agent = agent_repository.find_by_id(agent_id)
    if not agent:
        raise AgentNotFoundError(f"Agent {agent_id} not found")
    return agent
```

### Error Handling Patterns

```python
# Good - specific exception handling
try:
    result = process_message(message)
except MessageValidationError as e:
    logger.warning(f"Message validation failed: {e}")
    return {"error": "Invalid message format", "details": str(e)}
except TimeoutError:
    logger.error("Message processing timed out")
    return {"error": "Processing timeout"}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"error": "Internal server error"}

# Bad - generic exception handling
try:
    result = process_message(message)
except Exception as e:
    return {"error": str(e)}
```

## Testing Standards

### Test Structure

Follow the **Arrange-Act-Assert** pattern:

```python
import pytest
from unittest.mock import Mock, patch
from devcycle.core.agents import AgentManager

class TestAgentManager:
    def test_create_agent_success(self):
        # Arrange
        agent_data = {
            "name": "test_agent",
            "type": "business_analyst",
            "description": "Test agent"
        }
        expected_agent_id = "agent_123"

        with patch('devcycle.core.agents.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = expected_agent_id

            # Act
            result = AgentManager.create_agent(agent_data)

            # Assert
            assert result.id == expected_agent_id
            assert result.name == agent_data["name"]
            assert result.status == "registered"
```

### Test Naming

Use descriptive test names that explain the scenario:

```python
# Good
def test_create_agent_with_invalid_type_raises_validation_error(self):
    pass

def test_get_agent_returns_none_when_agent_not_found(self):
    pass

# Bad
def test_create_agent(self):
    pass

def test_get_agent(self):
    pass
```

### Test Coverage

- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% coverage required
- **Use pytest-cov** for coverage reporting:

```bash
poetry run pytest --cov=devcycle --cov-report=html
```

## Code Organization

### Module Structure

Organize code into logical modules:

```
devcycle/
├── core/           # Core business logic
│   ├── agents/     # Agent management
│   ├── messages/   # Message handling
│   └── config/     # Configuration
├── api/            # API layer
│   ├── routes/     # Route handlers
│   ├── models/     # Pydantic models
│   └── middleware/ # Custom middleware
└── utils/          # Utility functions
```

### Function Size

- **Maximum function length**: 50 lines
- **Maximum class length**: 300 lines
- **Break down large functions** into smaller, focused functions

```python
# Good - focused function
def validate_agent_data(data: Dict[str, Any]) -> None:
    """Validate agent creation data."""
    if not data.get("name"):
        raise ValidationError("Agent name is required")

    if not data.get("type"):
        raise ValidationError("Agent type is required")

    if data["type"] not in VALID_AGENT_TYPES:
        raise ValidationError(f"Invalid agent type: {data['type']}")

# Bad - doing too much
def create_agent(data: Dict[str, Any]) -> Agent:
    # 100+ lines of validation, creation, database operations, etc.
    pass
```

## Performance Guidelines

### Database Queries

- **Use connection pooling** for database connections
- **Avoid N+1 queries** by using eager loading
- **Use database indexes** for frequently queried fields
- **Implement query timeouts**

```python
# Good - single query with joins
agents = session.query(Agent).options(
    joinedload(Agent.messages)
).filter(Agent.status == "online").all()

# Bad - N+1 queries
agents = session.query(Agent).filter(Agent.status == "online").all()
for agent in agents:
    messages = session.query(Message).filter(Message.agent_id == agent.id).all()
```

### Caching

- **Use Redis** for application-level caching
- **Cache expensive operations** (database queries, API calls)
- **Set appropriate TTL** for cached data
- **Invalidate cache** when data changes

```python
from devcycle.core.cache import cache

@cache(ttl=300)  # Cache for 5 minutes
def get_agent_capabilities(agent_type: str) -> List[str]:
    """Get capabilities for an agent type."""
    return database.query(Capability).filter_by(agent_type=agent_type).all()
```

### Async Operations

Use async/await for I/O operations:

```python
import asyncio
from typing import List

async def process_messages_batch(messages: List[Message]) -> List[ProcessingResult]:
    """Process multiple messages concurrently."""
    tasks = [process_single_message(msg) for msg in messages]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to process message {messages[i].id}: {result}")
            processed_results.append(ProcessingResult(success=False, error=str(result)))
        else:
            processed_results.append(result)

    return processed_results
```

## Security Standards

### Input Validation

- **Validate all inputs** using Pydantic models
- **Sanitize user inputs** to prevent injection attacks
- **Use parameterized queries** for database operations

```python
from pydantic import BaseModel, validator
import re

class MessageCreate(BaseModel):
    content: str
    agent_id: str

    @validator('content')
    def validate_content(cls, v):
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', v)
        if len(sanitized) != len(v):
            raise ValueError("Content contains invalid characters")
        return sanitized

    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid agent ID format")
        return v
```

### Authentication & Authorization

- **Use JWT tokens** for authentication
- **Implement role-based access control**
- **Validate permissions** for each operation
- **Use secure session management**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Logging Security

- **Never log sensitive data** (passwords, tokens, personal information)
- **Use structured logging** with appropriate log levels
- **Implement log rotation** and retention policies

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_agent_activity(agent_id: str, action: str, user_id: str, **kwargs):
    """Log agent activity without sensitive data."""
    log_data = {
        "agent_id": agent_id,
        "action": action,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        **{k: v for k, v in kwargs.items() if k not in ['password', 'token', 'secret']}
    }
    logger.info(f"Agent activity: {json.dumps(log_data)}")
```

## Code Review Checklist

When reviewing code, ensure:

- [ ] Code follows PEP 8 and project style guidelines
- [ ] Type hints are present and correct
- [ ] Docstrings are complete and accurate
- [ ] Error handling is appropriate
- [ ] Tests are comprehensive and pass
- [ ] Security considerations are addressed
- [ ] Performance implications are considered
- [ ] Code is readable and maintainable

## Tools and Automation

### Pre-commit Hooks

We use pre-commit hooks to enforce standards. The configuration aligns with the project's tool settings:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-passlib]
```

### Flake8 Configuration

The project uses flake8 with specific configuration (`.flake8`):

```ini
[flake8]
max-line-length = 88
extend-ignore = E203
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    .mypy_cache,
    .pytest_cache,
    htmlcov,
    build,
    dist
```

**Key flake8 rules**:
- **Line length**: 88 characters (matches Black)
- **Ignore E203**: Whitespace before ':' (conflicts with Black)
- **Exclude directories**: Standard Python project exclusions

**Flake8 Plugins** (from `pyproject.toml`):
- **flake8-docstrings**: Enforces docstring standards
- **flake8-import-order**: Ensures proper import ordering

```python
# Good - proper docstring format (flake8-docstrings)
def process_message(message: Message) -> ProcessingResult:
    """Process a message through the system.

    Args:
        message: The message to process

    Returns:
        ProcessingResult with processing outcome

    Raises:
        ValidationError: If message is invalid
    """
    pass

# Bad - missing docstring (flake8-docstrings will warn)
def process_message(message: Message) -> ProcessingResult:
    pass
```

### Mypy Configuration

The project uses strict mypy configuration (`mypy.ini` and `pyproject.toml`):

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = False
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
```

**Key mypy rules**:
- **Strict type checking**: All functions must have complete type hints
- **No implicit Optional**: Use `Optional[T]` instead of `T = None`
- **Strict equality**: Use `is`/`is not` for None comparisons
- **Test files relaxed**: Test files have relaxed type checking rules

### IDE Configuration

Recommended VS Code settings that align with the project configuration:

```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.flake8Args": [
    "--max-line-length=88",
    "--extend-ignore=E203"
  ],
  "python.linting.mypyArgs": [
    "--config-file=mypy.ini"
  ],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.autoImportCompletions": true
}
```

### Running Quality Checks

To ensure your code passes all pre-commit checks:

```bash
# Run all quality checks
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 .
poetry run mypy .

# Fix formatting issues
poetry run black .
poetry run isort .

# Run specific checks
poetry run flake8 devcycle/
poetry run mypy devcycle/
```

### Common Issues and Solutions

**Flake8 Issues**:
```python
# E501: Line too long (88 characters)
# Solution: Break long lines or use Black formatting
long_variable_name = some_function_with_very_long_parameters(
    parameter1, parameter2, parameter3, parameter4
)

# E203: Whitespace before ':'
# Solution: This is ignored in .flake8 config (conflicts with Black)
```

**Mypy Issues**:
```python
# Missing type hints
def my_function(param):  # Error: Function is missing a type annotation
    pass

# Solution: Add complete type hints
def my_function(param: str) -> None:
    pass

# Implicit Optional
def my_function(param: str = None):  # Error: Implicit Optional
    pass

# Solution: Use explicit Optional
def my_function(param: Optional[str] = None) -> None:
    pass
```

## Conclusion

Following these coding standards ensures:

- **Consistency** across the codebase
- **Readability** for all team members
- **Maintainability** for future development
- **Quality** through automated checks
- **Security** through best practices

Remember: **Code is read more often than it's written**. Write code that your future self (and teammates) will thank you for.
