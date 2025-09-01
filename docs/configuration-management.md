# Configuration Management

DevCycle uses a unified, environment-aware configuration system built on Pydantic Settings. This system consolidates all configuration sources into a single, validated approach.

## Overview

The configuration system provides:

- **Environment-specific configurations** (development, testing, production, staging)
- **Type validation** with Pydantic
- **Environment variable support** with proper prefixes
- **Configuration validation** and error handling
- **Centralized configuration management**

## Configuration Structure

### Main Configuration Classes

- `DevCycleConfig` - Main configuration class
- `DatabaseConfig` - Database connection settings
- `SecurityConfig` - Security and authentication settings
- `APIConfig` - API server configuration
- `LoggingConfig` - Logging system settings
- `RedisConfig` - Redis connection settings
- `HuggingFaceConfig` - Hugging Face integration settings
- `AgentConfig` - AI agent configuration
- `DockerConfig` - Docker services configuration
- `TestConfig` - Testing environment settings

### Environment Support

The system supports four environments:

- **development** - Local development settings
- **testing** - Test environment settings
- **staging** - Staging environment settings
- **production** - Production environment settings

## Configuration Files

Environment-specific configuration files are located in the `config/` directory:

- `config/development.env` - Development environment settings
- `config/testing.env` - Testing environment settings
- `config/production.env` - Production environment settings
- `config/staging.env` - Staging environment settings (optional)

## Usage

### Basic Usage

```python
from devcycle.core.config import get_config, get_environment, is_development

# Get the global configuration instance
config = get_config()

# Check current environment
print(f"Environment: {get_environment()}")
print(f"Is development: {is_development()}")

# Access configuration values
print(f"Database host: {config.database.host}")
print(f"API port: {config.api.port}")
print(f"Secret key: {config.security.secret_key}")
```

### Environment-Specific Configuration

```python
from devcycle.core.config import create_config_with_environment

# Create configuration for specific environment
test_config = create_config_with_environment('testing')
print(f"Test database URL: {test_config.get_async_database_url()}")
```

### Environment Detection

The system automatically detects the environment from the `ENVIRONMENT` environment variable:

```bash
# Set environment
export ENVIRONMENT=production

# Or in your .env file
ENVIRONMENT=production
```

## Configuration Validation

The system includes built-in validation:

### Production Safety

- **Secret key validation** - Prevents default secret keys in production
- **Database password validation** - Requires passwords in production
- **Debug mode validation** - Prevents debug mode in production

### Type Validation

All configuration values are validated for correct types:

```python
# This will raise a validation error
config = DevCycleConfig(api_port="invalid")  # Should be int
```

## Environment Variables

Configuration values can be overridden using environment variables with appropriate prefixes:

### Database Configuration

```bash
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_DATABASE=devcycle
```

### Security Configuration

```bash
SECURITY_SECRET_KEY=your-secret-key
SECURITY_ALGORITHM=HS256
SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### API Configuration

```bash
API_HOST=127.0.0.1
API_PORT=8000
API_RELOAD=true
API_CORS_ORIGINS=["*"]
```

### Logging Configuration

```bash
LOG_LEVEL=INFO
LOG_JSON_OUTPUT=true
LOG_LOG_FILE=logs/app.log
```

## Docker Integration

The configuration system integrates with Docker Compose:

```yaml
# docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_DB: ${DOCKER_POSTGRES_DB:-devcycle}
      POSTGRES_USER: ${DOCKER_POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${DOCKER_POSTGRES_PASSWORD:-devcycle123}
```

## Migration from Old System

The old `config.env.template` system has been replaced. To migrate:

1. **Remove old files**:
   - `config.env.template`
   - `config.env` (if exists)

2. **Use new environment files**:
   - Copy values from old template to appropriate environment files
   - Update variable names to use new prefixes (e.g., `POSTGRES_*` → `DOCKER_POSTGRES_*`)

3. **Update environment variables**:
   - Set `ENVIRONMENT` variable to specify which config to use
   - Update any scripts that reference old configuration files

## Best Practices

### Development

- Use `config/development.env` for local development
- Set `ENVIRONMENT=development`
- Enable debug mode and verbose logging

### Testing

- Use `config/testing.env` for test environments
- Set `ENVIRONMENT=testing`
- Use separate test database and faster timeouts

### Production

- Use `config/production.env` for production
- Set `ENVIRONMENT=production`
- Ensure all security settings are properly configured
- Use strong secret keys and passwords

### Security

- Never commit production configuration files
- Use environment variables for sensitive data
- Regularly rotate secret keys and passwords
- Validate all configuration values

## Troubleshooting

### Common Issues

1. **Configuration not loading**:
   - Check that `ENVIRONMENT` variable is set correctly
   - Verify configuration file exists in `config/` directory
   - Check file permissions and syntax

2. **Validation errors**:
   - Ensure all required fields are set
   - Check data types match expected values
   - Verify environment-specific requirements

3. **Environment detection issues**:
   - Check `ENVIRONMENT` variable is set
   - Verify environment name matches supported values
   - Check for typos in environment names

### Debug Configuration

```python
from devcycle.core.config import get_config

config = get_config()
print(f"Current environment: {config.environment}")
print(f"Debug mode: {config.debug}")
print(f"Configuration: {config.model_dump()}")
```

## API Reference

### Main Functions

- `get_config()` - Get global configuration instance
- `get_environment()` - Get current environment
- `is_development()` - Check if in development
- `is_production()` - Check if in production
- `is_testing()` - Check if in testing
- `reload_config()` - Reload configuration from environment

### Environment Loader Functions

- `create_config_with_environment(env)` - Create config for specific environment
- `setup_environment_config(env)` - Setup environment variables
- `list_available_environments()` - List available environment configs
- `validate_environment_config(env)` - Validate environment config

### Configuration Classes

All configuration classes inherit from `BaseSettings` and support:

- Environment variable loading with prefixes
- Type validation
- Default values
- Custom validation methods
- Property methods for computed values
