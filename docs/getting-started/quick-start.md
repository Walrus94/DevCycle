# Quick Start Guide

Get up and running with DevCycle in minutes!

## Prerequisites

- **Python 3.9+** installed
- **Docker** and **Docker Compose** installed
- **Git** installed

## 1. Clone the Repository

```bash
git clone <repository-url>
cd DevCycle
```

## 2. Install Dependencies

=== "Poetry (Recommended)"

    ```bash
    # Install Poetry if you haven't already
    curl -sSL https://install.python-poetry.org | python3 -

    # Install project dependencies
    poetry install
    ```

=== "pip"

    ```bash
    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt
    ```

## 3. Set Up Environment

```bash
# Set environment to development
export ENVIRONMENT=development

# Or create a .env file
echo "ENVIRONMENT=development" > .env
```

## 4. Start Services

```bash
# Start all services (PostgreSQL, Redis, Kafka)
docker-compose up -d

# Verify services are running
docker-compose ps
```

## 5. Initialize Database

```bash
# Run database migrations
poetry run alembic upgrade head

# Verify database connection
poetry run python -c "from devcycle.core.database.connection import get_engine; print('✅ Database connected!')"
```

## 6. Start the Application

```bash
# Start the API server
poetry run uvicorn devcycle.api.app:app --reload
```

## 7. Verify Installation

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Version Info**: http://localhost:8000/api/version

## What's Next?

- **[Installation Guide](installation.md)** - Detailed setup instructions
- **[Development Setup](development-setup.md)** - Configure your development environment
- **[API Documentation](../api/overview.md)** - Explore the REST API
- **[Architecture Overview](../architecture/overview.md)** - Understand the system design

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
poetry run uvicorn devcycle.api.app:app --reload --port 8001
```

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart database service
docker-compose restart postgres
```

**Dependencies not found:**
```bash
# Reinstall dependencies
poetry install --sync

# Or with pip
pip install -r requirements.txt --force-reinstall
```

### Getting Help

- Check the [Troubleshooting Guide](../operations/troubleshooting.md)
- Review [Common Issues](../operations/common-issues.md)
- Open an [Issue](https://github.com/devcycle/devcycle/issues)
