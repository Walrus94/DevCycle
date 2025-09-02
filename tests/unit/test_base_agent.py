"""
Tests for the BaseAgent class and related components.

This module tests the base agent interface implementation including:
- Agent lifecycle management
- State management
- Error handling
- Extensibility patterns
- Configuration loading
"""

# mypy: disable-error-code=no-untyped-def

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from devcycle.agents.base import AgentFactory, AgentResult, AgentStatus, BaseAgent


class MockAgent(BaseAgent):
    """Concrete test agent implementation for testing BaseAgent."""

    async def process(self, input_data, **kwargs):
        """Test implementation of abstract process method."""
        await asyncio.sleep(0.01)  # Simulate some work
        return AgentResult(
            success=True, data=f"Processed: {input_data}", metadata={"processed": True}
        )

    def validate_input(self, input_data):
        """Test implementation of abstract validate_input method."""
        return input_data is not None and isinstance(input_data, str)


class MockAgentWithError(BaseAgent):
    """Test agent that raises errors for testing error handling."""

    async def process(self, input_data, **kwargs):
        """Raise an error for testing purposes."""
        raise ValueError("Test error for error handling")

    def validate_input(self, input_data):
        """Return True to test process error handling."""
        return True


class MockAgentWithValidationError(BaseAgent):
    """Test agent that fails validation."""

    async def process(self, input_data, **kwargs):
        """Return result that should never be reached due to validation failure."""
        return AgentResult(success=True, data="Should not reach here")

    def validate_input(self, input_data):
        """Fail validation for testing purposes."""
        return False


@pytest.fixture
def test_agent():
    """Create a test agent instance."""
    return MockAgent("test_agent")


@pytest.fixture
def error_agent():
    """Create an agent that raises errors."""
    return MockAgentWithError("error_agent")


@pytest.fixture
def validation_error_agent():
    """Create an agent that fails validation."""
    return MockAgentWithValidationError("validation_error_agent")


