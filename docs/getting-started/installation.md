# Installation Guide

Detailed installation instructions for DevCycle on different platforms and environments.

## System Requirements

### Minimum Requirements
- **Python**: 3.9 or higher
- **Memory**: 4GB RAM
- **Storage**: 2GB free space
- **Network**: Internet connection for dependencies

### Recommended Requirements
- **Python**: 3.11 or higher
- **Memory**: 8GB RAM
- **Storage**: 5GB free space
- **CPU**: Multi-core processor

## Platform-Specific Installation

### Windows

#### 1. Install Python

Download and install Python from [python.org](https://www.python.org/downloads/windows/):

```powershell
# Verify Python installation
python --version
pip --version
```

#### 2. Install Poetry

```powershell
# Using PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Add Poetry to PATH (restart terminal after this)
$env:PATH += ";$env:APPDATA\Python\Scripts"
```

#### 3. Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Install and start Docker Desktop
3. Verify installation:

```powershell
docker --version
docker-compose --version
```

#### 4. Install Git

Download and install [Git for Windows](https://git-scm.com/download/win):

```powershell
git --version
```

### macOS

#### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python

```bash
# Install Python
brew install python@3.11

# Verify installation
python3 --version
pip3 --version
```

#### 3. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### 4. Install Docker Desktop

```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app
```

### Linux (Ubuntu/Debian)

#### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Install Python

```bash
# Install Python and pip
sudo apt install python3.11 python3.11-venv python3-pip -y

# Verify installation
python3 --version
pip3 --version
```

#### 3. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 4. Install Docker

```bash
# Install Docker
sudo apt install docker.io docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker-compose --version
```

## Project Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd DevCycle
```

### 2. Install Dependencies

=== "Poetry (Recommended)"

    ```bash
    # Install all dependencies
    poetry install

    # Install development dependencies
    poetry install --with dev

    # Install documentation dependencies
    poetry install --with docs
    ```

=== "pip"

    ```bash
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt

    # Install development dependencies
    pip install -r requirements-dev.txt
    ```

### 3. Verify Installation

```bash
# Check if all dependencies are installed
poetry run python -c "import devcycle; print('✅ DevCycle installed successfully!')"

# Run basic tests
poetry run pytest tests/unit/test_basic.py -v
```

## Environment Configuration

### Development Environment

```bash
# Set environment
export ENVIRONMENT=development

# Or create .env file
cat > .env << EOF
ENVIRONMENT=development
DEBUG=true
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=devcycle123
DB_DATABASE=devcycle
EOF
```

### Testing Environment

```bash
# Set environment
export ENVIRONMENT=testing

# Or create .env file
cat > .env << EOF
ENVIRONMENT=testing
DEBUG=false
DB_HOST=localhost
DB_PORT=5434
DB_USERNAME=test_user
DB_PASSWORD=test_password
DB_DATABASE=devcycle_test
EOF
```

### Production Environment

```bash
# Set environment
export ENVIRONMENT=production

# Create production .env file
cat > .env << EOF
ENVIRONMENT=production
DEBUG=false
SECURITY_SECRET_KEY=your-very-secure-production-secret-key-here
DB_HOST=your-production-db-host
DB_PORT=5432
DB_USERNAME=your-production-db-user
DB_PASSWORD=your-secure-production-password
DB_DATABASE=devcycle_prod
REDIS_HOST=your-redis-host
REDIS_PASSWORD=your-redis-password
EOF
```

## Service Dependencies

### Start Required Services

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis kafka

# Check service status
docker-compose ps
```

### Service Health Checks

```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Check Redis
docker-compose exec redis redis-cli ping

# Check Kafka
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

## Database Setup

### Initialize Database

```bash
# Run migrations
poetry run alembic upgrade head

# Create initial data (optional)
poetry run python scripts/create_initial_data.py
```

### Verify Database

```bash
# Test database connection
poetry run python -c "
from devcycle.core.database.connection import get_engine
engine = get_engine()
print('✅ Database connected successfully!')
"
```

## Next Steps

After successful installation:

1. **[Development Setup](development-setup.md)** - Configure your development environment
2. **[Quick Start Guide](quick-start.md)** - Get up and running quickly
3. **[Configuration Guide](../operations/configuration.md)** - Detailed configuration options
4. **[API Documentation](../api/overview.md)** - Explore the REST API

## Troubleshooting

### Common Installation Issues

**Poetry installation fails:**
```bash
# Try alternative installation method
pip install poetry

# Or use pipx
pip install pipx
pipx install poetry
```

**Docker permission denied:**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Restart Docker Desktop (Windows/macOS)
```

**Python version conflicts:**
```bash
# Use specific Python version
poetry env use python3.11

# Or create virtual environment manually
python3.11 -m venv venv
source venv/bin/activate
```

### Getting Help

- Check the [Troubleshooting Guide](../operations/troubleshooting.md)
- Review [Common Issues](../operations/common-issues.md)
- Open an [Issue](https://github.com/devcycle/devcycle/issues)
