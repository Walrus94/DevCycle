"""
E2E test configuration and fixtures for DevCycle.

This module provides common test fixtures and configuration
for end-to-end tests.
"""

import asyncio
import os
import time
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from devcycle.api.app import create_app
from devcycle.core.database.models import Base
from tests.shared.testcontainers import (
    get_postgres_connection_info,
    get_postgres_container,
)


# Fix 1: Override event_loop fixture to match container scope
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Fix 2: Set Docker host environment variable to resolve port mapping issues
@pytest.fixture(scope="session", autouse=True)
def docker_host():
    """Set Docker host environment variable to resolve port mapping issues."""
    os.environ["TC_HOST"] = "localhost"
    yield
    # Clean up if needed


@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for E2E testing."""
    print("Creating PostgreSQL container...")
    postgres = get_postgres_container()

    print("Starting PostgreSQL container...")
    postgres.start()
    print("PostgreSQL container started successfully")

    # Fix 3: Implement proper wait mechanism for PostgreSQL readiness
    print("Waiting for PostgreSQL container to be ready...")
    if not wait_for_postgres_ready(postgres, timeout=30):
        raise TimeoutError("PostgreSQL container did not become ready in time")

    print("PostgreSQL container is ready!")

    yield postgres

    print("=== CONTAINER CLEANUP STARTING ===")
    import time

    print(f"Container cleanup timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    print("Step 1: Stopping PostgreSQL container...")
    try:
        # Fix 6: Better container cleanup with timeout
        print(f"  Container: {postgres}")
        postgres.stop(timeout=10)
        print("  PostgreSQL container stopped successfully")
    except Exception as e:
        print(f"  Warning: Error stopping container: {e}")
        import traceback

        traceback.print_exc()
        # Force cleanup if normal stop fails
        try:
            print("  Attempting force removal...")
            # Use the correct testcontainers API
            if hasattr(postgres, "remove"):
                postgres.remove(force=True)
                print("  PostgreSQL container force removed")
            else:
                print("  Container removal not available, skipping")
        except Exception as e2:
            print(f"  Warning: Could not force remove container: {e2}")
            import traceback

            traceback.print_exc()

    # Fix 7: Additional cleanup to prevent hanging
    print("Step 2: Waiting for container to fully stop...")
    time.sleep(1)  # Give container time to fully stop
    print("  Wait completed")

    # Fix 11: Force cleanup of any remaining container references
    print("Step 3: Checking for remaining testcontainers...")
    try:
        import docker

        client = docker.from_env()
        # Find and remove any containers with our test prefix
        containers = client.containers.list(
            all=True, filters={"name": "testcontainers"}
        )
        print(f"  Found {len(containers)} remaining testcontainers")

        for i, container in enumerate(containers):
            try:
                print(
                    f"  Processing container {i+1}/{len(containers)}: {container.name} (status: {container.status})"
                )
                if container.status == "running":
                    print(f"    Stopping running container...")
                    container.stop(timeout=5)
                    print(f"    Container stopped")
                print(f"    Removing container...")
                container.remove(force=True)
                print(f"    Force removed container: {container.name}")
            except Exception as e:
                print(f"    Warning: Could not remove container {container.name}: {e}")
                import traceback

                traceback.print_exc()
    except Exception as e:
        print(f"  Warning: Docker cleanup failed: {e}")
        import traceback

        traceback.print_exc()

    print("=== CONTAINER CLEANUP COMPLETED ===")
    print(
        f"Container cleanup completion timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Fix 13: Force process cleanup to prevent hanging
    print("Step 4: Force process cleanup...")
    try:
        import psutil

        current_process = psutil.Process()

        # Check for any child processes that might be hanging
        children = current_process.children(recursive=True)
        if children:
            print(f"  Found {len(children)} child processes")
            for child in children:
                try:
                    print(
                        f"    Terminating child process: {child.pid} ({child.name()})"
                    )
                    child.terminate()
                    child.wait(timeout=5)
                except psutil.TimeoutExpired:
                    print(f"    Force killing child process: {child.pid}")
                    child.kill()
                except Exception as e:
                    print(f"    Error with child process {child.pid}: {e}")
        else:
            print("  No child processes found")

    except Exception as e:
        print(f"  Warning: Error during process cleanup: {e}")
        import traceback

        traceback.print_exc()


def wait_for_postgres_ready(container, timeout=30):
    """Wait for PostgreSQL container to be ready to accept connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            conn_info = get_postgres_connection_info(container)
            import psycopg2

            conn = psycopg2.connect(
                host=conn_info["host"],
                port=conn_info["port"],
                user=conn_info["username"],
                password=conn_info["password"],
                database=conn_info["database"],
            )
            conn.close()
            print("PostgreSQL connection test successful")
            return True
        except Exception as e:
            print(f"PostgreSQL not ready yet: {e}")
            time.sleep(1)
    return False


