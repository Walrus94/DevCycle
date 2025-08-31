"""
Tests for the BusinessAnalystAgent.

This module tests the basic functionality of the Business Analyst agent.
"""

# mypy: disable-error-code=no-untyped-def

import pytest

from devcycle.agents.business_analyst import BusinessAnalystAgent, Requirement


class TestBusinessAnalystAgent:
    """Test BusinessAnalystAgent functionality."""

    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        agent = BusinessAnalystAgent()
        assert agent.name == "business_analyst"
        assert len(agent.requirements_database) == 0
        assert "feature" in agent.analysis_templates
        assert "bugfix" in agent.analysis_templates

    def test_input_validation(self):
        """Test input validation for different data types."""
        agent = BusinessAnalystAgent()

        # Valid inputs
        assert agent.validate_input("Valid requirement description") is True
        assert (
            agent.validate_input(
                {
                    "title": "Test Requirement",
                    "description": "This is a test requirement",
                }
            )
            is True
        )

        # Invalid inputs
        assert agent.validate_input("") is False
        assert agent.validate_input(None) is False
        assert agent.validate_input({}) is False
        assert agent.validate_input({"title": "Only title"}) is False

    def test_requirement_parsing(self):
        """Test requirement parsing from different input types."""
        agent = BusinessAnalystAgent()

        # String input
        req = agent._parse_requirement("Simple requirement description")
        assert isinstance(req, Requirement)
        assert req.title == "Business Requirement"
        assert req.description == "Simple requirement description"
        assert req.priority == "medium"
        assert req.category == "feature"

        # Dictionary input
        req = agent._parse_requirement(
            {
                "title": "Custom Title",
                "description": "Custom description",
                "priority": "high",
                "category": "bugfix",
            }
        )
        assert req.title == "Custom Title"
        assert req.description == "Custom description"
        assert req.priority == "high"
        assert req.category == "bugfix"

    @pytest.mark.asyncio
    async def test_basic_requirement_processing(self):
        """Test basic requirement processing."""
        agent = BusinessAnalystAgent()

        result = await agent.process("Test business requirement")

        assert result.success is True
        assert "requirement_id" in result.data
        assert result.data["title"] == "Business Requirement"
        assert result.data["description"] == "Test business requirement"
        assert len(agent.requirements_database) == 1

    def test_requirements_summary(self):
        """Test requirements summary generation."""
        agent = BusinessAnalystAgent()

        # Add some test requirements
        agent.requirements_database = [
            Requirement(
                "req_001", "High Priority", "Critical feature", "high", "feature"
            ),
            Requirement(
                "req_002", "Medium Priority", "Regular feature", "medium", "feature"
            ),
            Requirement("req_003", "Bug Fix", "Fix critical bug", "critical", "bugfix"),
        ]

        summary = agent.get_requirements_summary()

        assert summary["total_requirements"] == 3
        assert summary["by_priority"]["high"] == 1
        assert summary["by_priority"]["medium"] == 1
        assert summary["by_priority"]["critical"] == 1
        assert summary["by_category"]["feature"] == 2
        assert summary["by_category"]["bugfix"] == 1
        assert len(summary["recent_requirements"]) == 3


class TestRequirement:
    """Test Requirement dataclass."""

    def test_requirement_creation(self):
        """Test creating Requirement instances."""
        req = Requirement(
            id="test_001",
            title="Test Requirement",
            description="This is a test requirement",
            priority="high",
            category="feature",
        )

        assert req.id == "test_001"
        assert req.title == "Test Requirement"
        assert req.description == "This is a test requirement"
        assert req.priority == "high"
        assert req.category == "feature"
        assert req.acceptance_criteria == []
        assert req.dependencies == []

    def test_requirement_with_optional_fields(self):
        """Test creating Requirement with optional fields."""
        req = Requirement(
            id="test_002",
            title="Test Requirement",
            description="This is a test requirement",
            acceptance_criteria=["User can login", "User can logout"],
            dependencies=["authentication_system"],
        )

        assert req.acceptance_criteria == ["User can login", "User can logout"]
        assert req.dependencies == ["authentication_system"]
