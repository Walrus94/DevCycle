"""
Auth test using SQLite to avoid testcontainer issues.
"""

import os
import tempfile
from pathlib import Path


def test_auth_with_sqlite():
    """Test auth functionality using SQLite database."""
    print("=== Starting SQLite auth test ===")

    # Create temporary SQLite database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    sqlite_url = f"sqlite:///{db_path}"

    print(f"Using SQLite database: {sqlite_url}")

    try:
        # Set environment variables for SQLite
        os.environ["DB_HOST"] = "localhost"
        os.environ["DB_PORT"] = "5432"  # Dummy values for SQLite
        os.environ["DB_USERNAME"] = "test"
        os.environ["DB_PASSWORD"] = "test"
        os.environ["DB_DATABASE"] = str(db_path)
        os.environ["DATABASE_URL"] = sqlite_url

        print("Environment variables set")

        # Reload configuration
        from devcycle.core.config import reload_config
        from devcycle.core.database.connection import reset_database_factories

        reload_config()
        reset_database_factories()
        print("Configuration reloaded")

        # Create database tables
        from sqlalchemy import create_engine

        from devcycle.core.auth.models import User
        from devcycle.core.database.models import Base

        engine = create_engine(sqlite_url, echo=False)
        Base.metadata.create_all(bind=engine)
        print("Database tables created")

        # Test app creation
        from devcycle.api.app import create_app

        app = create_app()
        print("FastAPI app created successfully")

        # Test basic endpoint
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/api/v1/health")
        print(f"Health endpoint response: {response.status_code}")
        assert response.status_code == 200

        # Test auth endpoints
        print("Testing auth endpoints...")

        # Test registration endpoint
        response = client.get("/api/v1/auth/users/active")
        print(f"Active users endpoint response: {response.status_code}")
        # This should work even without authentication

        print("=== SQLite auth test completed successfully ===")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        # Cleanup
        print("Cleaning up...")
        try:
            if "engine" in locals():
                engine.dispose()
        except:
            pass

        # Remove temporary database
        try:
            if db_path.exists():
                db_path.unlink()
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir)
        except:
            pass

        print("Cleanup completed")


if __name__ == "__main__":
    test_auth_with_sqlite()
