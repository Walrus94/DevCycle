# Development Guidelines

This document provides comprehensive development guidelines and best practices for the DevCycle project, covering common issues, troubleshooting steps, and development recommendations.

## Table of Contents

- [Troubleshooting Guide](#troubleshooting-guide)
- [Development Best Practices](#development-best-practices)
- [Code Review Guidelines](#code-review-guidelines)
- [Performance Optimization](#performance-optimization)
- [Security Guidelines](#security-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)

## Troubleshooting Guide

### Common Development Issues

#### 1. Environment Setup Issues

**Problem**: Poetry installation fails or dependencies conflict

**Symptoms**:
- `poetry install` fails with dependency resolution errors
- Import errors for installed packages
- Version conflicts between packages

**Solutions**:

```bash
# Clear Poetry cache and reinstall
poetry cache clear --all pypi
rm -rf ~/.cache/pypoetry
poetry install --no-cache

# If still failing, try with verbose output
poetry install -vvv

# For dependency conflicts, check pyproject.toml
poetry show --tree
```

**Prevention**:
- Pin dependency versions in `pyproject.toml`
- Use `poetry lock` to generate consistent lock file
- Test in clean environment before committing

#### 2. Database Connection Issues

**Problem**: Cannot connect to PostgreSQL database

**Symptoms**:
- `psycopg2.OperationalError: could not connect to server`
- `sqlalchemy.exc.OperationalError: connection refused`
- Database timeout errors

**Solutions**:

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL service
docker-compose restart postgres

# Check database logs
docker-compose logs postgres

# Verify connection string
echo $DATABASE_URL
# Should be: postgresql://dev:dev@localhost:5432/devcycle

# Test connection manually
psql postgresql://dev:dev@localhost:5432/devcycle
```

**Configuration Check**:
```python
# Verify database configuration
from devcycle.core.config import settings
print(f"Database URL: {settings.database_url}")
print(f"Database pool size: {settings.database_pool_size}")
```

#### 3. Redis Connection Issues

**Problem**: Redis connection failures

**Symptoms**:
- `redis.exceptions.ConnectionError`
- Cache operations failing
- Session storage issues

**Solutions**:

```bash
# Check Redis status
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check Redis logs
docker-compose logs redis

# Test Redis connection
redis-cli -h localhost -p 6379 ping
# Should return: PONG
```

**Configuration Check**:
```python
# Test Redis connection
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(f"Redis ping: {r.ping()}")
```

#### 4. Kafka Connection Issues

**Problem**: Kafka broker connection failures

**Symptoms**:
- `kafka.errors.NoBrokersAvailable`
- Message publishing failures
- Consumer group issues

**Solutions**:

```bash
# Check Kafka status
docker-compose ps kafka

# Restart Kafka
docker-compose restart kafka

# Check Kafka logs
docker-compose logs kafka

# List topics
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check broker connectivity
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

#### 5. API Server Issues

**Problem**: FastAPI server won't start or crashes

**Symptoms**:
- `uvicorn` startup errors
- Port already in use errors
- Import errors on startup

**Solutions**:

```bash
# Check if port is in use
netstat -tulpn | grep :8000
# or on Windows
netstat -ano | findstr :8000

# Kill process using port (Linux/Mac)
sudo lsof -ti:8000 | xargs kill -9

# Kill process using port (Windows)
taskkill /PID <PID> /F

# Start server with debug logging
poetry run uvicorn devcycle.main:app --reload --log-level debug

# Check for import errors
poetry run python -c "from devcycle.main import app; print('Import successful')"
```

#### 6. Test Failures

**Problem**: Tests failing unexpectedly

**Symptoms**:
- Intermittent test failures
- Database-related test failures
- Timeout errors in tests

**Solutions**:

```bash
# Run tests with verbose output
poetry run pytest -vvv

# Run specific test with debugging
poetry run pytest tests/unit/test_agents.py::test_create_agent -vvv -s

# Check test database
poetry run pytest --setup-show

# Run tests with coverage
poetry run pytest --cov=devcycle --cov-report=html

# Check for test isolation issues
poetry run pytest --forked
```

**Common Test Issues**:

```python
# Database not cleaned between tests
@pytest.fixture(autouse=True)
def clean_database():
    # Clean database before each test
    yield
    # Clean database after each test

# Async test not properly awaited
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None

# Mock not properly configured
@patch('devcycle.core.agents.AgentRepository')
def test_with_mock(mock_repo):
    mock_repo.return_value.find_by_id.return_value = None
    # Test implementation
```

### Performance Issues

#### 1. Slow Database Queries

**Symptoms**:
- API response times > 1 second
- Database connection pool exhaustion
- High CPU usage on database server

**Diagnosis**:

```python
# Enable query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Profile slow queries
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log queries taking more than 100ms
        print(f"Slow query ({total:.2f}s): {statement}")
```

**Solutions**:

```python
# Add database indexes
from sqlalchemy import Index

# Create index on frequently queried columns
Index('idx_agent_status', Agent.status)
Index('idx_message_agent_id', Message.agent_id)
Index('idx_message_created_at', Message.created_at)

# Use eager loading to avoid N+1 queries
agents = session.query(Agent).options(
    joinedload(Agent.messages)
).filter(Agent.status == 'online').all()

# Use database connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

#### 2. Memory Leaks

**Symptoms**:
- Increasing memory usage over time
- Out of memory errors
- Slow performance after extended use

**Diagnosis**:

```python
# Monitor memory usage
import psutil
import gc

def log_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

# Check for circular references
import gc
print(f"Garbage collection: {gc.collect()} objects collected")

# Profile memory usage
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Function implementation
    pass
```

**Solutions**:

```python
# Properly close database connections
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Use weak references for caches
import weakref

class AgentCache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, value):
        self._cache[key] = value

# Clear caches periodically
import threading
import time

def clear_caches_periodically():
    while True:
        time.sleep(3600)  # Clear every hour
        cache.clear()
        gc.collect()

threading.Thread(target=clear_caches_periodically, daemon=True).start()
```

#### 3. API Rate Limiting Issues

**Symptoms**:
- 429 Too Many Requests errors
- Slow API responses
- Client timeout errors

**Solutions**:

```python
# Implement proper rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limiting to endpoints
@app.post("/api/v1/agents")
@limiter.limit("10/minute")
async def create_agent(request: Request, agent_data: AgentCreate):
    pass

# Implement exponential backoff for clients
import time
import random

def exponential_backoff(attempt, base_delay=1, max_delay=60):
    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
    time.sleep(delay)
```

### Debugging Techniques

#### 1. Logging Configuration

```python
# Configure structured logging
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/devcycle.log')
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

#### 2. Debug Mode

```python
# Enable debug mode for development
import os
from devcycle.core.config import settings

if settings.debug:
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Enable SQLAlchemy query logging
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # Enable FastAPI debug mode
    app.debug = True
```

#### 3. Error Tracking

```python
# Integrate with Sentry for error tracking
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[
        FastApiIntegration(auto_enabling_instrumentations=True),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,
    environment=settings.environment
)
```

## Development Best Practices

### Code Organization

#### 1. Project Structure

```
devcycle/
├── devcycle/                 # Main application package
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection
│   │   ├── agents/          # Agent management
│   │   ├── messages/        # Message handling
│   │   └── utils/           # Utility functions
│   ├── api/                 # API layer
│   │   ├── __init__.py
│   │   ├── routes/          # Route handlers
│   │   ├── models/          # Pydantic models
│   │   └── middleware/      # Custom middleware
│   └── tests/               # Test files
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── config/                  # Configuration files
├── pyproject.toml          # Project dependencies
├── docker-compose.yml      # Docker services
└── README.md               # Project documentation
```

#### 2. Module Design

```python
# Single Responsibility Principle
class AgentManager:
    """Manages agent lifecycle and operations."""

    def __init__(self, repository: AgentRepository):
        self.repository = repository

    def create_agent(self, data: AgentCreate) -> Agent:
        """Create a new agent."""
        pass

    def get_agent(self, agent_id: str) -> Agent:
        """Get agent by ID."""
        pass

class MessageRouter:
    """Routes messages to appropriate agents."""

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager

    def route_message(self, message: Message) -> str:
        """Route message to best available agent."""
        pass
```

### Error Handling

#### 1. Custom Exceptions

```python
# Define custom exception hierarchy
class DevCycleError(Exception):
    """Base exception for DevCycle application."""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(DevCycleError):
    """Raised when data validation fails."""
    pass

class AgentNotFoundError(DevCycleError):
    """Raised when an agent cannot be found."""
    pass

class MessageProcessingError(DevCycleError):
    """Raised when message processing fails."""
    pass
```

#### 2. Error Response Format

```python
from fastapi import HTTPException, status
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str
    error_code: str = None
    details: dict = None
    timestamp: datetime

def create_error_response(
    error: str,
    message: str,
    status_code: int = 500,
    error_code: str = None,
    details: dict = None
) -> HTTPException:
    """Create standardized error response."""
    return HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=error,
            message=message,
            error_code=error_code,
            details=details,
            timestamp=datetime.utcnow()
        ).dict()
    )
```

### Configuration Management

#### 1. Environment-based Configuration

```python
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    app_name: str = "DevCycle API"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Database settings
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")

    # Redis settings
    redis_url: str = Field(..., env="REDIS_URL")
    redis_ttl: int = Field(default=3600, env="REDIS_TTL")

    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration: int = Field(default=900, env="JWT_EXPIRATION")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

#### 2. Configuration Validation

```python
def validate_configuration():
    """Validate application configuration."""
    errors = []

    # Check required settings
    if not settings.database_url:
        errors.append("DATABASE_URL is required")

    if not settings.secret_key:
        errors.append("SECRET_KEY is required")

    # Validate database URL format
    if not settings.database_url.startswith(('postgresql://', 'sqlite://')):
        errors.append("Invalid DATABASE_URL format")

    # Validate JWT settings
    if settings.jwt_expiration < 60:
        errors.append("JWT_EXPIRATION must be at least 60 seconds")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
```

## Code Review Guidelines

### Review Checklist

#### For Authors

- [ ] **Code Quality**
  - [ ] Follows project coding standards
  - [ ] No code duplication
  - [ ] Proper error handling
  - [ ] Input validation implemented
  - [ ] No hardcoded values

- [ ] **Testing**
  - [ ] Unit tests written and passing
  - [ ] Integration tests updated
  - [ ] Test coverage maintained
  - [ ] Edge cases covered

- [ ] **Documentation**
  - [ ] Docstrings for public functions
  - [ ] README updated if needed
  - [ ] API documentation updated
  - [ ] Comments for complex logic

- [ ] **Security**
  - [ ] No sensitive data in code
  - [ ] Input sanitization implemented
  - [ ] Authentication/authorization checked
  - [ ] SQL injection prevention

- [ ] **Performance**
  - [ ] Database queries optimized
  - [ ] Caching implemented where appropriate
  - [ ] Memory usage considered
  - [ ] Async operations used correctly

#### For Reviewers

- [ ] **Functionality**
  - [ ] Code works as intended
  - [ ] Edge cases handled
  - [ ] Error scenarios covered
  - [ ] Performance acceptable

- [ ] **Maintainability**
  - [ ] Code is readable and clear
  - [ ] Functions are focused and small
  - [ ] Dependencies are minimal
  - [ ] Refactoring opportunities identified

- [ ] **Architecture**
  - [ ] Follows established patterns
  - [ ] Separation of concerns maintained
  - [ ] No circular dependencies
  - [ ] Proper abstraction levels

### Review Process

#### 1. Initial Review

- **Timeline**: Within 24 hours
- **Focus**: High-level architecture and functionality
- **Actions**: Approve, request changes, or ask questions

#### 2. Detailed Review

- **Timeline**: Within 48 hours
- **Focus**: Code quality, testing, and security
- **Actions**: Provide specific feedback and suggestions

#### 3. Final Review

- **Timeline**: Within 4 hours of changes
- **Focus**: Verify all feedback addressed
- **Actions**: Approve for merge

### Review Best Practices

#### 1. Constructive Feedback

```markdown
# Good feedback
The error handling here could be more specific. Consider catching
ValidationError separately from generic exceptions to provide
better error messages to users.

# Bad feedback
This is wrong.
```

#### 2. Specific Suggestions

```markdown
# Good feedback
Line 45: The variable name `data` is too generic. Consider
renaming to `agent_config` to be more descriptive.

# Bad feedback
Variable names are confusing.
```

#### 3. Learning Opportunities

```markdown
# Good feedback
This is a great use of the repository pattern! For consistency,
consider applying the same pattern to the MessageService class.

# Bad feedback
This pattern is wrong.
```

## Performance Optimization

### Database Optimization

#### 1. Query Optimization

```python
# Use indexes for frequently queried columns
from sqlalchemy import Index

Index('idx_agent_status_created', Agent.status, Agent.created_at)
Index('idx_message_agent_priority', Message.agent_id, Message.priority)

# Use eager loading to avoid N+1 queries
agents = session.query(Agent).options(
    joinedload(Agent.messages),
    joinedload(Agent.configuration)
).filter(Agent.status == 'online').all()

# Use database-level pagination
def get_agents_paginated(page: int, size: int):
    offset = (page - 1) * size
    return session.query(Agent).offset(offset).limit(size).all()
```

#### 2. Connection Pooling

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Base number of connections
    max_overflow=30,        # Additional connections when needed
    pool_pre_ping=True,     # Validate connections before use
    pool_recycle=3600       # Recycle connections every hour
)
```

### Caching Strategies

#### 1. Application-level Caching

```python
from functools import lru_cache
import redis

# In-memory caching for frequently accessed data
@lru_cache(maxsize=1000)
def get_agent_type_capabilities(agent_type: str) -> List[str]:
    """Get capabilities for an agent type (cached)."""
    return database.query(Capability).filter_by(agent_type=agent_type).all()

# Redis caching for shared data
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_agent_by_id_cached(agent_id: str) -> Optional[Agent]:
    """Get agent by ID with Redis caching."""
    cache_key = f"agent:{agent_id}"

    # Try cache first
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return Agent.parse_raw(cached_data)

    # Fetch from database
    agent = database.query(Agent).filter_by(id=agent_id).first()
    if agent:
        # Cache for 1 hour
        redis_client.setex(cache_key, 3600, agent.json())

    return agent
```

#### 2. Cache Invalidation

```python
def update_agent(agent_id: str, data: dict) -> Agent:
    """Update agent and invalidate cache."""
    agent = database.query(Agent).filter_by(id=agent_id).first()
    if agent:
        # Update database
        for key, value in data.items():
            setattr(agent, key, value)
        database.commit()

        # Invalidate cache
        cache_key = f"agent:{agent_id}"
        redis_client.delete(cache_key)

        # Invalidate related caches
        redis_client.delete(f"agent_capabilities:{agent.type}")

    return agent
```

### Async Programming

#### 1. Proper Async Usage

```python
import asyncio
from typing import List

async def process_messages_concurrently(messages: List[Message]) -> List[ProcessingResult]:
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

async def process_single_message(message: Message) -> ProcessingResult:
    """Process a single message asynchronously."""
    try:
        # Simulate async I/O operation
        await asyncio.sleep(0.1)
        return ProcessingResult(success=True, message_id=message.id)
    except Exception as e:
        return ProcessingResult(success=False, error=str(e))
```

#### 2. Async Database Operations

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    pool_size=20,
    max_overflow=30
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_agent_async(agent_id: str) -> Optional[Agent]:
    """Get agent asynchronously."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
```

## Security Guidelines

### Input Validation

#### 1. Pydantic Models

```python
from pydantic import BaseModel, Field, validator
import re

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., regex=r'^[a-z_]+$')
    description: Optional[str] = Field(None, max_length=500)

    @validator('name')
    def validate_name(cls, v):
        # Prevent SQL injection and XSS
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        if v:
            # Remove potentially dangerous HTML tags
            v = re.sub(r'<[^>]+>', '', v)
            # Limit length
            if len(v) > 500:
                raise ValueError('Description too long')
        return v
```

#### 2. SQL Injection Prevention

```python
# Use parameterized queries
def get_agents_by_type(agent_type: str) -> List[Agent]:
    """Get agents by type (SQL injection safe)."""
    return session.query(Agent).filter(Agent.type == agent_type).all()

# Bad - vulnerable to SQL injection
def get_agents_by_type_unsafe(agent_type: str) -> List[Agent]:
    query = f"SELECT * FROM agents WHERE type = '{agent_type}'"
    return session.execute(query).fetchall()
```

### Authentication and Authorization

#### 1. JWT Token Validation

```python
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user
```

#### 2. Role-based Access Control

```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"

def require_role(required_role: UserRole):
    """Decorator to require specific role."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user or user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/api/v1/agents/{agent_id}")
@require_role(UserRole.ADMIN)
async def delete_agent(agent_id: str, current_user: User = Depends(get_current_user)):
    pass
```

### Data Protection

#### 1. Sensitive Data Handling

```python
import logging
from typing import Any, Dict

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data from logs."""
    sensitive_keys = ['password', 'token', 'secret', 'key', 'auth']
    sanitized = {}

    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized

def log_agent_activity(agent_id: str, action: str, data: Dict[str, Any]):
    """Log agent activity without sensitive data."""
    sanitized_data = sanitize_log_data(data)
    logger.info(f"Agent {agent_id} performed {action}: {sanitized_data}")
```

#### 2. Environment Variables

```python
# Never hardcode secrets
# Bad
SECRET_KEY = "my-secret-key-123"

# Good
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

# Use different secrets for different environments
class Settings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    database_password: str = Field(..., env="DATABASE_PASSWORD")
    redis_password: str = Field(..., env="REDIS_PASSWORD")

    class Config:
        env_file = ".env"
```

## Testing Guidelines

### Test Structure

#### 1. Test Organization

```
tests/
├── unit/                    # Unit tests
│   ├── test_agents.py
│   ├── test_messages.py
│   └── test_utils.py
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_redis.py
├── e2e/                     # End-to-end tests
│   ├── test_agent_workflow.py
│   └── test_message_flow.py
└── conftest.py              # Shared fixtures
```

#### 2. Test Fixtures

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devcycle.main import app
from devcycle.core.database import get_db, Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### Test Best Practices

#### 1. Test Naming

```python
# Good - descriptive test names
def test_create_agent_with_valid_data_returns_agent():
    pass

def test_create_agent_with_invalid_type_raises_validation_error():
    pass

def test_get_agent_returns_none_when_agent_not_found():
    pass

# Bad - generic test names
def test_create_agent():
    pass

def test_get_agent():
    pass
```

#### 2. Test Data Management

```python
# Use factories for test data
import factory
from devcycle.core.models import Agent

class AgentFactory(factory.Factory):
    class Meta:
        model = Agent

    name = factory.Sequence(lambda n: f"test_agent_{n}")
    type = "business_analyst"
    status = "registered"
    version = "1.0.0"

# Use in tests
def test_agent_creation():
    agent_data = AgentFactory.build()
    result = create_agent(agent_data.dict())
    assert result.name == agent_data.name
```

#### 3. Mocking External Dependencies

```python
from unittest.mock import Mock, patch

def test_send_message_with_mock_agent():
    # Mock external service
    with patch('devcycle.core.agents.AgentService') as mock_service:
        mock_service.return_value.send_message.return_value = "success"

        result = send_message("agent_123", "test_action", {})

        assert result == "success"
        mock_service.return_value.send_message.assert_called_once()
```

## Documentation Guidelines

### Code Documentation

#### 1. Docstring Standards

```python
def process_message(
    message: Message,
    agent_id: str,
    timeout: int = 30
) -> ProcessingResult:
    """Process a message through the specified agent.

    This function routes a message to the specified agent and waits for
    the processing to complete within the given timeout period.

    Args:
        message: The message to be processed
        agent_id: Unique identifier of the target agent
        timeout: Maximum time to wait for processing (seconds)

    Returns:
        ProcessingResult containing the processing outcome and any
        generated data or error information

    Raises:
        AgentNotFoundError: If the specified agent doesn't exist
        MessageValidationError: If the message format is invalid
        TimeoutError: If processing exceeds the timeout period

    Example:
        >>> message = Message(content="Analyze this requirement")
        >>> result = process_message(message, "agent_123", timeout=60)
        >>> print(result.status)
        completed
    """
    pass
```

#### 2. Type Hints

```python
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

def get_agents(
    agent_type: Optional[str] = None,
    status: Union[str, List[str]] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Agent]:
    """Get agents with optional filtering and pagination."""
    pass

def create_agent_config(
    config_data: Dict[str, Any],
    validate: bool = True
) -> AgentConfiguration:
    """Create agent configuration from data dictionary."""
    pass
```

### API Documentation

#### 1. OpenAPI Documentation

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="DevCycle API",
    description="AI-Powered Application Development Lifecycle Automation System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class AgentCreate(BaseModel):
    name: str = Field(..., description="Unique agent name", example="business_analyst_01")
    type: str = Field(..., description="Agent type", example="business_analyst")
    description: Optional[str] = Field(None, description="Agent description", max_length=500)

@app.post(
    "/api/v1/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent",
    description="Register a new agent with the system",
    responses={
        201: {"description": "Agent created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Agent name already exists"}
    }
)
async def create_agent(agent_data: AgentCreate):
    """Create a new agent.

    This endpoint allows you to register a new agent with the DevCycle system.
    The agent will be created in 'registered' status and can be activated
    through the lifecycle management endpoints.
    """
    pass
```

#### 2. README Documentation

```markdown
# DevCycle API

AI-Powered Application Development Lifecycle Automation System

## Quick Start

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Set up environment**:
   ```bash
   cp config/development.env.example config/development.env
   # Edit configuration as needed
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Run the application**:
   ```bash
   poetry run uvicorn devcycle.main:app --reload
   ```

## API Documentation

- **Interactive docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Development

See [Development Guidelines](docs/development/guidelines.md) for detailed information about:
- Coding standards
- Development workflows
- Testing procedures
- Deployment processes
```

## Conclusion

Following these development guidelines ensures:

- **Consistent code quality** across the project
- **Efficient development workflows** for the team
- **Reliable troubleshooting** when issues arise
- **Secure and performant** application code
- **Comprehensive testing** and documentation

Remember: **Guidelines are living documents**. Update them as the project evolves and new best practices emerge. The goal is to make development more efficient and enjoyable for everyone on the team.
