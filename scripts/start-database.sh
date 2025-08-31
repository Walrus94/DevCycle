#!/bin/bash

echo "Starting DevCycle Database Services..."
echo

# Load environment variables from config.env if it exists
if [ -f "config.env" ]; then
    echo "Loading environment variables from config.env..."
    export $(grep -v '^#' config.env | xargs)
fi

# Set default values if not defined
export POSTGRES_DB=${POSTGRES_DB:-devcycle}
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-devcycle123}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export PGADMIN_EMAIL=${PGADMIN_EMAIL:-admin@devcycle.dev}
export PGADMIN_PASSWORD=${PGADMIN_PASSWORD:-admin123}

echo "Starting PostgreSQL and pgAdmin..."
docker-compose up -d postgres pgadmin

echo
echo "Waiting for PostgreSQL to be ready..."
sleep 10

echo
echo "Database services started!"
echo
echo "PostgreSQL: localhost:${POSTGRES_PORT}"
echo "  - Database: ${POSTGRES_DB}"
echo "  - Username: ${POSTGRES_USER}"
echo "  - Password: ${POSTGRES_PASSWORD}"
echo
echo "pgAdmin: http://localhost:5050"
echo "  - Email: ${PGADMIN_EMAIL}"
echo "  - Password: ${PGADMIN_PASSWORD}"
echo
echo "Default users:"
echo "  - admin/admin123 (admin role)"
echo "  - user/user123 (user role)"
echo
