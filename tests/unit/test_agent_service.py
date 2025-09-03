"""
Unit tests for Agent service operations.

Tests the agent service layer with Tortoise ORM.
"""

import pytest
from tortoise import Tortoise

from devcycle.core.database.tortoise_schemas import AgentCreate
from devcycle.core.services.agent_service import AgentService


@pytest.fixture
async def tortoise_db():
    """Create test database."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["devcycle.core.models.tortoise_models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
def agent_service():
    """Create agent service instance."""
    return AgentService()


@pytest.mark.asyncio
async def test_create_agent(tortoise_db, agent_service):
    """Test creating an agent."""
    agent_data = AgentCreate(
        name="test_agent",
        agent_type="test",
        version="1.0.0",
        capabilities='["test"]',
        configuration='{"test": true}',
        metadata_json='{"test": true}',
    )

    agent = await agent_service.create_agent(agent_data)
    assert agent.id is not None
    assert agent.name == "test_agent"
    assert agent.agent_type == "test"


@pytest.mark.asyncio
async def test_get_agent_by_name(tortoise_db, agent_service):
    """Test getting agent by name."""
    # Create agent first
    agent_data = AgentCreate(
        name="test_agent",
        agent_type="test",
        version="1.0.0",
        capabilities='["test"]',
        configuration='{"test": true}',
        metadata_json='{"test": true}',
    )
    created_agent = await agent_service.create_agent(agent_data)

    # Get agent by name
    found_agent = await agent_service.get_agent_by_name("test_agent")
    assert found_agent is not None
    assert found_agent.id == created_agent.id
