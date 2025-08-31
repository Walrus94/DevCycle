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

3. **Verify installation**
   ```bash
   python -c "import devcycle; print('DevCycle installed successfully!')"
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
