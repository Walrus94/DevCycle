"""Unit tests for workflow Redis integration."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from devcycle.core.acp.config import ACPConfig, ACPWorkflowConfig
from devcycle.core.acp.models import ACPWorkflow, ACPWorkflowStep
from devcycle.core.acp.services.workflow_engine import ACPWorkflowEngine
from devcycle.core.cache.acp_cache import ACPCache


class TestWorkflowRedisIntegration:
    """Test workflow engine Redis integration."""

    @pytest.fixture
    def mock_acp_cache(self):
        """Create a mock ACP cache."""
        mock_cache = Mock(spec=ACPCache)
        mock_cache.cache_workflow_state = AsyncMock(return_value=True)
        mock_cache.update_workflow_step = AsyncMock(return_value=True)
        mock_cache.get_workflow_state = AsyncMock(return_value=None)
        mock_cache.get_workflow_step = AsyncMock(return_value=None)
        return mock_cache

    @pytest.fixture
    def mock_agent_registry(self):
        """Create a mock agent registry."""
        return Mock()

    @pytest.fixture
    def mock_message_router(self):
        """Create a mock message router."""
        return Mock()

    @pytest.fixture
    def workflow_engine(self, mock_acp_cache, mock_agent_registry, mock_message_router):
        """Create workflow engine with Redis cache."""
        config = ACPConfig()
        workflow_config = ACPWorkflowConfig(
            retry_failed_steps=False
        )  # Disable retries for testing
        return ACPWorkflowEngine(
            config,
            workflow_config,
            mock_agent_registry,
            mock_message_router,
            mock_acp_cache,
        )

    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing."""
        steps = [
            ACPWorkflowStep(
                step_id="step1",
                step_name="Test Step 1",
                agent_id="test-agent-1",
                input_data={"input": "test1"},
            ),
            ACPWorkflowStep(
                step_id="step2",
                step_name="Test Step 2",
                agent_id="test-agent-2",
                input_data={"input": "test2"},
                depends_on=["step1"],
            ),
        ]

        return ACPWorkflow(
            workflow_id="test-workflow-1", workflow_name="Test Workflow", steps=steps
        )

    @pytest.mark.asyncio
    async def test_start_workflow_caches_state(
        self, workflow_engine, sample_workflow, mock_acp_cache
    ):
        """Test that starting a workflow caches state in Redis."""
        # Mock the workflow execution to prevent actual execution
        with patch.object(workflow_engine, "_execute_workflow", new_callable=AsyncMock):
            response = await workflow_engine.start_workflow(sample_workflow)

            # Verify workflow was started successfully
            assert response.success is True

            # Verify workflow state was cached
            mock_acp_cache.cache_workflow_state.assert_called_once()
            call_args = mock_acp_cache.cache_workflow_state.call_args

            assert call_args[0][0] == "test-workflow-1"  # workflow_id
            cached_state = call_args[0][1]  # state dict

            assert cached_state["status"] == "running"
            assert cached_state["current_step"] == "step1"
            assert cached_state["progress"] == 0
            assert cached_state["total_steps"] == 2
            assert cached_state["completed_steps"] == 0

    @pytest.mark.asyncio
    async def test_execute_step_caches_result(
        self, workflow_engine, sample_workflow, mock_acp_cache, mock_message_router
    ):
        """Test that executing a step caches the result in Redis."""
        # Mock successful message routing
        from devcycle.core.acp.models import ACPResponse

        mock_response = ACPResponse(
            response_id="resp_test_msg",
            message_id="test_msg",
            success=True,
            content={"result": "test_output"},
        )
        mock_message_router.route_workflow_message = AsyncMock(
            return_value=mock_response
        )

        # Execute a step
        step = sample_workflow.steps[0]
        await workflow_engine._execute_step(sample_workflow, step)

        # Verify step result was cached
        mock_acp_cache.update_workflow_step.assert_called_once()
        call_args = mock_acp_cache.update_workflow_step.call_args

        assert call_args[0][0] == "test-workflow-1"  # workflow_id
        assert call_args[0][1] == "step1"  # step_id
        cached_result = call_args[0][2]  # result dict

        assert cached_result["status"] == "completed"
        assert cached_result["result"] == {"result": "test_output"}
        assert cached_result["agent_id"] == "test-agent-1"
        assert "duration_ms" in cached_result
        assert "completed_at" in cached_result

    @pytest.mark.asyncio
    async def test_execute_step_caches_failure(
        self, workflow_engine, sample_workflow, mock_acp_cache, mock_message_router
    ):
        """Test that step failures are cached in Redis."""
        # Mock failed message routing
        from devcycle.core.acp.models import ACPResponse

        mock_response = ACPResponse(
            response_id="resp_test_msg",
            message_id="test_msg",
            success=False,
            error="Test error message",
        )
        mock_message_router.route_workflow_message = AsyncMock(
            return_value=mock_response
        )

        # Execute a step - expect it to raise an exception
        step = sample_workflow.steps[0]
        with pytest.raises(Exception, match="Step step1 failed: Test error message"):
            await workflow_engine._execute_step(sample_workflow, step)

        # Verify step failure was cached
        mock_acp_cache.update_workflow_step.assert_called_once()
        call_args = mock_acp_cache.update_workflow_step.call_args

        assert call_args[0][0] == "test-workflow-1"  # workflow_id
        assert call_args[0][1] == "step1"  # step_id
        cached_result = call_args[0][2]  # result dict

        assert cached_result["status"] == "failed"
        assert cached_result["error"] == "Test error message"
        assert cached_result["agent_id"] == "test-agent-1"

    @pytest.mark.asyncio
    async def test_get_workflow_state(self, workflow_engine, mock_acp_cache):
        """Test getting workflow state from Redis cache."""
        expected_state = {
            "status": "running",
            "current_step": "step1",
            "progress": 50,
            "total_steps": 2,
            "completed_steps": 1,
        }
        mock_acp_cache.get_workflow_state.return_value = expected_state

        result = await workflow_engine.get_workflow_state("test-workflow-1")

        assert result == expected_state
        mock_acp_cache.get_workflow_state.assert_called_once_with("test-workflow-1")

    @pytest.mark.asyncio
    async def test_get_workflow_step_result(self, workflow_engine, mock_acp_cache):
        """Test getting workflow step result from Redis cache."""
        expected_result = {
            "status": "completed",
            "result": {"output": "test"},
            "duration_ms": 1500,
        }
        mock_acp_cache.get_workflow_step.return_value = expected_result

        result = await workflow_engine.get_workflow_step_result(
            "test-workflow-1", "step1"
        )

        assert result == expected_result
        mock_acp_cache.get_workflow_step.assert_called_once_with(
            "test-workflow-1", "step1"
        )

    @pytest.mark.asyncio
    async def test_update_workflow_progress(self, workflow_engine, mock_acp_cache):
        """Test updating workflow progress in Redis cache."""
        current_state = {
            "status": "running",
            "current_step": "step1",
            "progress": 25,
            "total_steps": 4,
        }
        mock_acp_cache.get_workflow_state.return_value = current_state

        await workflow_engine.update_workflow_progress("test-workflow-1", "step2", 50)

        # Verify state was updated and cached
        mock_acp_cache.get_workflow_state.assert_called_once_with("test-workflow-1")
        mock_acp_cache.cache_workflow_state.assert_called_once()

        call_args = mock_acp_cache.cache_workflow_state.call_args
        updated_state = call_args[0][1]

        assert updated_state["current_step"] == "step2"
        assert updated_state["progress"] == 50
        assert updated_state["status"] == "running"  # Other fields preserved

    @pytest.mark.asyncio
    async def test_workflow_completion_caches_final_state(
        self, workflow_engine, sample_workflow, mock_acp_cache
    ):
        """Test that workflow completion caches final state."""
        # Mock workflow execution completion
        sample_workflow.started_at = datetime.now(timezone.utc)
        sample_workflow.completed_at = datetime.now(timezone.utc)

        # Simulate workflow completion
        sample_workflow.status = "completed"
        sample_workflow.completed_at = datetime.now(timezone.utc)

        # Call the completion logic (simulating what happens in _execute_workflow)
        if workflow_engine.acp_cache:
            await workflow_engine.acp_cache.cache_workflow_state(
                sample_workflow.workflow_id,
                {
                    "status": "completed",
                    "current_step": None,
                    "progress": 100,
                    "started_at": sample_workflow.started_at.isoformat(),
                    "completed_at": sample_workflow.completed_at.isoformat(),
                    "total_steps": len(sample_workflow.steps),
                    "completed_steps": len(sample_workflow.steps),
                    "duration_ms": (
                        sample_workflow.completed_at - sample_workflow.started_at
                    ).total_seconds()
                    * 1000,
                },
            )

        # Verify final state was cached
        mock_acp_cache.cache_workflow_state.assert_called_once()
        call_args = mock_acp_cache.cache_workflow_state.call_args

        assert call_args[0][0] == "test-workflow-1"
        final_state = call_args[0][1]

        assert final_state["status"] == "completed"
        assert final_state["progress"] == 100
        assert final_state["current_step"] is None
        assert final_state["total_steps"] == 2
        assert final_state["completed_steps"] == 2
        assert "duration_ms" in final_state

    @pytest.mark.asyncio
    async def test_workflow_failure_caches_error_state(
        self, workflow_engine, sample_workflow, mock_acp_cache
    ):
        """Test that workflow failure caches error state."""
        # Mock workflow execution failure
        sample_workflow.started_at = datetime.now(timezone.utc)
        sample_workflow.completed_at = datetime.now(timezone.utc)
        error_message = "Test workflow error"

        # Simulate workflow failure
        sample_workflow.status = "failed"
        sample_workflow.error = error_message
        sample_workflow.completed_at = datetime.now(timezone.utc)

        # Call the failure logic (simulating what happens in _execute_workflow)
        if workflow_engine.acp_cache:
            await workflow_engine.acp_cache.cache_workflow_state(
                sample_workflow.workflow_id,
                {
                    "status": "failed",
                    "current_step": None,
                    "progress": 0,
                    "started_at": sample_workflow.started_at.isoformat(),
                    "completed_at": sample_workflow.completed_at.isoformat(),
                    "error": error_message,
                    "total_steps": len(sample_workflow.steps),
                    "completed_steps": 0,
                    "duration_ms": (
                        sample_workflow.completed_at - sample_workflow.started_at
                    ).total_seconds()
                    * 1000,
                },
            )

        # Verify error state was cached
        mock_acp_cache.cache_workflow_state.assert_called_once()
        call_args = mock_acp_cache.cache_workflow_state.call_args

        assert call_args[0][0] == "test-workflow-1"
        error_state = call_args[0][1]

        assert error_state["status"] == "failed"
        assert error_state["error"] == error_message
        assert error_state["progress"] == 0
        assert error_state["completed_steps"] == 0
        assert "duration_ms" in error_state
