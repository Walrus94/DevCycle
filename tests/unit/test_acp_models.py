"""
Unit tests for ACP database models.

This module tests the Tortoise ORM models for ACP agent management,
workflow orchestration, and message logging.
"""

from datetime import datetime, timezone

import pytest
from tortoise import Tortoise

from devcycle.core.models.acp_models import (
    ACPAgent,
    ACPAgentMetrics,
    ACPMessageLog,
    ACPSystemMetrics,
    ACPWorkflow,
    ACPWorkflowMetrics,
    ACPWorkflowStep,
)


@pytest.fixture(scope="function")
async def setup_db():
    """Set up in-memory SQLite database for unit tests."""
    # Configure Tortoise for in-memory SQLite
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["devcycle.core.models.acp_models"]},
    )

    # Generate schema
    await Tortoise.generate_schemas()

    yield

    # Clean up
    await Tortoise.close_connections()


class TestACPAgent:
    """Test ACP agent database model."""

    @pytest.mark.asyncio
    async def test_create_agent(self, setup_db):
        """Test creating an ACP agent."""
        agent = await ACPAgent.create(
            agent_id="test-agent-1",
            name="Test Agent",
            capabilities=["code_generation", "testing"],
            status="online",
            last_heartbeat=datetime.now(timezone.utc),
        )

        assert agent.agent_id == "test-agent-1"
        assert agent.name == "Test Agent"
        assert agent.capabilities == ["code_generation", "testing"]
        assert agent.status == "online"
        assert agent.last_heartbeat is not None
        assert agent.created_at is not None
        assert agent.updated_at is not None

    @pytest.mark.asyncio
    async def test_agent_unique_constraint(self, setup_db):
        """Test agent ID uniqueness constraint."""
        # Create first agent
        await ACPAgent.create(
            agent_id="unique-agent", name="First Agent", capabilities=["testing"]
        )

        # Try to create second agent with same ID
        with pytest.raises(Exception):  # Should raise integrity error
            await ACPAgent.create(
                agent_id="unique-agent",
                name="Second Agent",
                capabilities=["code_generation"],
            )

    @pytest.mark.asyncio
    async def test_agent_capabilities_json(self, setup_db):
        """Test agent capabilities as JSON field."""
        capabilities = {
            "primary": ["code_generation"],
            "secondary": ["testing", "analysis"],
            "metadata": {"version": "1.0.0"},
        }

        agent = await ACPAgent.create(
            agent_id="json-agent", name="JSON Agent", capabilities=capabilities
        )

        assert agent.capabilities == capabilities
        assert isinstance(agent.capabilities, dict)

    @pytest.mark.asyncio
    async def test_agent_status_enum(self, setup_db):
        """Test agent status field."""
        statuses = ["offline", "online", "busy", "error"]

        for status in statuses:
            agent = await ACPAgent.create(
                agent_id=f"status-agent-{status}",
                name=f"Status Agent {status}",
                capabilities=["testing"],
                status=status,
            )
            assert agent.status == status


class TestACPWorkflow:
    """Test ACP workflow database model."""

    @pytest.mark.asyncio
    async def test_create_workflow(self, setup_db):
        """Test creating an ACP workflow."""
        workflow = await ACPWorkflow.create(
            workflow_id="test-workflow-1",
            name="Test Workflow",
            version="1.0.0",
            status="pending",
            steps=[
                {
                    "step_id": "step-1",
                    "step_name": "Generate Code",
                    "agent_id": "code-generator",
                },
                {"step_id": "step-2", "step_name": "Run Tests", "agent_id": "tester"},
            ],
        )

        assert workflow.workflow_id == "test-workflow-1"
        assert workflow.name == "Test Workflow"
        assert workflow.version == "1.0.0"
        assert workflow.status == "pending"
        assert len(workflow.steps) == 2
        assert workflow.steps[0]["step_id"] == "step-1"

    @pytest.mark.asyncio
    async def test_workflow_retry_count(self, setup_db):
        """Test workflow retry count functionality."""
        workflow = await ACPWorkflow.create(
            workflow_id="retry-workflow",
            name="Retry Workflow",
            retry_count=2,
            max_retries=5,
        )

        assert workflow.retry_count == 2
        assert workflow.max_retries == 5

    @pytest.mark.asyncio
    async def test_workflow_timestamps(self, setup_db):
        """Test workflow timestamp fields."""
        now = datetime.now(timezone.utc)

        workflow = await ACPWorkflow.create(
            workflow_id="timestamp-workflow",
            name="Timestamp Workflow",
            started_at=now,
            completed_at=now,
        )

        assert workflow.started_at == now
        assert workflow.completed_at == now
        assert workflow.created_at is not None
        assert workflow.updated_at is not None


