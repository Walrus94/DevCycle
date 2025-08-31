# Kafka Setup for DevCycle

This document describes how to set up and run Kafka locally for DevCycle development using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB of available RAM
- Ports 9092 available (and optionally 8080 for dev tools)

## Quick Start

### Option 1: Using the startup script (Recommended)

**Linux/macOS:**
```bash
chmod +x scripts/start-kafka.sh
./scripts/start-kafka.sh
```

**Windows:**
```cmd
scripts\start-kafka.bat
```

### Option 2: Manual Docker Compose

```bash
# Start Kafka (KRaft mode)
docker-compose up -d kafka

# Start with development tools
docker-compose --profile dev up -d
```

## Services

### Core Services (Always Running)

- **Kafka** (Port 9092): Message broker running in KRaft mode (no Zookeeper required)

### Development Services (Optional)

- **Kafka UI** (Port 8080): Web interface for managing topics and messages

## Configuration

The Kafka configuration is optimized for local development:

- **KRaft Mode**: Modern Kafka without Zookeeper dependency
- **Auto-create topics**: Enabled for easier development
- **Single broker**: Sufficient for local development
- **Data retention**: 7 days (configurable)
- **Health checks**: Built-in to ensure services are ready

## Usage

### Basic Kafka Operations

```bash
# List topics
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create a topic
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic test-topic --partitions 3 --replication-factor 1

# View topic details
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic test-topic
```

### DevCycle Configuration

Update your DevCycle configuration to use Kafka:

```python
from devcycle.core.messaging.config import MessagingConfig, KafkaConfig

config = MessagingConfig(
    backend="kafka",
    kafka=KafkaConfig(
        bootstrap_servers="localhost:9092",
        topic_prefix="devcycle",
        consumer_group="devcycle-consumer"
    )
)
```

## Management

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f kafka
```

### Reset Data
```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: This deletes all data)
docker-compose down -v

# Restart
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Check if another service is using port 9092
2. **Kafka not ready**: Wait for health checks to complete (usually 30-60 seconds)
3. **Memory issues**: Ensure Docker has at least 4GB RAM allocated

### Health Check

```bash
# Check service status
docker-compose ps

# Check Kafka readiness
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Logs

```bash
# Check for errors
docker-compose logs kafka | grep ERROR
```

## Production Considerations

This setup is for development only. For production:

- Use multiple Kafka brokers for redundancy
- Configure proper security (SASL, SSL)
- Set appropriate retention policies
- Monitor resource usage
- Consider using external KRaft cluster

## Next Steps

1. Test your DevCycle application with Kafka
2. Monitor message flow through Kafka UI
3. Configure proper topic naming conventions
4. Set up monitoring and alerting
