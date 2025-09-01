# DevCycle Test Suite

This directory contains the comprehensive test suite for DevCycle, organized by test type and functionality.

## Test Organization

### 📁 Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                 # Shared test configuration and fixtures
├── unit/                       # Unit tests (fast, isolated)
│   ├── conftest.py            # Unit test specific fixtures
│   ├── test_base_agent.py
│   ├── test_business_analyst.py
│   ├── test_error_handling.py
│   ├── test_huggingface.py
│   ├── test_logging.py
│   └── test_message_protocol.py
├── integration/                # Integration tests (component interaction)
│   ├── conftest.py            # Integration test specific fixtures
│   ├── test_kafka_messaging.py
│   └── test_kafka_routing.py
├── api/                       # API endpoint tests
│   ├── test_auth_endpoints.py
│   ├── test_auth_sessions.py
│   └── test_health.py
├── e2e/                       # End-to-end tests (testcontainers)
│   ├── conftest.py           # E2E-specific fixtures
│   └── test_auth_security_e2e.py
└── __pycache__/               # Python cache (ignored by git)
```

### 🏷️ Test Markers

Tests are categorized using `pytest` markers, defined in `pyproject.toml`. You can run specific sets of tests using these markers.

- **`@pytest.mark.unit`**: For fast, isolated tests that do not depend on external services or complex setups. Mocks are heavily used.
- **`@pytest.mark.integration`**: For tests that verify the interaction between several components, possibly using in-memory databases or mocked external services.
- **`@pytest.mark.e2e`**: For end-to-end tests that spin up real external services (like PostgreSQL and Redis) using `testcontainers` to test the complete system flow. These are typically slower.
- **`@pytest.mark.api`**: Specifically for tests related to FastAPI endpoints.
- **`@pytest.mark.auth`**: Specifically for authentication and security related tests.
- **`@pytest.mark.slow`**: Marks tests that are known to take a longer time to execute.

## How to Run Tests

Use pytest directly to run different test types:

```bash
# Run all unit tests
poetry run pytest tests/unit/ -v

# Run all integration tests
poetry run pytest tests/integration/ -v

# Run all API tests
poetry run pytest tests/api/ -v

# Run all end-to-end tests (requires Docker to be running)
poetry run pytest tests/e2e/ -v

# Run all tests (including E2E)
poetry run pytest tests/ -v

# Or use markers:
poetry run pytest -m unit
poetry run pytest -m "unit or integration"
poetry run pytest -m e2e --durations=10 # Show slowest 10 E2E tests
```

## Test Configuration

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions and classes in isolation
- **Dependencies**: Minimal, heavy use of mocks
- **Speed**: Fast execution
- **Configuration**: `tests/unit/conftest.py` provides unit-specific fixtures

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and workflows
- **Dependencies**: May use in-memory databases or mocked external services
- **Speed**: Medium execution time
- **Configuration**: `tests/integration/conftest.py` provides integration-specific fixtures

### API Tests (`tests/api/`)
- **Purpose**: Test FastAPI endpoints and API behavior
- **Dependencies**: Mocked database and Redis, FastAPI TestClient
- **Speed**: Fast execution
- **Configuration**: Uses main `tests/conftest.py` fixtures

### E2E Tests (`tests/e2e/`)
- **Purpose**: Test complete system integration
- **Dependencies**: Real PostgreSQL and Redis containers via testcontainers
- **Speed**: Slower execution (requires container startup)
- **Configuration**: `tests/e2e/conftest.py` provides testcontainer fixtures

## Fixture Organization

- **`tests/conftest.py`**: Shared fixtures available to all test types
- **`tests/unit/conftest.py`**: Unit test specific fixtures (minimal, fast)
- **`tests/integration/conftest.py`**: Integration test fixtures (component interaction)
- **`tests/e2e/conftest.py`**: E2E test fixtures (testcontainers, real services)

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Mock External Dependencies**: Use mocks for external services in unit and integration tests
3. **Real Services for E2E**: Only use real services (via testcontainers) in E2E tests
4. **Fast Execution**: Unit tests should run in milliseconds, integration tests in seconds
5. **Clear Naming**: Test files and functions should clearly indicate what they test
6. **Proper Markers**: Always use appropriate pytest markers for test categorization

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure the project root is in the Python path (handled by conftest.py files)
2. **Fixture Not Found**: Check that the fixture is defined in the appropriate conftest.py file
3. **Test Discovery**: Ensure test files follow the naming convention `test_*.py`
4. **Marker Warnings**: Verify that all markers are defined in `pyproject.toml`

### Running Specific Tests

```bash
# Run a specific test file
poetry run pytest tests/unit/test_base_agent.py

# Run a specific test class
poetry run pytest tests/unit/test_base_agent.py::TestBaseAgent

# Run a specific test method
poetry run pytest tests/unit/test_base_agent.py::TestBaseAgent::test_agent_creation

# Run tests matching a pattern
poetry run pytest -k "test_agent" tests/unit/
```