class TestACPWorkflowStep:
    """Test ACP workflow step database model."""

    @pytest.mark.asyncio
    async def test_create_workflow_step(self, setup_db):
        """Test creating a workflow step."""
        # First create a workflow
        workflow = await ACPWorkflow.create(
            workflow_id="parent-workflow", name="Parent Workflow"
        )

        # Create workflow step
        step = await ACPWorkflowStep.create(
            workflow=workflow,
            step_id="test-step-1",
            step_name="Test Step",
            agent_id="test-agent",
            status="pending",
            input_data={"input": "test"},
            depends_on=["step-0"],
        )

        assert step.step_id == "test-step-1"
        assert step.step_name == "Test Step"
        assert step.agent_id == "test-agent"
        assert step.status == "pending"
        assert step.input_data == {"input": "test"}
        assert step.depends_on == ["step-0"]
        assert step.workflow_id == workflow.id

    @pytest.mark.asyncio
    async def test_workflow_step_foreign_key(self, setup_db):
        """Test workflow step foreign key relationship."""
        workflow = await ACPWorkflow.create(
            workflow_id="fk-workflow", name="FK Workflow"
        )

        step = await ACPWorkflowStep.create(
            workflow=workflow,
            step_id="fk-step",
            step_name="FK Step",
            agent_id="test-agent",
        )

        # Test relationship
        assert step.workflow.id == workflow.id
        assert step.workflow.workflow_id == "fk-workflow"

    @pytest.mark.asyncio
    async def test_workflow_step_cascade_delete(self, setup_db):
        """Test workflow step cascade delete."""
        workflow = await ACPWorkflow.create(
            workflow_id="cascade-workflow", name="Cascade Workflow"
        )

        step = await ACPWorkflowStep.create(
            workflow=workflow,
            step_id="cascade-step",
            step_name="Cascade Step",
            agent_id="test-agent",
        )

        step_id = step.id

        # Delete workflow
        await workflow.delete()

        # Check that step is also deleted
        with pytest.raises(Exception):  # Should not exist
            await ACPWorkflowStep.get(id=step_id)


class TestACPMessageLog:
    """Test ACP message log database model."""

    @pytest.mark.asyncio
    async def test_create_message_log(self, setup_db):
        """Test creating a message log entry."""
        log = await ACPMessageLog.create(
            message_id="test-message-1",
            from_agent="agent-1",
            to_agent="agent-2",
            message_type="code_generation",
            content={"requirements": "test"},
            response={"generated_code": "def test(): pass"},
            workflow_id="workflow-1",
            success=True,
            processing_time_ms=150.5,
        )

        assert log.message_id == "test-message-1"
        assert log.from_agent == "agent-1"
        assert log.to_agent == "agent-2"
        assert log.message_type == "code_generation"
        assert log.content == {"requirements": "test"}
        assert log.response == {"generated_code": "def test(): pass"}
        assert log.workflow_id == "workflow-1"
        assert log.success is True
        assert log.processing_time_ms == 150.5
        assert log.timestamp is not None

    @pytest.mark.asyncio
    async def test_message_log_error_case(self, setup_db):
        """Test message log for error case."""
        log = await ACPMessageLog.create(
            message_id="error-message-1",
            from_agent="agent-1",
            to_agent="agent-2",
            message_type="invalid_type",
            content={"test": "data"},
            success=False,
            error="Agent not found",
        )

        assert log.success is False
        assert log.error == "Agent not found"
        assert log.response is None


