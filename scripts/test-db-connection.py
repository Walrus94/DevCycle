#!/usr/bin/env python3
"""
Test database connection script for DevCycle.

This script tests the database connection using environment variables
and displays the connection status.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_env_file(env_file: str = "config.env") -> None:
    """Load environment variables from config.env file."""
    env_path = project_root / env_file
    if env_path.exists():
        print(f"Loading environment variables from {env_file}...")
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value
        print("Environment variables loaded successfully.")
    else:
        print(f"Warning: {env_file} not found. Using system environment variables.")


def test_database_connection() -> None:
    """Test the database connection."""
    try:
        from devcycle.core.database.connection import get_database_url, get_engine

        print("\nTesting database connection...")
        print(f"Database URL: {get_database_url()}")

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT version();")
            version = result.scalar()
            print(f"✅ Database connection successful!")
            print(f"PostgreSQL version: {version}")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory.")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your environment variables")
        print("3. Verify the database credentials")


def main() -> None:
    """Main function."""
    print("DevCycle Database Connection Test")
    print("=" * 40)

    # Load environment variables
    load_env_file()

    # Display current database configuration
    print("\nCurrent database configuration:")
    print(f"  Host: {os.getenv('DB_HOST', 'localhost')}")
    print(f"  Port: {os.getenv('DB_PORT', '5432')}")
    print(f"  Database: {os.getenv('DB_DATABASE', 'devcycle')}")
    print(f"  Username: {os.getenv('DB_USERNAME', 'postgres')}")
    print(
        f"  Password: {'*' * len(os.getenv('DB_PASSWORD', '')) if os.getenv('DB_PASSWORD') else '(none)'}"
    )

    # Test connection
    test_database_connection()


if __name__ == "__main__":
    main()
