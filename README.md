# DevCycle

AI-Powered Application Development Lifecycle Automation System

## Summary

DevCycle is a Proof of Concept (POC) that leverages multiple specialized AI agents to streamline software development processes. The system integrates multiple agents with different software development roles through Hugging Face Spaces, enabling automated requirements analysis, code generation with testing and deployment orchestration.

## Key Features

- Multi-Agent Architecture: Specialized AI agents for different development roles
- Automated Workflow: Streamlined development lifecycle automation
- Hugging Face Integration: Leverages Hugging Face Spaces for agent deployment
- End-to-End Process: From requirements analysis to deployment

## Technology Stack

- **Python 3.9+**
- **AI/ML**: Hugging Face, Transformers, PyTorch
- **Web Framework**: FastAPI, Uvicorn
- **Database**: PostgreSQL, SQLAlchemy, Alembic
- **Authentication**: FastAPI Users
- **Configuration**: Pydantic, Pydantic-settings
- **Logging**: Structlog (Kibana compatible)
- **Development Tools**: Poetry, Black, Flake8, Pytest, MyPy
- **Architecture**: Multi-agent system with orchestration

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DevCycle
   ```

2. **Set up virtual environment**
   ```bash
   # Using Poetry (recommended)
   poetry install

   # Or using pip
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Set environment (development, testing, production)
   export ENVIRONMENT=development

   # Or create a .env file
   echo "ENVIRONMENT=development" > .env
   ```

4. **Verify installation**
   ```bash
   python -c "import devcycle; print('DevCycle installed successfully!')"
   ```

## Configuration

DevCycle uses a unified, environment-aware configuration system. See [Configuration Management Guide](docs/configuration-management.md) for detailed instructions.

**Quick configuration:**
```bash
# Development (default)
export ENVIRONMENT=development

# Testing
export ENVIRONMENT=testing

# Production
export ENVIRONMENT=production
```

## Kafka Setup

DevCycle uses Apache Kafka for scalable agent communication. See [Kafka Setup Guide](docs/kafka-setup.md) for detailed instructions.

**Quick Kafka commands:**
```bash
# Start Kafka (KRaft mode - no Zookeeper needed)
docker-compose up -d

# View Kafka UI (optional)
docker-compose --profile dev up -d

# Stop services
docker-compose down
```

## Database Setup

DevCycle uses PostgreSQL with a unified architecture combining FastAPI Users and custom repositories. See [Database Setup Guide](docs/database-setup.md) for detailed instructions.

**Quick Database commands:**
```bash
# Start database services
scripts/start-database.bat  # Windows
./scripts/start-database.sh  # Linux/macOS

# Run migrations
poetry run alembic upgrade head

# Test connection
poetry run python -c "from devcycle.core.database.connection import get_engine; print('✅ Database connected!')"
```

**Architecture:**
- **FastAPI Users**: User authentication and management
- **Repository Pattern**: Agent and task management
- **Unified Models**: Consistent SQLAlchemy patterns