@pytest.mark.unit
class TestAgentStatus:
    """Test AgentStatus enum."""

    @pytest.mark.unit
    def test_agent_status_values(self):
        """Test that all expected status values exist."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"


@pytest.mark.unit
class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_agent_result_creation(self):
        """Test creating AgentResult instances."""
        result = AgentResult(success=True, data="test data")
        assert result.success is True
        assert result.data == "test data"
        assert result.error is None
        assert result.execution_time == 0.0
        assert result.timestamp > 0

    def test_agent_result_to_dict(self):
        """Test converting AgentResult to dictionary."""
        result = AgentResult(
            success=False,
            error="test error",
            metadata={"key": "value"},
            execution_time=1.5,
        )
        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "test error"
        assert result_dict["metadata"] == {"key": "value"}
        assert result_dict["execution_time"] == 1.5
        assert "timestamp" in result_dict


@pytest.mark.unit
class TestBaseAgent:
    """Test BaseAgent abstract class implementation."""

    def test_agent_initialization(self, test_agent):
        """Test agent initialization."""
        assert test_agent.name == "test_agent"
        assert test_agent.status == AgentStatus.IDLE
        assert test_agent.config == {}
        assert len(test_agent.execution_history) == 0
        assert test_agent.current_task is None
        assert test_agent.logger is not None

    def test_agent_config_loading(self):
        """Test agent configuration loading."""
        with patch("devcycle.agents.base.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.get_agent_config.return_value = {"timeout": 30}
            mock_get_config.return_value = mock_config

            agent = MockAgent("config_test", {"custom": "value"})
            assert agent.config["timeout"] == 30
            assert agent.config["custom"] == "value"

    def test_agent_validation(self, test_agent):
        """Test input validation."""
        assert test_agent.validate_input("valid input") is True
        assert test_agent.validate_input(None) is False
        assert test_agent.validate_input(123) is False

    @pytest.mark.asyncio
    async def test_agent_process_abstract_method(self):
        """Test that abstract methods are properly defined."""
        # This should work without raising NotImplementedError
        agent = MockAgent("abstract_test")
        result = await agent.process("test input")
        assert isinstance(result, AgentResult)
        assert result.success is True

    def test_agent_string_representations(self, test_agent):
        """Test string representation methods."""
        str_repr = str(test_agent)
        repr_repr = repr(test_agent)

        assert "MockAgent" in str_repr
        assert "test_agent" in str_repr
        assert "idle" in str_repr

        assert "MockAgent" in repr_repr
        assert "test_agent" in repr_repr
        assert "idle" in repr_repr


@pytest.mark.unit
class TestAgentExecution:
    """Test agent execution functionality."""

    @pytest.mark.asyncio
    async def test_successful_execution(self, test_agent):
        """Test successful agent execution."""
        result = await test_agent.execute("test input")

        assert result.success is True
        assert "Processed: test input" in result.data
        assert result.error is None
        assert result.execution_time > 0
        assert test_agent.status == AgentStatus.COMPLETED
        assert len(test_agent.execution_history) == 1

    @pytest.mark.asyncio
    async def test_execution_with_validation_failure(self, validation_error_agent):
        """Test execution when validation fails."""
        result = await validation_error_agent.execute("test input")

        assert result.success is False
        assert "Invalid input data" in result.error
        assert validation_error_agent.status == AgentStatus.FAILED
        assert len(validation_error_agent.execution_history) == 1

    @pytest.mark.asyncio
    async def test_execution_with_processing_error(self, error_agent):
        """Test execution when processing raises an error."""
        result = await error_agent.execute("test input")

        assert result.success is False
        assert "Test error for error handling" in result.error
        assert error_agent.status == AgentStatus.FAILED
        assert len(error_agent.execution_history) == 1

    @pytest.mark.asyncio
    async def test_execution_history_tracking(self, test_agent):
        """Test that execution history is properly tracked."""
        # Execute multiple times
        await test_agent.execute("input 1")
        await test_agent.execute("input 2")
        await test_agent.execute("input 3")

        assert len(test_agent.execution_history) == 3
        assert all(result.success for result in test_agent.execution_history)

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, test_agent):
        """Test that execution time is properly tracked."""
        start_time = time.time()
        result = await test_agent.execute("test input")
        end_time = time.time()

        assert result.execution_time > 0
        assert (
            result.execution_time <= (end_time - start_time) + 0.1
        )  # Allow small overhead


@pytest.mark.unit
class TestAgentAsyncExecution:
    """Test asynchronous execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_async(self, test_agent):
        """Test asynchronous execution."""
        task = test_agent.execute_async("async input")

        assert isinstance(task, asyncio.Task)
        assert test_agent.current_task == task

        # Wait for completion
        result = await task

        assert result.success is True
        assert test_agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_async_already_running(self, test_agent):
        """Test that execute_async fails when already running."""
        # Start first execution
        task1 = test_agent.execute_async("first input")

        # Try to start second execution
        with pytest.raises(RuntimeError, match="already running"):
            test_agent.execute_async("second input")

        # Wait for first to complete
        await task1

    @pytest.mark.asyncio
    async def test_cancel_execution(self, test_agent):
        """Test execution cancellation."""
        # Start execution
        task = test_agent.execute_async("cancel input")

        # Cancel immediately
        cancelled = test_agent.cancel()
        assert cancelled is True
        assert test_agent.status == AgentStatus.CANCELLED

        # Wait for task to be cancelled
        with pytest.raises(asyncio.CancelledError):
            await task

    def test_cancel_no_execution(self, test_agent):
        """Test cancellation when no execution is running."""
        cancelled = test_agent.cancel()
        assert cancelled is False