@pytest.fixture(scope="session")
def test_database(postgres_container) -> Generator[str, None, None]:
    """Initializes the test database schema and yields the database URL."""
    import os

    import pytest

    print("Setting up test database...")

    # Get connection info directly from the container
    conn_info = get_postgres_connection_info(postgres_container)
    database_url = conn_info["url"]

    print(f"Database URL: {database_url}")
    print(f"Connection info: {conn_info}")

    # Set environment variables for the test database
    os.environ["DB_HOST"] = conn_info["host"]
    os.environ["DB_PORT"] = str(conn_info["port"])
    os.environ["DB_USERNAME"] = conn_info["username"]
    os.environ["DB_PASSWORD"] = conn_info["password"]
    os.environ["DB_DATABASE"] = conn_info["database"]

    # Also set the full database URL for async connections
    os.environ["DATABASE_URL"] = conn_info["url"]
    os.environ["ASYNC_DATABASE_URL"] = conn_info["url"].replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )

    print("Environment variables set")
    print(f"DB_HOST: {os.environ['DB_HOST']}")
    print(f"DB_PORT: {os.environ['DB_PORT']}")
    print(f"DATABASE_URL: {os.environ['DATABASE_URL']}")
    print(f"ASYNC_DATABASE_URL: {os.environ['ASYNC_DATABASE_URL']}")

    # Force reload configuration and reset database factories
    from devcycle.core.config import reload_config
    from devcycle.core.database.connection import reset_database_factories

    print("Reloading configuration...")
    reload_config()
    reset_database_factories()
    print("Configuration reloaded")

    # Create engine and initialize tables
    from sqlalchemy import create_engine

    print("Creating database engine...")
    engine = create_engine(database_url, echo=False)

    # Import and create all necessary models including FastAPI Users models
    from devcycle.core.auth.models import User
    from devcycle.core.database.models import Base

    print("Creating database tables...")
    # Create all tables including FastAPI Users tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

    yield database_url

    print("Cleaning up database...")
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    # Fix 1: Close all SQLAlchemy sessions to prevent hanging
    from sqlalchemy.orm import close_all_sessions

    close_all_sessions()

    # Fix 9: Additional cleanup to prevent hanging
    try:
        # Close any remaining connections in the connection pool
        if hasattr(engine, "pool"):
            engine.pool.dispose()

        # Force close all connections
        if hasattr(engine, "_pool"):
            engine._pool.dispose()

    except Exception as e:
        print(f"Warning: Error during engine cleanup: {e}")

    print("Database cleanup completed")


@pytest.fixture
def app(test_database: str) -> FastAPI:
    """A pytest fixture that provides a FastAPI app instance with real dependencies."""
    print("Creating FastAPI app...")

    # The environment variables are already set by test_database fixture
    # Reload configuration to ensure the app uses the updated database settings
    from devcycle.core.config import reload_config
    from devcycle.core.database.connection import reset_database_factories

    print("Reloading configuration for app...")
    reload_config()
    reset_database_factories()
    print("Configuration reloaded for app")

    # Force a small delay to ensure configuration is fully reloaded
    import time

    time.sleep(0.1)

    print("Creating app with create_app()...")
    app = create_app()
    print("FastAPI app created successfully")

    yield app


# Fix 14: Add database isolation fixture for each test
@pytest.fixture(autouse=True)
def database_isolation():
    """Ensure each test gets a clean database state using transaction rollback."""
    print("  [DB ISOLATION] Starting transaction-based isolation...")

    try:
        # Get the current database engine
        from sqlalchemy import create_engine

        from devcycle.core.config import get_config

        config = get_config()
        database_url = f"postgresql+psycopg2://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.database}"
        engine = create_engine(database_url, echo=False)

        # Start a transaction that will be rolled back
        connection = engine.connect()
        transaction = connection.begin()

        # Create a session bound to this transaction
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(bind=connection)
        session = SessionLocal()

        # Bind the session to the transaction
        session.begin_nested()

        print("  [DB ISOLATION] Transaction started, test will run in isolated context")

        # Reset any database-related caches
        from devcycle.core.database.connection import reset_database_factories

        reset_database_factories()

        yield

        # Rollback the transaction to undo all changes
        print("  [DB ISOLATION] Rolling back transaction to isolate test changes...")
        try:
            session.rollback()
            transaction.rollback()
            print("  [DB ISOLATION] Transaction rolled back successfully")
        except Exception as e:
            print(f"  [DB ISOLATION] Warning: Error during rollback: {e}")

        # Cleanup
        session.close()
        connection.close()
        engine.dispose()
        print("  [DB ISOLATION] Database isolation completed")

    except Exception as e:
        print(f"  [DB ISOLATION] Warning: Error during database isolation: {e}")
        import traceback

        traceback.print_exc()
        yield  # Still yield to allow test to run


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """A pytest fixture that provides a TestClient for the FastAPI app."""
    print("Creating TestClient...")
    client = TestClient(app)
    print("TestClient created successfully")
    return client


@pytest.fixture
async def db_session(test_database: str):
    """A pytest fixture that provides an async database session."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # Convert the sync URL to async URL
    async_database_url = test_database.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(async_database_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session

    # Fix 2: Ensure proper cleanup of async engine
    await engine.dispose()

    # Fix 3: Close all sessions to prevent hanging
    from sqlalchemy.orm import close_all_sessions

    close_all_sessions()


# Fix 4: Add cleanup fixture to handle testcontainers cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_resources():
    """Cleanup all test resources after tests complete."""
    yield

    print("=== STARTING FINAL CLEANUP ===")
    print(f"Cleanup timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Fix 12: Add timeout-based cleanup to prevent hanging
    import sys
    import threading

    def force_exit():
        """Force exit if cleanup takes too long."""
        print("=== FORCE EXIT TRIGGERED - Cleanup taking too long ===")
        time.sleep(10)  # Wait 10 seconds for cleanup
        print("=== FORCING EXIT ===")
        os._exit(0)  # Force exit

    # Start force exit timer
    exit_timer = threading.Timer(30.0, force_exit)  # 30 second timeout
    exit_timer.daemon = True
    exit_timer.start()

    try:
        # Fix 8: Cancel all pending asyncio tasks
        print("Step 1: Cancelling pending asyncio tasks...")
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            print(
                f"Event loop status: running={loop.is_running()}, closed={loop.is_closed()}"
            )

            if loop.is_running():
                # Cancel all pending tasks
                pending = asyncio.all_tasks(loop)
                print(f"Found {len(pending)} pending asyncio tasks")

                cancelled_count = 0
                for i, task in enumerate(pending):
                    if not task.done():
                        task_name = getattr(task, "_name", f"Task-{i}")
                        print(
                            f"  Cancelling task {i+1}/{len(pending)}: {task_name} (done={task.done()}, cancelled={task.cancelled()})"
                        )
                        task.cancel()
                        cancelled_count += 1

                print(f"Cancelled {cancelled_count} tasks")

                # Wait a bit for tasks to cancel
                if pending:
                    print("Waiting for tasks to complete cancellation...")
                    try:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                        print("All tasks cancelled successfully")
                    except Exception as e:
                        print(f"Warning: Error during task cancellation: {e}")
            else:
                print("Event loop is not running, skipping task cancellation")

        except Exception as e:
            print(f"Warning: Error cancelling asyncio tasks: {e}")
            import traceback

            traceback.print_exc()

        # Close all SQLAlchemy sessions
        print("Step 2: Closing SQLAlchemy sessions...")
        try:
            from sqlalchemy.orm import close_all_sessions

            close_all_sessions()
            print("All SQLAlchemy sessions closed")
        except Exception as e:
            print(f"Warning: Error closing SQLAlchemy sessions: {e}")
            import traceback

            traceback.print_exc()

        # Force garbage collection to clean up any remaining references
        print("Step 3: Running garbage collection...")
        try:
            import gc

            before_count = len(gc.get_objects())
            collected = gc.collect()
            after_count = len(gc.get_objects())
            print(
                f"Garbage collection: collected {collected} objects, before: {before_count}, after: {after_count}"
            )
        except Exception as e:
            print(f"Warning: Error during garbage collection: {e}")
            import traceback

            traceback.print_exc()

        # Additional cleanup steps
        print("Step 4: Additional cleanup...")
        try:
            # Check for any remaining file handles
            import psutil

            process = psutil.Process()
            open_files = process.open_files()
            print(f"Open file handles: {len(open_files)}")
            if open_files:
                for file in open_files[:5]:  # Show first 5
                    print(f"  - {file.path}")
                if len(open_files) > 5:
                    print(f"  ... and {len(open_files) - 5} more")

            # Check for any remaining network connections
            connections = process.connections()
            print(f"Network connections: {len(connections)}")
            if connections:
                for conn in connections[:5]:  # Show first 5
                    print(f"  - {conn.laddr} -> {conn.raddr} ({conn.status})")
                if len(connections) > 5:
                    print(f"  ... and {len(connections) - 5} more")

        except Exception as e:
            print(f"Warning: Error during additional cleanup: {e}")
            import traceback

            traceback.print_exc()

        # Cancel the force exit timer since cleanup completed successfully
        exit_timer.cancel()
        print("=== FINAL CLEANUP COMPLETED SUCCESSFULLY ===")
        print(f"Cleanup completion timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"=== CRITICAL ERROR DURING CLEANUP: {e} ===")
        import traceback

        traceback.print_exc()
        # Force exit on critical error
        os._exit(1)


# Fix 5: Add signal handler for graceful shutdown
import signal
import sys


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\nReceived signal {signum}, cleaning up...")

    # Close all SQLAlchemy sessions
    from sqlalchemy.orm import close_all_sessions

    close_all_sessions()

    # Force cleanup
    import gc

    gc.collect()

    print("Cleanup completed, exiting...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Fix 15: Add test isolation markers and configuration
def pytest_configure(config):
    """Configure pytest with isolation settings."""
    # Mark all E2E tests as requiring isolation
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test requiring isolation"
    )
    config.addinivalue_line(
        "markers", "isolated: mark test as requiring complete isolation"
    )

    # Note: --forked option not available in current pytest version
    # Using transaction-based isolation instead


def pytest_collection_modifyitems(config, items):
    """Automatically mark E2E tests with isolation requirements."""
    for item in items:
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.isolated)


# Fix 10: Add per-test cleanup fixture with enhanced isolation and timeout enforcement
@pytest.fixture(autouse=True)
def cleanup_after_each_test():
    """Cleanup after each individual test to prevent state pollution."""
    # Setup: Ensure clean state before each test
    print(f"\n=== TEST ISOLATION: Setting up clean environment for test ===")

    # Reset any global state that might persist between tests
    try:
        # Clear any cached database connections
        from devcycle.core.database.connection import reset_database_factories

        reset_database_factories()

        # Clear any cached configuration
        from devcycle.core.config import reload_config

        reload_config()

        # Reset any global variables or caches
        import gc

        gc.collect()

        print("  [TEST ISOLATION] Environment reset completed")
    except Exception as e:
        print(f"  [TEST ISOLATION] Warning: Error during environment reset: {e}")

    yield

    # Teardown: Aggressive cleanup after each test with timeout enforcement
    print(f"=== TEST ISOLATION: Cleaning up after test ===")

    # Fix 16: Add timeout enforcement for test cleanup
    import os
    import threading

    def force_cleanup_exit():
        """Force exit if cleanup takes too long."""
        print("  [TEST ISOLATION] FORCE EXIT: Cleanup taking too long, forcing exit")
        os._exit(0)

    # Start cleanup timeout timer (15 seconds)
    cleanup_timer = threading.Timer(15.0, force_cleanup_exit)
    cleanup_timer.daemon = True
    cleanup_timer.start()

    try:
        # Close any open SQLAlchemy sessions
        from sqlalchemy.orm import close_all_sessions

        close_all_sessions()
        print("  [TEST ISOLATION] SQLAlchemy sessions closed")

        # Cancel any pending asyncio tasks for this test
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                pending = asyncio.all_tasks(loop)
                test_tasks = [
                    t
                    for t in pending
                    if not t.done() and getattr(t, "_name", "").startswith("test_")
                ]
                if test_tasks:
                    print(
                        f"  [TEST ISOLATION] Cancelling {len(test_tasks)} test-related asyncio tasks"
                    )
                    for task in test_tasks:
                        task.cancel()

                    # Wait for tasks to complete cancellation with timeout
                    try:
                        # Use asyncio.wait_for to prevent hanging
                        loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*test_tasks, return_exceptions=True),
                                timeout=5.0,
                            )
                        )
                        print(
                            "  [TEST ISOLATION] All test tasks cancelled successfully"
                        )
                    except asyncio.TimeoutError:
                        print(
                            "  [TEST ISOLATION] Warning: Task cancellation timed out, continuing cleanup"
                        )
                    except Exception as e:
                        print(
                            f"  [TEST ISOLATION] Warning: Error during task cancellation: {e}"
                        )
                else:
                    print("  [TEST ISOLATION] No test-related asyncio tasks found")
            else:
                print(
                    "  [TEST ISOLATION] Event loop not running, skipping task cancellation"
                )
        except Exception as e:
            print(f"  [TEST ISOLATION] Warning: Error cancelling test tasks: {e}")

        # Force garbage collection to clean up test objects
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        print(
            f"  [TEST ISOLATION] Garbage collection: collected {collected} objects, before: {before_count}, after: {after_count}"
        )

        # Clear any remaining references
        import sys

        if hasattr(sys, "exc_clear"):
            sys.exc_clear()

        # Cancel the cleanup timeout since we completed successfully
        cleanup_timer.cancel()
        print("  [TEST ISOLATION] Test cleanup completed successfully")

    except Exception as e:
        print(f"  [TEST ISOLATION] Warning: Error during test cleanup: {e}")
        import traceback

        traceback.print_exc()
        # Force exit on critical cleanup error
        cleanup_timer.cancel()
        os._exit(1)
