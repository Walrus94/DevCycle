"""
Testcontainers configuration for DevCycle tests.

This module provides PostgreSQL test containers for integration and E2E testing.
"""

import sys

print(f"Python version: {sys.version}")
print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries

from typing import Dict

print("Importing testcontainers...")

try:
    from testcontainers.postgres import PostgresContainer

    print("testcontainers.postgres imported successfully")
except ImportError as e:
    print(f"ERROR importing testcontainers.postgres: {e}")
    raise


def get_postgres_container():
    """Get a real PostgreSQL container for testing."""
    print("Creating PostgresContainer configuration...")
    print("  - Image: postgres:15")
    print("  - Username: test")
    print("  - Password: test")
    print("  - Database: test_db")
    print("  - Port: None (let testcontainers choose)")

    # Let testcontainers choose an available port automatically
    container = PostgresContainer(
        image="postgres:15",
        username="test",
        password="test",
        dbname="test_db"
        # Remove port specification to let testcontainers choose automatically
    )

    print("PostgresContainer created successfully")
    return container


def get_postgres_connection_info(postgres) -> Dict[str, str]:
    """Get PostgreSQL connection information for testing."""
    print("Getting PostgreSQL connection information...")

    host = postgres.get_container_host_ip()
    port = postgres.get_exposed_port(5432)
    url = postgres.get_connection_url()

    print(f"  - Host: {host}")
    print(f"  - Port: {port}")
    print(f"  - URL: {url}")

    conn_info = {
        "host": host,
        "port": str(port),
        "username": "test",
        "password": "test",
        "database": "test_db",
        "url": url,
    }

    print("Connection information retrieved successfully")
    return conn_info
