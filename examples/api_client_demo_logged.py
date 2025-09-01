#!/usr/bin/env python3
"""
DevCycle API Client Demo with Proper Logging

This script demonstrates how to interact with the DevCycle API using
the standardized REST endpoints and authentication with proper structured logging.
"""

import asyncio
from typing import Any, Dict, Optional

import httpx
from logging_utils import get_example_logger, setup_example_logging


class DevCycleAPIClient:
    """Client for interacting with the DevCycle API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient()
        self.logger = get_example_logger(__name__)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def login(self, email: str, password: str) -> bool:
        """
        Authenticate with the API.

        Args:
            email: User email
            password: User password

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            response = await self.client.post(
                f"{self.api_base}/auth/jwt/login",
                data={"username": email, "password": password},
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.logger.success(f"Authenticated as {email}")
                return True
            else:
                self.logger.error(f"Authentication failed: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_health(self) -> Dict[str, Any]:
        """Get basic health status."""
        response = await self.client.get(f"{self.api_base}/health")
        return response.json()  # type: ignore

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status."""
        response = await self.client.get(f"{self.api_base}/health/detailed")
        return response.json()  # type: ignore

    async def get_agents(self) -> Dict[str, Any]:
        """Get list of agents."""
        response = await self.client.get(
            f"{self.api_base}/agents/", headers=self._get_headers()
        )
        return response.json()  # type: ignore

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get specific agent by ID."""
        response = await self.client.get(
            f"{self.api_base}/agents/{agent_id}", headers=self._get_headers()
        )
        return response.json()  # type: ignore

    async def get_agent_types(self) -> Dict[str, Any]:
        """Get available agent types."""
        response = await self.client.get(f"{self.api_base}/agents/types")
        return response.json()  # type: ignore

    async def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get available agent capabilities."""
        response = await self.client.get(f"{self.api_base}/agents/capabilities")
        return response.json()  # type: ignore

    async def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent statistics overview."""
        response = await self.client.get(f"{self.api_base}/agents/statistics/overview")
        return response.json()  # type: ignore

    async def send_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to an agent."""
        response = await self.client.post(
            f"{self.api_base}/messages/send",
            json=message_data,
            headers=self._get_headers(),
        )
        return response.json()  # type: ignore

    async def get_version_info(self) -> Dict[str, Any]:
        """Get API version information."""
        response = await self.client.get(f"{self.api_base}/version")
        return response.json()  # type: ignore


async def demo_api_client() -> None:
    """Demonstrate API client usage with proper logging."""
    # Setup logging for the demo
    setup_example_logging()
    logger = get_example_logger(__name__)

    logger.demo_start("DevCycle API Client Demo")

    # Initialize client
    client = DevCycleAPIClient()

    try:
        # Step 1: Check API health (no auth required)
        logger.step("Health Check", 1)
        health = await client.get_health()
        logger.info(f"API Status: {health.get('status', 'unknown')}")
        logger.info(f"Service: {health.get('service', 'unknown')}")
        logger.info(f"Version: {health.get('version', 'unknown')}")

        # Step 2: Detailed health check
        logger.step("Detailed Health Check", 2)
        detailed_health = await client.get_detailed_health()
        logger.info(f"Overall Status: {detailed_health.get('status', 'unknown')}")

        components = detailed_health.get("components", {})
        if components:
            logger.info("Component Status:")
            for component, status in components.items():
                logger.info(f"  - {component}: {status}")

        metrics = detailed_health.get("metrics", {})
        if metrics:
            logger.info("Metrics:")
            for metric, value in metrics.items():
                logger.info(f"  - {metric}: {value}")

        # Step 3: Authentication (demo structure)
        logger.step("Authentication", 3)
        # Note: In a real scenario, you would use actual credentials
        # success = await client.login("user@example.com", "password")
        logger.info("Authentication would be done with:")
        logger.info("  email: user@example.com")
        logger.info("  password: your_password")

        # if success:
        #     user_info = await client.get_current_user()
        #     logger.info(f"Current user: {user_info.get('email', 'unknown')}")

        # Step 4: Agent operations (demo structure)
        logger.step("Agent Operations", 4)

        # Demo agent registration data
        agent_data = {
            "name": "demo_agent",
            "agent_type": "business_analyst",
            "version": "1.0.0",
            "capabilities": ["analysis", "reporting"],
            "description": "Demo agent for API testing",
        }

        logger.data(agent_data, "Agent Registration Data")

        # Step 5: Message operations (demo structure)
        logger.step("Message Operations", 5)

        # Demo message data
        message_data = {
            "to_agent": "demo_agent",
            "message_type": "command",
            "action": "analyze_requirement",
            "data": {
                "requirement": "Implement user authentication system",
                "priority": "high",
                "deadline": "2024-01-15",
            },
            "priority": "high",
            "ttl": 3600,
        }

        logger.data(message_data, "Message Data")

        # Step 6: API version information
        logger.step("API Version Information", 6)
        try:
            version_info = await client.get_version_info()
            logger.data(version_info, "API Version Info")
        except Exception as e:
            logger.warning(f"Version endpoint not available: {e}")

        logger.demo_end("DevCycle API Client Demo", success=True)

        logger.info("This demonstrates:")
        logger.info("- Health check endpoints (public)")
        logger.info("- Authentication flow structure")
        logger.info("- Agent management operations")
        logger.info("- Message handling operations")
        logger.info("- API versioning information")
        logger.info("")
        logger.info("To use with real authentication:")
        logger.info("1. Create a user account through the API")
        logger.info("2. Use valid credentials in the login() method")
        logger.info("3. All protected endpoints will work with the token")

    except Exception as e:
        logger.error(f"Demo error: {e}")
        logger.demo_end("DevCycle API Client Demo", success=False)
    finally:
        await client.close()


async def demo_error_handling() -> None:
    """Demonstrate error handling patterns with proper logging."""
    setup_example_logging()
    logger = get_example_logger(__name__)

    logger.demo_start("Error Handling Demo")

    client = DevCycleAPIClient()

    try:
        # Test 1: 404 Error
        logger.step("404 Error Test", 1)
        try:
            response = await client.client.get(f"{client.api_base}/nonexistent")
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 404:
                error_data = response.json()
                logger.info(f"Error: {error_data.get('detail', 'Not found')}")
        except Exception as e:
            logger.error(f"Error: {e}")

        # Test 2: Authentication Error
        logger.step("Authentication Error Test", 2)
        try:
            # Try to access protected endpoint without auth
            response = await client.client.get(
                f"{client.api_base}/agents/",
                headers={"Authorization": "Bearer invalid_token"},
            )
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 401:
                error_data = response.json()
                logger.info(f"Error: {error_data.get('detail', 'Unauthorized')}")
        except Exception as e:
            logger.error(f"Error: {e}")

        logger.demo_end("Error Handling Demo", success=True)

    finally:
        await client.close()


async def main() -> None:
    """Main demo function."""
    setup_example_logging()
    logger = get_example_logger(__name__)

    logger.info("Starting DevCycle API Client Demos")

    # Run main demo
    await demo_api_client()

    # Run error handling demo
    await demo_error_handling()

    logger.info("All demos completed!")


if __name__ == "__main__":
    asyncio.run(main())
