# DevCycle Testing Guide

This document explains how to run tests in the DevCycle project, including strategies to avoid terminal freezing issues with E2E tests.

## 🧪 Test Types

### 1. Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions and classes in isolation
- **Speed**: Fast execution
- **Dependencies**: Minimal, mostly mocked
- **Status**: ✅ Fully working

### 2. Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions
- **Speed**: Medium execution
- **Dependencies**: Some external services
- **Status**: ✅ Fully working

### 3. End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows
- **Speed**: Slow execution (requires database setup)
- **Dependencies**: PostgreSQL container, full application stack
- **Status**: ⚠️ Working but with batch limitations

## 🚀 Running Tests

### Option 1: Poetry Commands (Direct)

```bash
# Run all tests (may freeze terminal with E2E tests)
poetry run pytest

# Run specific test types
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v
poetry run pytest tests/e2e/ -v

# Run specific test file
poetry run pytest tests/e2e/test_auth_fastapi_users_e2e.py -v

# Run specific test method
poetry run pytest tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_registration_and_login_flow -v
```

### Option 2: Windows Batch File

```cmd
# Double-click or run from command line
run_tests.bat
```

## 📋 E2E Test Batches

Due to terminal freezing issues when running 4+ E2E tests together, tests are organized into batches:

### Batch 1: Core Authentication (2 tests)
- `test_user_registration_and_login_flow`
- `test_user_profile_management`

### Batch 2: User Management (3 tests)
- `test_multiple_user_sessions`
- `test_logout_and_token_invalidation`
- `test_debug_routes`

### Batch 3: Health Endpoints (4 tests)
- `test_health_check_endpoint`
- `test_detailed_health_check`
- `test_readiness_check`
- `test_liveness_check`

### Batch 4: Performance & SQLite (3 tests)
- `test_health_endpoints_consistency`
- `test_health_endpoints_performance`
- `test_auth_with_sqlite`

## ⏭️ Skipped Tests

The following tests are currently skipped (not yet implemented):
- `test_password_change_flow` - Password change functionality
- `test_user_deactivation` - User deactivation functionality

The following tests are temporarily skipped due to isolation issues:
- `test_jwt_token_validation` - Causes terminal freezing (investigating)

## 🔧 Test Configuration

### Environment Setup
- **Database**: PostgreSQL container via testcontainers
- **Isolation**: Transaction-based database isolation
- **Cleanup**: Comprehensive resource cleanup between tests
- **Timeouts**: 60-second timeouts for individual tests

### Test Isolation Features
- **Database**: Each test runs in a transaction that gets rolled back
- **Containers**: Fresh PostgreSQL container for each test session
- **Resources**: Aggressive cleanup of asyncio tasks, connections, and file handles
- **Delays**: 2-second delays between E2E test batches

## 🐛 Troubleshooting

### Terminal Freezing
**Problem**: Terminal freezes after running 3+ E2E tests together

**Solutions**:
1. **Use batch approach**: Run tests in batches of 3-4
2. **Run individual tests**: Use specific test paths
3. **Check resource cleanup**: Ensure Docker containers are stopped

### Database Connection Issues
**Problem**: Database connection errors or timeouts

**Solutions**:
1. **Check Docker**: Ensure Docker is running
2. **Clean containers**: `docker system prune -f`
3. **Restart tests**: Wait a few minutes and try again
4. **Check ports**: Ensure no port conflicts

### Test Failures
**Problem**: Tests fail intermittently

**Solutions**:
1. **Check isolation**: Ensure proper cleanup between tests
2. **Verify dependencies**: Check all required services are running
3. **Review logs**: Check test output for specific error messages
4. **Run individually**: Test specific failing tests in isolation

## 📊 Test Status

| Test Type | Status | Notes |
|-----------|--------|-------|
| Unit Tests | ✅ Working | All tests pass |
| Integration Tests | ✅ Working | All tests pass |
| E2E Tests | ⚠️ Working with batches | 3-4 tests per batch to avoid freezing |
| Security Tests | ✅ Working | All security features tested |

## 🎯 Best Practices

### For Development
1. **Run unit tests frequently** during development
2. **Use integration tests** for component testing
3. **Run E2E tests** before committing major changes
4. **Use batch approach** for E2E tests

### For CI/CD
1. **Run all tests** in sequence
2. **Use batch runner** for E2E tests
3. **Monitor resource usage** during test execution
4. **Set appropriate timeouts** for long-running tests

### For Debugging
1. **Run tests individually** to isolate issues
2. **Check test logs** for detailed error information
3. **Verify environment** (Docker, database, etc.)
4. **Use verbose output** (`-v` flag) for more details

## 🔄 Continuous Improvement

The testing strategy is continuously improved based on:
- **Performance metrics** from test runs
- **Failure patterns** and root cause analysis
- **Resource usage** monitoring
- **Developer feedback** and experience

## 📚 Additional Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Testcontainers**: https://testcontainers.com/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **SQLAlchemy Testing**: https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction
