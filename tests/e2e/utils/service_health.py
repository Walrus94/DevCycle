"""
Service health checking utilities for E2E tests.
"""

import asyncio
import logging
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.e2e.config import TEST_CONFIG

logger = logging.getLogger(__name__)


class ServiceHealthChecker:
    """Comprehensive service health checking for E2E tests."""

    def __init__(self, config=None) -> None:
        self.config = config or TEST_CONFIG
        self.health_status: Dict[str, bool] = {}

    async def check_database_health(self) -> bool:
        """Check database connectivity and basic operations."""
        try:
            engine = create_async_engine(
                self.config.database_url,
                echo=False,
                pool_size=self.config.database_pool_size,
                max_overflow=self.config.database_max_overflow,
            )
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            await engine.dispose()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def check_api_health(self) -> bool:
        """Check API endpoint availability."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{self.config.api_host}:{self.config.api_port}/health",
                    timeout=10,
                )
                return bool(response.status_code == 200)
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False

    async def wait_for_services(self, timeout: int = 60) -> bool:
        """Wait for all services to be healthy."""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            db_healthy = await self.check_database_health()
            api_healthy = await self.check_api_health()

            if all([db_healthy, api_healthy]):
                logger.info("All services are healthy")
                return True

            logger.info(
                f"Waiting for services to be healthy... "
                f"DB: {db_healthy}, API: {api_healthy}"
            )
            await asyncio.sleep(5)

        logger.error(f"Services failed to become healthy within {timeout}s timeout")
        return False

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of all service health statuses."""
        return {
            "database": self.health_status.get("database", False),
            "api": self.health_status.get("api", False),
            "overall": bool(all(self.health_status.values()))
            if self.health_status
            else False,
        }


async def wait_for_services_ready(timeout: int = 60) -> bool:
    """Convenience function to wait for services to be ready."""
    checker = ServiceHealthChecker()
    return await checker.wait_for_services(timeout)
