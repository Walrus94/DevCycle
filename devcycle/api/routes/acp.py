"""
ACP API routes for DevCycle.

This module provides FastAPI endpoints for ACP agent management and communication.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.acp import (
    ACPAgentConfig,
    ACPAgentInfo,
    ACPAgentStatus,
    ACPMessage,
    ACPResponse,
)
from ...core.acp.agents import (
    BusinessAnalystACPAgent,
    CodeGeneratorACPAgent,
    TestingACPAgent,
)
from ...core.acp.models import ACPMessageType, ACPPriority
from ...core.acp.services import ACPAgentRegistry, ACPMessageRouter
from ...core.auth.fastapi_users import current_active_user
from ...core.auth.tortoise_models import User
from ...core.dependencies import get_agent_registry, get_message_router

logger = logging.getLogger(__name__)

# Create ACP router
acp_router = APIRouter(prefix="/acp", tags=["ACP"])

# ACP services are now dependency injected via get_agent_registry and get_message_router


# Pydantic models for API requests/responses
class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")
    capabilities: List[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    input_types: List[str] = Field(
        default_factory=list, description="Supported input message types"
    )
    output_types: List[str] = Field(
        default_factory=list, description="Supported output message types"
    )
    is_stateful: bool = Field(
        default=False, description="Whether agent maintains state"
    )
    max_concurrent_runs: int = Field(
        default=10, description="Maximum concurrent agent runs"
    )
    hf_model_name: Optional[str] = Field(
        default=None, description="Hugging Face model name"
    )


class MessageRequest(BaseModel):
    """Request model for sending messages."""

    message_type: str = Field(..., description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    target_agent_id: Optional[str] = Field(default=None, description="Target agent ID")
    priority: str = Field(default="normal", description="Message priority")
    timeout: Optional[int] = Field(
        default=None, description="Message timeout in seconds"
    )


class BroadcastRequest(BaseModel):
    """Request model for broadcasting messages."""

    message_type: str = Field(..., description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    capability: Optional[str] = Field(default=None, description="Target capability")
    priority: str = Field(default="normal", description="Message priority")


class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""

    workflow_name: str = Field(..., description="Workflow name")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata"
    )


# Agent Management Endpoints
@acp_router.get("/agents", response_model=List[ACPAgentInfo])
async def list_agents(
    status: Optional[ACPAgentStatus] = None,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> List[ACPAgentInfo]:
    """List all registered agents."""
    try:
        agents = await registry.list_agents(status)
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.get("/agents/{agent_id}", response_model=ACPAgentInfo)
async def get_agent(
    agent_id: str,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> ACPAgentInfo:
    """Get agent information by ID."""
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/agents/register", response_model=Dict[str, str])
async def register_agent(
    request: AgentRegistrationRequest,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, str]:
    """Register a new agent."""
    try:
        agent_info = ACPAgentInfo(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            agent_version=request.agent_version,
            capabilities=request.capabilities,
            input_types=request.input_types,
            output_types=request.output_types,
            status=ACPAgentStatus.OFFLINE,
            is_stateful=request.is_stateful,
            max_concurrent_runs=request.max_concurrent_runs,
            hf_model_name=request.hf_model_name,
        )

        # Create a simple wrapper for ACPAgentInfo to work with registry
        class AgentInfoWrapper:
            def __init__(self, agent_info: ACPAgentInfo):
                self.agent_info = agent_info

            def get_agent_info(self) -> ACPAgentInfo:
                return self.agent_info

        wrapper = AgentInfoWrapper(agent_info)
        success = await registry.register_agent(wrapper)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to register agent")

        return {
            "message": "Agent registered successfully",
            "agent_id": request.agent_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.delete("/agents/{agent_id}", response_model=Dict[str, str])
async def unregister_agent(
    agent_id: str,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, str]:
    """Unregister an agent."""
    try:
        success = await registry.unregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")

        return {"message": "Agent unregistered successfully", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.get("/agents/discover/{capability}", response_model=List[ACPAgentInfo])
async def discover_agents(
    capability: str,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> List[ACPAgentInfo]:
    """Discover agents by capability."""
    try:
        agents = await registry.discover_agents(capability)
        return agents
    except Exception as e:
        logger.error(f"Failed to discover agents with capability {capability}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Message Communication Endpoints
@acp_router.post("/messages/send", response_model=ACPResponse)
async def send_message(
    request: MessageRequest,
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> ACPResponse:
    """Send a message to an agent."""
    try:
        message = ACPMessage(
            message_id=f"msg_{datetime.now(timezone.utc).timestamp()}",
            message_type=ACPMessageType(request.message_type),
            content=request.content,
            target_agent_id=request.target_agent_id,
            priority=ACPPriority(request.priority),
            timeout=request.timeout,
        )

        response = await router.route_message(message)
        return response
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/messages/broadcast", response_model=List[ACPResponse])
async def broadcast_message(
    request: BroadcastRequest,
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> List[ACPResponse]:
    """Broadcast a message to multiple agents."""
    try:
        message = ACPMessage(
            message_id=f"broadcast_{datetime.now(timezone.utc).timestamp()}",
            message_type=ACPMessageType(request.message_type),
            content=request.content,
            priority=ACPPriority(request.priority),
        )

        responses = await router.broadcast_message(
            message, capability=request.capability
        )
        return responses
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent Health and Status Endpoints
@acp_router.get("/health", response_model=Dict[str, Any])
async def health_check(
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, Any]:
    """Get ACP system health status."""
    try:
        health_status = await registry.health_check_all()
        metrics = await registry.get_metrics()

        return {
            "status": "healthy" if all(health_status.values()) else "degraded",
            "agent_health": health_status,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> Dict[str, Any]:
    """Get ACP system metrics."""
    try:
        registry_metrics = await registry.get_metrics()
        router_metrics = router.get_stats()

        return {
            "registry": registry_metrics,
            "router": router_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Pre-built Agent Endpoints
@acp_router.post("/agents/code-generator/start", response_model=Dict[str, str])
async def start_code_generator_agent(
    background_tasks: BackgroundTasks,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, str]:
    """Start the code generator ACP agent."""
    try:
        agent_config = ACPAgentConfig(
            agent_id="code-generator",
            agent_name="Code Generator",
            capabilities=["code_generation", "text_processing"],
            hf_model_name="microsoft/CodeGPT-small-python",
        )

        agent = CodeGeneratorACPAgent(agent_config)

        # Register agent
        await registry.register_agent(agent)

        # Start agent in background
        background_tasks.add_task(agent.run)

        return {"message": "Code generator agent started", "agent_id": "code-generator"}
    except Exception as e:
        logger.error(f"Failed to start code generator agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/agents/testing/start", response_model=Dict[str, str])
async def start_testing_agent(
    background_tasks: BackgroundTasks,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, str]:
    """Start the testing ACP agent."""
    try:
        agent_config = ACPAgentConfig(
            agent_id="testing",
            agent_name="Testing Agent",
            capabilities=["testing", "code_analysis", "quality_assurance"],
            hf_model_name="microsoft/CodeGPT-small-python",
        )

        agent = TestingACPAgent(agent_config)

        # Register agent
        await registry.register_agent(agent)

        # Start agent in background
        background_tasks.add_task(agent.run)

        return {"message": "Testing agent started", "agent_id": "testing"}
    except Exception as e:
        logger.error(f"Failed to start testing agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/agents/business-analyst/start", response_model=Dict[str, str])
async def start_business_analyst_agent(
    background_tasks: BackgroundTasks,
    registry: ACPAgentRegistry = Depends(get_agent_registry),
    current_user: User = Depends(current_active_user),
) -> Dict[str, str]:
    """Start the business analyst ACP agent."""
    try:
        agent_config = ACPAgentConfig(
            agent_id="business-analyst",
            agent_name="Business Analyst",
            capabilities=[
                "business_analysis",
                "requirements_gathering",
                "stakeholder_analysis",
            ],
            hf_model_name="microsoft/CodeGPT-small",
        )

        agent = BusinessAnalystACPAgent(agent_config)

        # Register agent
        await registry.register_agent(agent)

        # Start agent in background
        background_tasks.add_task(agent.run)

        return {
            "message": "Business analyst agent started",
            "agent_id": "business-analyst",
        }
    except Exception as e:
        logger.error(f"Failed to start business analyst agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Quick Action Endpoints
@acp_router.post("/quick/generate-code", response_model=ACPResponse)
async def quick_generate_code(
    requirements: str,
    language: str = "python",
    framework: str = "",
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> ACPResponse:
    """Quick code generation endpoint."""
    try:
        message = ACPMessage(
            message_id=f"quick_code_{datetime.now(timezone.utc).timestamp()}",
            message_type=ACPMessageType.REQUEST,
            content={
                "requirements": requirements,
                "language": language,
                "framework": framework,
            },
            target_agent_id="code-generator",
        )

        response = await router.route_message(message)
        return response
    except Exception as e:
        logger.error(f"Quick code generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/quick/generate-tests", response_model=ACPResponse)
async def quick_generate_tests(
    code: str,
    language: str = "python",
    test_framework: str = "pytest",
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> ACPResponse:
    """Quick test generation endpoint."""
    try:
        message = ACPMessage(
            message_id=f"quick_tests_{datetime.now(timezone.utc).timestamp()}",
            message_type=ACPMessageType.REQUEST,
            content={
                "code": code,
                "language": language,
                "test_framework": test_framework,
            },
            target_agent_id="testing",
        )

        response = await router.route_message(message)
        return response
    except Exception as e:
        logger.error(f"Quick test generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@acp_router.post("/quick/analyze-requirements", response_model=ACPResponse)
async def quick_analyze_requirements(
    project_description: str,
    business_context: str = "",
    stakeholders: List[str] = [],
    router: ACPMessageRouter = Depends(get_message_router),
    current_user: User = Depends(current_active_user),
) -> ACPResponse:
    """Quick requirements analysis endpoint."""
    try:
        message = ACPMessage(
            message_id=f"quick_req_{datetime.now(timezone.utc).timestamp()}",
            message_type=ACPMessageType.REQUEST,
            content={
                "project_description": project_description,
                "business_context": business_context,
                "stakeholders": stakeholders,
            },
            target_agent_id="business-analyst",
        )

        response = await router.route_message(message)
        return response
    except Exception as e:
        logger.error(f"Quick requirements analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
