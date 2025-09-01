# Database Setup Guide

This guide explains how to set up and configure the PostgreSQL database for DevCycle.

## Overview

DevCycle uses PostgreSQL as its primary database with the following components:
- **PostgreSQL 15**: Main database server
- **pgAdmin 4**: Web-based database management interface
- **Alembic**: Database migration management
- **SQLAlchemy**: ORM for database operations

## Quick Start

### 1. Start Database Services

#### Windows
```bash
scripts\start-database.bat
```

#### Linux/macOS
```bash
chmod +x scripts/start-database.sh
./scripts/start-database.sh
```

### 2. Verify Connection
```bash
# Test connection by running a simple query
poetry run python -c "
from devcycle.core.database.connection import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute('SELECT version();')
    print('✅ Database connection successful!')
    print(f'PostgreSQL version: {result.scalar()}')
"
```

## Configuration

### Environment Variables

The database configuration is managed through environment variables. Create a `config.env` file in the project root:

```bash
# PostgreSQL Database Configuration (for Docker Compose)
POSTGRES_DB=devcycle
POSTGRES_USER=postgres
POSTGRES_PASSWORD=devcycle123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# pgAdmin Configuration
PGADMIN_EMAIL=admin@devcycle.dev
PGADMIN_PASSWORD=admin123

# Database Configuration (for application - uses DB_ prefix)
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=devcycle123
DB_DATABASE=devcycle
```

### Application Configuration

The application uses the `DB_` prefixed variables:
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_USERNAME`: Database username (default: postgres)
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name (default: devcycle)

## Services

### PostgreSQL
- **Port**: 5432 (configurable via `POSTGRES_PORT`)
- **Database**: devcycle (configurable via `POSTGRES_DB`)
- **Username**: postgres (configurable via `POSTGRES_USER`)
- **Password**: devcycle123 (configurable via `POSTGRES_PASSWORD`)

### pgAdmin
- **URL**: http://localhost:5050
- **Email**: admin@devcycle.dev (configurable via `PGADMIN_EMAIL`)
- **Password**: admin123 (configurable via `PGADMIN_PASSWORD`)

## Database Schema

The unified database schema includes:

### Tables
- `user`: User accounts and profiles (FastAPI Users)
- `agents`: Agent management and health tracking
- `agent_tasks`: Agent task execution and results
- System uses structlog for logging instead of database audit logs

### Architecture
- **FastAPI Users**: Handles user authentication, registration, and management
- **Repository Pattern**: Custom repositories for agent and task management
- **Unified Base Model**: All models extend a common base for consistency

### Default Data
- **Default Users**:
  - `admin@devcycle.dev/admin123` (superuser)
  - `user@devcycle.dev/user123` (regular user)
- **User Roles**: Managed through FastAPI Users (is_superuser, is_active, is_verified)

## Development Workflow

### 1. Start Services
```bash
# Start only database services
docker-compose up -d postgres pgadmin

# Start all services (including Kafka)
docker-compose up -d
```

### 2. Run Migrations
```bash
# Apply all migrations
poetry run alembic upgrade head

# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Rollback migration
poetry run alembic downgrade -1
```

### 3. Test Connection
```bash
# Test connection by running a simple query
poetry run python -c "
from devcycle.core.database.connection import get_engine
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute('SELECT version();')
    print('✅ Database connection successful!')
    print(f'PostgreSQL version: {result.scalar()}')
"
```

## Troubleshooting

### Common Issues

#### Connection Refused
- Ensure PostgreSQL container is running: `docker ps`
- Check if port 5432 is available: `netstat -an | grep 5432`

#### Authentication Failed
- Verify credentials in `config.env`
- Check if the database exists: `docker exec -it devcycle-postgres psql -U postgres -l`

#### Migration Errors
- Ensure database is running before running migrations
- Check Alembic configuration in `alembic/env.py`

### Useful Commands

```bash
# View container logs
docker logs devcycle-postgres

# Access PostgreSQL shell
docker exec -it devcycle-postgres psql -U postgres -d devcycle

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d postgres
```

## Production Considerations

For production deployments:

1. **Change Default Passwords**: Update all default credentials
2. **Secure Network**: Use internal Docker networks, not port exposure
3. **Backup Strategy**: Implement regular database backups
4. **Monitoring**: Add database monitoring and alerting
5. **SSL**: Enable SSL connections for database security

## Next Steps

After setting up the database:

1. [Run Database Migrations](../migrations/README.md)
2. [Configure User Management](../user-management/README.md)
3. [Set Up Authentication](../authentication/README.md)
4. [Test the API](../api-testing/README.md)
