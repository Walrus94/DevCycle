"""
ACP configuration classes for DevCycle.

Based on the ACP specification and SDK requirements.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ACPConfig(BaseSettings):
    """Configuration for ACP integration."""

    # ACP Server Configuration
    server_host: str = Field(default="localhost", description="ACP server host")
    server_port: int = Field(default=8000, description="ACP server port")
    server_workers: int = Field(default=1, description="Number of server workers")

    # Agent Configuration
    agent_timeout: int = Field(
        default=300, description="Agent execution timeout in seconds"
    )
    agent_max_retries: int = Field(
        default=3, description="Maximum retry attempts for agent calls"
    )

    # Message Configuration
    message_timeout: int = Field(
        default=30, description="Message processing timeout in seconds"
    )
    message_max_size: int = Field(
        default=1048576, description="Maximum message size in bytes"
    )

    # Discovery Configuration
    discovery_enabled: bool = Field(default=True, description="Enable agent discovery")
    discovery_interval: int = Field(
        default=30, description="Discovery interval in seconds"
    )

    # Health Check Configuration
    health_check_interval: int = Field(
        default=60, description="Health check interval in seconds"
    )
    health_check_timeout: int = Field(
        default=10, description="Health check timeout in seconds"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")

    # Redis Configuration (for ACP state management)
    redis_url: Optional[str] = Field(
        default=None, description="Redis URL for ACP state management"
    )
    redis_ttl: int = Field(
        default=3600, description="Redis TTL for agent state in seconds"
    )

    # Advanced Configuration
    enable_metrics: bool = Field(
        default=True, description="Enable ACP metrics collection"
    )
    enable_tracing: bool = Field(
        default=True, description="Enable OpenTelemetry tracing"
    )

    model_config = SettingsConfigDict(env_prefix="DEVCYCLE_ACP_", case_sensitive=False)


class ACPAgentConfig(BaseSettings):
    """Configuration for individual ACP agents."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")

    # Agent Capabilities
    capabilities: list[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    input_types: list[str] = Field(
        default_factory=list, description="Supported input message types"
    )
    output_types: list[str] = Field(
        default_factory=list, description="Supported output message types"
    )

    # Agent Behavior
    is_stateful: bool = Field(
        default=False, description="Whether agent maintains state"
    )
    is_stateless: bool = Field(default=True, description="Whether agent is stateless")
    max_concurrent_runs: int = Field(
        default=10, description="Maximum concurrent agent runs"
    )

    # Resource Limits
    memory_limit_mb: int = Field(default=512, description="Memory limit in MB")
    cpu_limit: float = Field(default=1.0, description="CPU limit (cores)")

    # Hugging Face Integration
    hf_model_name: Optional[str] = Field(
        default=None, description="Hugging Face model name"
    )
    hf_token: Optional[str] = Field(default=None, description="Hugging Face API token")

    model_config = SettingsConfigDict(
        env_prefix="DEVCYCLE_ACP_AGENT_", case_sensitive=False
    )


class ACPWorkflowConfig(BaseSettings):
    """Configuration for ACP workflow orchestration."""

    # Workflow Engine
    workflow_engine_enabled: bool = Field(
        default=True, description="Enable workflow engine"
    )
    workflow_timeout: int = Field(
        default=1800, description="Workflow execution timeout in seconds"
    )
    workflow_max_steps: int = Field(default=100, description="Maximum workflow steps")

    # Agent Coordination
    coordination_strategy: str = Field(
        default="sequential", description="Agent coordination strategy"
    )
    parallel_execution: bool = Field(
        default=True, description="Enable parallel agent execution"
    )
    max_parallel_agents: int = Field(default=5, description="Maximum parallel agents")

    # Error Handling
    retry_failed_steps: bool = Field(
        default=True, description="Retry failed workflow steps"
    )
    max_retries: int = Field(default=3, description="Maximum retries for failed steps")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")

    # Monitoring
    enable_workflow_metrics: bool = Field(
        default=True, description="Enable workflow metrics"
    )
    enable_step_tracing: bool = Field(
        default=True, description="Enable step-level tracing"
    )

    model_config = SettingsConfigDict(
        env_prefix="DEVCYCLE_ACP_WORKFLOW_", case_sensitive=False
    )
