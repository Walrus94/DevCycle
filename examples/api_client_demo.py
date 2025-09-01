#!/usr/bin/env python3
"""
DevCycle API Client Demo

This script demonstrates how to interact with the DevCycle API using
the standardized REST endpoints and authentication.
"""

import asyncio
import json
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
            True if authentication successful
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
        return response.json()  # type: ignore  # type: ignore

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health status."""
        response = await self.client.get(f"{self.api_base}/health/detailed")
        return response.json()  # type: ignore

    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information."""
        response = await self.client.get(
            f"{self.api_base}/auth/me", headers=self._get_headers()
        )
        return response.json()  # type: ignore

    async def list_agents(self, limit: int = 10) -> Dict[str, Any]:
        """List agents with optional filtering."""
        response = await self.client.get(
            f"{self.api_base}/agents",
            params={"limit": limit},
            headers=self._get_headers(),
        )
        return response.json()  # type: ignore

    async def register_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent."""
        response = await self.client.post(
            f"{self.api_base}/agents", json=agent_data, headers=self._get_headers()
        )
        return response.json()  # type: ignore

    async def send_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to an agent."""
        response = await self.client.post(
            f"{self.api_base}/messages/send",
            json=message_data,
            headers=self._get_headers(),
        )
        return response.json()  # type: ignore

    async def get_message_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get message history."""
        response = await self.client.get(
            f"{self.api_base}/messages/history",
            params={"limit": limit},
            headers=self._get_headers(),
        )
        return response.json()  # type: ignore


async def demo_api_client() -> None:
    """Demonstrate API client usage."""
    # Setup logging for the demo
    setup_example_logging()
    logger = get_example_logger(__name__)

    logger.demo_start("DevCycle API Client Demo")

    # Initialize client
    client = DevCycleAPIClient()

    try:
        # Step 1: Check API health (no auth required)
        print("\n📊 Step 1: Health Check")
        print("-" * 40)

        health = await client.get_health()
        print(f"API Status: {health.get('status', 'unknown')}")
        print(f"Service: {health.get('service', 'unknown')}")
        print(f"Version: {health.get('version', 'unknown')}")

        # Step 2: Detailed health check
        print("\n📊 Step 2: Detailed Health Check")
        print("-" * 40)

        detailed_health = await client.get_detailed_health()
        print(f"Overall Status: {detailed_health.get('status', 'unknown')}")

        components = detailed_health.get("components", {})
        print("Component Status:")
        for component, status in components.items():
            print(f"  - {component}: {status}")

        metrics = detailed_health.get("metrics", {})
        if metrics:
            print("Metrics:")
            for metric, value in metrics.items():
                print(f"  - {metric}: {value}")

        # Step 3: Authentication (optional - for protected endpoints)
        print("\n🔐 Step 3: Authentication")
        print("-" * 40)

        # Note: In a real scenario, you'd have valid credentials
        # For demo purposes, we'll show the structure
        print("Authentication would be done with:")
        print("  email: user@example.com")
        print("  password: your_password")

        # Uncomment to test with real credentials:
        # auth_success = await client.login("user@example.com", "password")
        # if auth_success:
        #     user_info = await client.get_current_user()
        #     print(f"Current user: {user_info.get('email', 'unknown')}")

        # Step 4: Demonstrate agent operations (would require auth)
        print("\n🤖 Step 4: Agent Operations (Demo Structure)")
        print("-" * 40)

        # Example agent registration data
        agent_data = {
            "name": "demo_business_analyst",
            "type": "business_analyst",
            "description": "Demo business analyst agent",
            "version": "1.0.0",
            "capabilities": ["analyze_requirements", "generate_documentation"],
            "configuration": {"max_concurrent_tasks": 3, "timeout_seconds": 300},
        }

        print("Agent Registration Data:")
        print(json.dumps(agent_data, indent=2))

        # Step 5: Demonstrate message operations (would require auth)
        print("\n💬 Step 5: Message Operations (Demo Structure)")
        print("-" * 40)

        # Example message data
        message_data = {
            "agent_id": "demo_business_analyst",
            "action": "analyze_business_requirement",
            "data": {
                "requirement": "Implement user authentication system",
                "priority": "high",
                "context": "E-commerce platform",
            },
            "priority": "normal",
            "ttl": 3600,
            "metadata": {"source": "api_demo", "user_id": "demo_user"},
        }

        print("Message Data:")
        print(json.dumps(message_data, indent=2))

        # Step 6: API Version Information
        print("\n📋 Step 6: API Version Information")
        print("-" * 40)

        try:
            version_response = await client.client.get(f"{client.base_url}/api/version")
            if version_response.status_code == 200:
                version_info = version_response.json()
                print("API Version Info:")
                print(json.dumps(version_info, indent=2))
            else:
                print(f"Version endpoint not available: {version_response.status_code}")
        except Exception as e:
            print(f"Version endpoint error: {e}")

        print("\n✅ API Client Demo completed successfully!")
        print("\nThis demonstrates:")
        print("- Health check endpoints (public)")
        print("- Authentication flow structure")
        print("- Agent management operations")
        print("- Message handling operations")
        print("- API versioning information")
        print("\nTo use with real authentication:")
        print("1. Create a user account through the API")
        print("2. Use valid credentials in the login() method")
        print("3. All protected endpoints will work with the token")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await client.close()


async def demo_error_handling() -> None:
    """Demonstrate error handling patterns."""
    print("\n🚨 Error Handling Demo")
    print("=" * 50)

    client = DevCycleAPIClient()

    try:
        # Test 404 error
        print("\n📝 Test 1: 404 Error")
        print("-" * 30)

        try:
            response = await client.client.get(f"{client.api_base}/agents/nonexistent")
            print(f"Status: {response.status_code}")
            if response.status_code == 404:
                error_data = response.json()
                print(f"Error: {error_data.get('detail', 'Not found')}")
        except Exception as e:
            print(f"Error: {e}")

        # Test authentication error
        print("\n📝 Test 2: Authentication Error")
        print("-" * 30)

        try:
            response = await client.client.get(
                f"{client.api_base}/agents",
                headers={"Authorization": "Bearer invalid_token"},
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 401:
                error_data = response.json()
                print(f"Error: {error_data.get('detail', 'Unauthorized')}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n✅ Error handling demo completed!")

    finally:
        await client.close()


if __name__ == "__main__":
    # Run the main demo
    asyncio.run(demo_api_client())

    # Run error handling demo
    asyncio.run(demo_error_handling())