@pytest.mark.unit
class TestAgentStateManagement:
    """Test agent state management functionality."""

    def test_get_status(self, test_agent):
        """Test getting agent status."""
        status = test_agent.get_status()

        assert status["name"] == "test_agent"
        assert status["status"] == "idle"
        assert status["execution_history_count"] == 0
        assert status["last_execution"] is None
        assert status["config"] == {}

    def test_get_status_with_history(self, test_agent):
        """Test getting status with execution history."""
        # Execute once to create history
        asyncio.run(test_agent.execute("test input"))

        status = test_agent.get_status()
        assert status["execution_history_count"] == 1
        assert status["last_execution"] is not None

    def test_get_execution_history(self, test_agent):
        """Test getting execution history."""
        # Execute multiple times
        asyncio.run(test_agent.execute("input 1"))
        asyncio.run(test_agent.execute("input 2"))
        asyncio.run(test_agent.execute("input 3"))

        # Get all history
        all_history = test_agent.get_execution_history()
        assert len(all_history) == 3

        # Get limited history
        limited_history = test_agent.get_execution_history(limit=2)
        assert len(limited_history) == 2
        assert limited_history[-1].data == "Processed: input 3"

    def test_reset_agent(self, test_agent):
        """Test resetting agent to initial state."""
        # Execute once to change state
        asyncio.run(test_agent.execute("test input"))

        # Reset
        test_agent.reset()

        assert test_agent.status == AgentStatus.IDLE
        assert len(test_agent.execution_history) == 0
        assert test_agent.current_task is None


@pytest.mark.unit
class TestAgentFactory:
    """Test AgentFactory functionality."""

    def test_agent_registration(self):
        """Test registering agent classes."""
        # Register test agent
        AgentFactory.register("test", MockAgent)

        # Verify registration
        assert "test" in AgentFactory.list_agents()
        assert AgentFactory._agents["test"] == MockAgent

    def test_agent_creation(self):
        """Test creating agent instances."""
        # Register first
        AgentFactory.register("test", MockAgent)

        # Create instance
        agent = AgentFactory.create("test_instance", "test")

        assert isinstance(agent, MockAgent)
        assert agent.name == "test_instance"

    def test_agent_creation_unknown_type(self):
        """Test creating agent with unknown type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            AgentFactory.create("test", "unknown_type")

    def test_agent_registration_invalid_class(self):
        """Test registering invalid agent class."""

        class InvalidAgent:
            pass

        with pytest.raises(ValueError, match="must inherit from BaseAgent"):
            AgentFactory.register("invalid", InvalidAgent)  # type: ignore[arg-type]

    def test_list_agents(self):
        """Test listing registered agents."""
        # Clear existing registrations
        AgentFactory._agents.clear()

        # Register some agents
        AgentFactory.register("test1", MockAgent)
        AgentFactory.register("test2", MockAgent)

        agents = AgentFactory.list_agents()
        assert "test1" in agents
        assert "test2" in agents
        assert len(agents) == 2


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for agent functionality."""

    @pytest.mark.asyncio
    async def test_agent_execution_lifecycle(self):
        """Test agent execution lifecycle."""
        agent = MockAgent("lifecycle_test")

        # Initial state
        assert agent.status == AgentStatus.IDLE

        # Execute
        result = await agent.execute("lifecycle input")
        assert result.success is True
        # Status should be COMPLETED after successful execution
        assert agent.status == AgentStatus.COMPLETED  # type: ignore[comparison-overlap]

        # Check history
        assert len(agent.execution_history) == 1  # type: ignore[unreachable]

    @pytest.mark.asyncio
    async def test_agent_reset_lifecycle(self):
        """Test agent reset functionality."""
        agent = MockAgent("reset_test")

        # Execute first
        result = await agent.execute("test input")
        assert result.success is True
        assert agent.status == AgentStatus.COMPLETED

        # Reset
        agent.reset()
        # After reset, status should be IDLE again
        assert len(agent.execution_history) == 0
        # Verify status is reset
        assert agent.status.value == "idle"

    @pytest.mark.asyncio
    async def test_multiple_agents(self):
        """Test multiple agents working independently."""
        agent1 = MockAgent("agent1")
        agent2 = MockAgent("agent2")

        # Execute both agents
        result1 = await agent1.execute("input1")
        result2 = await agent2.execute("input2")

        assert result1.success is True
        assert result2.success is True
        assert agent1.status == AgentStatus.COMPLETED
        assert agent2.status == AgentStatus.COMPLETED

        # Each should have independent history
        assert len(agent1.execution_history) == 1
        assert len(agent2.execution_history) == 1
        assert agent1.execution_history[0].data != agent2.execution_history[0].data
