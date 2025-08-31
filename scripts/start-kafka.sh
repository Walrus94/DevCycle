#!/bin/bash

# Start Kafka services for DevCycle development
echo "Starting Kafka services for DevCycle..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start Kafka (KRaft mode - no Zookeeper needed)
echo "Starting Kafka (KRaft mode)..."
docker-compose up -d kafka

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
until docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
    echo "Waiting for Kafka..."
    sleep 5
done

echo "Kafka is ready!"

# Check if dev profile is requested
if [[ "$1" == "--dev" ]]; then
    echo "Starting development services (Kafka UI)..."
    docker-compose --profile dev up -d
    echo ""
    echo "Services available at:"
    echo "  Kafka: localhost:9092"
    echo "  Kafka UI: http://localhost:8080"
else
    echo ""
    echo "Kafka is running at localhost:9092"
    echo "To start development services, run: $0 --dev"
fi

echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
