"""
ACP models and data structures for DevCycle.

Based on the ACP SDK models and specifications.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Re-export ACP SDK models for convenience
from pydantic import BaseModel, Field


class ACPAgentStatus(str, Enum):
    """Agent status enumeration."""

    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ACPMessageType(str, Enum):
    """ACP message type enumeration."""

    # Core message types
    PING = "ping"
    PONG = "pong"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"

    # DevCycle specific message types
    GENERATE_CODE = "generate_code"
    ANALYZE_CODE = "analyze_code"
    REFACTOR_CODE = "refactor_code"
    GENERATE_TESTS = "generate_tests"
    RUN_TESTS = "run_tests"
    DEPLOY_APPLICATION = "deploy_application"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    SCALE_APPLICATION = "scale_application"
    ANALYZE_COVERAGE = "analyze_coverage"

    # Business analysis message types
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    GATHER_STAKEHOLDER_NEEDS = "gather_stakeholder_needs"
    ANALYZE_BUSINESS_PROCESS = "analyze_business_process"
    CREATE_USER_STORIES = "create_user_stories"
    CREATE_ACCEPTANCE_CRITERIA = "create_acceptance_criteria"

    # Test message types
    TEST_MESSAGE = "test_message"

    # Workflow message types
    START_WORKFLOW = "start_workflow"
    WORKFLOW_STEP = "workflow_step"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"


class ACPPriority(str, Enum):
    """Message priority enumeration."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ACPAgentInfo(BaseModel):
    """Information about an ACP agent."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")

    # Agent capabilities
    capabilities: List[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    input_types: List[str] = Field(
        default_factory=list, description="Supported input message types"
    )
    output_types: List[str] = Field(
        default_factory=list, description="Supported output message types"
    )

    # Agent status
    status: ACPAgentStatus = Field(
        default=ACPAgentStatus.OFFLINE, description="Current agent status"
    )
    last_heartbeat: Optional[datetime] = Field(
        default=None, description="Last heartbeat timestamp"
    )

    # Agent metadata
    is_stateful: bool = Field(
        default=False, description="Whether agent maintains state"
    )
    max_concurrent_runs: int = Field(
        default=10, description="Maximum concurrent agent runs"
    )
    current_runs: int = Field(
        default=0, description="Current number of running instances"
    )

    # Resource information
    memory_usage_mb: Optional[float] = Field(
        default=None, description="Current memory usage in MB"
    )
    cpu_usage_percent: Optional[float] = Field(
        default=None, description="Current CPU usage percentage"
    )

    # Hugging Face integration
    hf_model_name: Optional[str] = Field(
        default=None, description="Hugging Face model name"
    )

    model_config = {"use_enum_values": True}


class ACPMessage(BaseModel):
    """ACP message structure for DevCycle."""

    message_id: str = Field(..., description="Unique message identifier")
    message_type: ACPMessageType = Field(..., description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )

    # Message routing
    source_agent_id: Optional[str] = Field(default=None, description="Source agent ID")
    target_agent_id: Optional[str] = Field(default=None, description="Target agent ID")
    workflow_id: Optional[str] = Field(
        default=None, description="Workflow ID if part of workflow"
    )

    # Message properties
    priority: ACPPriority = Field(
        default=ACPPriority.NORMAL, description="Message priority"
    )
    timeout: Optional[int] = Field(
        default=None, description="Message timeout in seconds"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message creation timestamp",
    )
    expires_at: Optional[datetime] = Field(
        default=None, description="Message expiration timestamp"
    )

    model_config = {"use_enum_values": True}


class ACPResponse(BaseModel):
    """ACP response structure for DevCycle."""

    response_id: str = Field(..., description="Unique response identifier")
    message_id: str = Field(..., description="Original message ID")
    success: bool = Field(..., description="Whether the operation was successful")

    # Response content
    content: Dict[str, Any] = Field(
        default_factory=dict, description="Response content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )

    # Error information
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )

    # Performance metrics
    processing_time_ms: Optional[float] = Field(
        default=None, description="Processing time in milliseconds"
    )
    memory_used_mb: Optional[float] = Field(
        default=None, description="Memory used in MB"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response creation timestamp",
    )

    @classmethod
    def create_success(
        cls, message_id: str, content: Dict[str, Any], **kwargs: Any
    ) -> "ACPResponse":
        """Create a successful response."""
        return cls(
            response_id=f"resp_{message_id}",
            message_id=message_id,
            success=True,
            content=content,
            **kwargs,
        )

    @classmethod
    def create_error(
        cls,
        message_id: str,
        error: str,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> "ACPResponse":
        """Create an error response."""
        return cls(
            response_id=f"resp_{message_id}",
            message_id=message_id,
            success=False,
            error=error,
            error_code=error_code,
            **kwargs,
        )


class ACPWorkflowStep(BaseModel):
    """Individual step in an ACP workflow."""

    step_id: str = Field(..., description="Unique step identifier")
    step_name: str = Field(..., description="Human-readable step name")
    agent_id: str = Field(..., description="Agent responsible for this step")

    # Step configuration
    input_data: Dict[str, Any] = Field(
        default_factory=dict, description="Step input data"
    )
    output_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Step output data"
    )

    # Step status
    status: str = Field(default="pending", description="Step status")
    started_at: Optional[datetime] = Field(
        default=None, description="Step start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Step completion timestamp"
    )

    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list, description="Steps this step depends on"
    )

    # Error handling
    error: Optional[str] = Field(
        default=None, description="Error message if step failed"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class ACPWorkflow(BaseModel):
    """ACP workflow definition."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_name: str = Field(..., description="Human-readable workflow name")
    workflow_version: str = Field(default="1.0.0", description="Workflow version")

    # Workflow steps
    steps: List[ACPWorkflowStep] = Field(
        default_factory=list, description="Workflow steps"
    )

    # Workflow status
    status: str = Field(default="pending", description="Workflow status")
    started_at: Optional[datetime] = Field(
        default=None, description="Workflow start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Workflow completion timestamp"
    )

    # Workflow metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata"
    )
    created_by: Optional[str] = Field(
        default=None, description="User who created the workflow"
    )

    # Error handling
    error: Optional[str] = Field(
        default=None, description="Error message if workflow failed"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class ACPMetrics(BaseModel):
    """ACP system metrics."""

    # Agent metrics
    total_agents: int = Field(
        default=0, description="Total number of registered agents"
    )
    online_agents: int = Field(default=0, description="Number of online agents")
    busy_agents: int = Field(default=0, description="Number of busy agents")
    error_agents: int = Field(default=0, description="Number of agents in error state")

    # Message metrics
    messages_processed: int = Field(default=0, description="Total messages processed")
    messages_successful: int = Field(default=0, description="Successful messages")
    messages_failed: int = Field(default=0, description="Failed messages")
    messages_pending: int = Field(default=0, description="Pending messages")

    # Performance metrics
    avg_processing_time_ms: float = Field(
        default=0.0, description="Average processing time in ms"
    )
    max_processing_time_ms: float = Field(
        default=0.0, description="Maximum processing time in ms"
    )
    min_processing_time_ms: float = Field(
        default=0.0, description="Minimum processing time in ms"
    )

    # Workflow metrics
    active_workflows: int = Field(default=0, description="Number of active workflows")
    completed_workflows: int = Field(
        default=0, description="Number of completed workflows"
    )
    failed_workflows: int = Field(default=0, description="Number of failed workflows")

    # Timestamps
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last metrics update",
    )