class TestACPAgentMetrics:
    """Test ACP agent metrics database model."""

    @pytest.mark.asyncio
    async def test_create_agent_metrics(self, setup_db):
        """Test creating agent metrics."""
        metrics = await ACPAgentMetrics.create(
            agent_id="test-agent",
            metric_name="response_time",
            metric_value=125.5,
            metric_unit="ms",
            metadata={"version": "1.0.0"},
        )

        assert metrics.agent_id == "test-agent"
        assert metrics.metric_name == "response_time"
        assert metrics.metric_value == 125.5
        assert metrics.metric_unit == "ms"
        assert metrics.metadata == {"version": "1.0.0"}
        assert metrics.timestamp is not None

    @pytest.mark.asyncio
    async def test_agent_metrics_query(self, setup_db):
        """Test querying agent metrics."""
        # Create multiple metrics for same agent
        await ACPAgentMetrics.create(
            agent_id="query-agent",
            metric_name="cpu_usage",
            metric_value=75.0,
            metric_unit="percent",
        )

        await ACPAgentMetrics.create(
            agent_id="query-agent",
            metric_name="memory_usage",
            metric_value=512.0,
            metric_unit="MB",
        )

        # Query metrics for agent
        metrics = await ACPAgentMetrics.filter(agent_id="query-agent").all()
        assert len(metrics) == 2

        cpu_metric = await ACPAgentMetrics.filter(
            agent_id="query-agent", metric_name="cpu_usage"
        ).first()
        assert cpu_metric.metric_value == 75.0


class TestACPWorkflowMetrics:
    """Test ACP workflow metrics database model."""

    @pytest.mark.asyncio
    async def test_create_workflow_metrics(self, setup_db):
        """Test creating workflow metrics."""
        metrics = await ACPWorkflowMetrics.create(
            workflow_id="test-workflow",
            metric_name="execution_time",
            metric_value=3000.0,
            metric_unit="ms",
            metadata={"steps_count": 5},
        )

        assert metrics.workflow_id == "test-workflow"
        assert metrics.metric_name == "execution_time"
        assert metrics.metric_value == 3000.0
        assert metrics.metric_unit == "ms"
        assert metrics.metadata == {"steps_count": 5}


class TestACPSystemMetrics:
    """Test ACP system metrics database model."""

    @pytest.mark.asyncio
    async def test_create_system_metrics(self, setup_db):
        """Test creating system metrics."""
        metrics = await ACPSystemMetrics.create(
            metric_name="total_agents",
            metric_value=10.0,
            metric_unit="count",
            metadata={"active": 8, "offline": 2},
        )

        assert metrics.metric_name == "total_agents"
        assert metrics.metric_value == 10.0
        assert metrics.metric_unit == "count"
        assert metrics.metadata == {"active": 8, "offline": 2}

    @pytest.mark.asyncio
    async def test_system_metrics_aggregation(self, setup_db):
        """Test system metrics aggregation."""
        # Create multiple system metrics
        for i in range(5):
            await ACPSystemMetrics.create(
                metric_name="active_workflows",
                metric_value=float(i + 1),
                metric_unit="count",
            )

        # Query all metrics
        metrics = await ACPSystemMetrics.filter(metric_name="active_workflows").all()

        assert len(metrics) == 5
        values = [m.metric_value for m in metrics]
        assert sum(values) == 15.0  # 1+2+3+4+5


class TestACPDatabaseRelationships:
    """Test ACP database model relationships."""

    @pytest.mark.asyncio
    async def test_workflow_steps_relationship(self, setup_db):
        """Test workflow-steps relationship."""
        # Create workflow
        workflow = await ACPWorkflow.create(
            workflow_id="relationship-workflow", name="Relationship Workflow"
        )

        # Create multiple steps
        await ACPWorkflowStep.create(
            workflow=workflow, step_id="step-1", step_name="Step 1", agent_id="agent-1"
        )

        await ACPWorkflowStep.create(
            workflow=workflow, step_id="step-2", step_name="Step 2", agent_id="agent-2"
        )

        # Test relationship
        workflow_steps = await workflow.workflow_steps.all()
        assert len(workflow_steps) == 2

        step_ids = [s.step_id for s in workflow_steps]
        assert "step-1" in step_ids
        assert "step-2" in step_ids

    @pytest.mark.asyncio
    async def test_workflow_metrics_consistency(self, setup_db):
        """Test workflow metrics consistency."""
        workflow_id = "metrics-workflow"

        # Create workflow
        await ACPWorkflow.create(workflow_id=workflow_id, name="Metrics Workflow")

        # Create workflow metrics
        await ACPWorkflowMetrics.create(
            workflow_id=workflow_id, metric_name="duration", metric_value=1000.0
        )

        # Verify consistency
        workflow = await ACPWorkflow.get(workflow_id=workflow_id)
        metrics = await ACPWorkflowMetrics.filter(workflow_id=workflow_id).all()

        assert workflow.workflow_id == workflow_id
        assert len(metrics) == 1
        assert metrics[0].metric_value == 1000.0
