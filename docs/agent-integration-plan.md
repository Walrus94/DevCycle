# Agent Integration Plan

## Overview

This document outlines the integration plan for the new Agent Lifecycle Management System with existing DevCycle components. The integration will enhance the current agent system with comprehensive lifecycle management while maintaining backward compatibility.

## Integration Architecture

### Current System Components

1. **AgentService**: Business logic for agent management
2. **AgentRepository**: Database access layer
3. **AgentAvailabilityService**: Agent availability and load balancing
4. **API Endpoints**: REST API for agent operations
5. **Database Models**: SQLAlchemy models for persistence
6. **Hugging Face Integration**: HF Spaces for agent hosting

### New Lifecycle Components

1. **AgentLifecycleService**: High-level lifecycle management
2. **AgentLifecycleManager**: Individual agent lifecycle management
3. **AgentLifecycleState**: State definitions and transitions
4. **Event System**: State transition events and handlers

## Integration Strategy

### Phase 1: Core Integration

#### 1.1 Update AgentService

**Objective**: Integrate lifecycle management into the existing AgentService

**Changes Required**:

```python
# devcycle/core/services/agent_service.py

from ..agents.lifecycle import AgentLifecycleService, AgentLifecycleState

class AgentService(BaseService[Agent]):
    def __init__(
        self,
        agent_repository: AgentRepository,
        task_repository: AgentTaskRepository,
        lifecycle_service: Optional[AgentLifecycleService] = None
    ):
        super().__init__(agent_repository)
        self.agent_repository = agent_repository
        self.task_repository = task_repository
        self.lifecycle_service = lifecycle_service or AgentLifecycleService()

    async def register_agent(self, registration: AgentRegistration) -> AgentResponse:
        """Register a new agent with lifecycle management."""
        # Existing validation logic...

        # Create agent through repository
        agent = await self.repository.create(**agent_data)

        # Register with lifecycle service
        await self.lifecycle_service.register_agent(agent.id)

        # Convert to response model
        return await self._to_agent_response(agent)

    async def start_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Start an agent with lifecycle management."""
        # Check if agent exists
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        # Start through lifecycle service
        success = await self.lifecycle_service.start_agent(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.ONLINE)

        return await self._to_agent_response(agent)

    async def stop_agent(self, agent_id: UUID) -> Optional[AgentResponse]:
        """Stop an agent with lifecycle management."""
        # Stop through lifecycle service
        success = await self.lifecycle_service.stop_agent(agent_id)
        if not success:
            return None

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.OFFLINE)

        agent = await self.get_by_id(agent_id)
        return await self._to_agent_response(agent) if agent else None

    async def assign_task_to_agent(
        self, agent_id: UUID, task_type: str, parameters: Dict[str, Any]
    ) -> Optional[AgentTask]:
        """Assign a task with lifecycle management."""
        # Check if agent is available through lifecycle service
        if agent_id not in self.lifecycle_service.get_available_agents():
            raise ValueError("Agent is not available for task assignment")

        # Assign task through lifecycle service
        success = await self.lifecycle_service.assign_task(agent_id)
        if not success:
            raise ValueError("Failed to assign task to agent")

        # Create task through repository
        task_data = {
            "agent_id": agent_id,
            "task_type": task_type,
            "status": "pending",
            "parameters": json.dumps(parameters),
        }

        task = await self.task_repository.create(**task_data)

        # Update agent status in database
        await self.agent_repository.update_agent_status(agent_id, AgentStatus.BUSY)

        return task

    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[AgentTask]:
        """Update task status with lifecycle management."""
        # Update task through repository
        updated_task = await self.task_repository.update_task_status(
            task_id, status, result, error
        )

        if updated_task and status in ["completed", "failed"]:
            # Complete task through lifecycle service
            await self.lifecycle_service.complete_task(updated_task.agent_id)

            # Update agent status in database
            await self.agent_repository.update_agent_status(
                updated_task.agent_id, AgentStatus.IDLE
            )

        return updated_task

    def get_agent_lifecycle_status(self, agent_id: UUID) -> Optional[Dict[str, Any]]:
        """Get agent lifecycle status."""
        return self.lifecycle_service.get_agent_status(agent_id)

    def get_all_agent_lifecycle_statuses(self) -> Dict[UUID, Dict[str, Any]]:
        """Get all agent lifecycle statuses."""
        return self.lifecycle_service.get_all_agent_statuses()
```

#### 1.2 Update Dependencies

**Objective**: Add lifecycle service to dependency injection

**Changes Required**:

```python
# devcycle/core/dependencies.py

from ..agents.lifecycle import AgentLifecycleService

async def get_lifecycle_service() -> AgentLifecycleService:
    """
    Get agent lifecycle service dependency.

    Returns:
        AgentLifecycleService instance
    """
    return AgentLifecycleService()

async def get_agent_service(
    agent_repository: AgentRepository = Depends(get_agent_repository),
    agent_task_repository: AgentTaskRepository = Depends(get_agent_task_repository),
    lifecycle_service: AgentLifecycleService = Depends(get_lifecycle_service),
) -> AgentService:
    """
    Get agent service dependency with lifecycle integration.

    Args:
        agent_repository: Agent repository instance
        agent_task_repository: Agent task repository instance
        lifecycle_service: Lifecycle service instance

    Returns:
        AgentService instance
    """
    return AgentService(agent_repository, agent_task_repository, lifecycle_service)
```

#### 1.3 Update API Endpoints

**Objective**: Add lifecycle endpoints to the existing API

**Changes Required**:

```python
# devcycle/api/routes/agents.py

@router.get("/{agent_id}/lifecycle", response_model=Dict[str, Any])
async def get_agent_lifecycle_status(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    Get agent lifecycle status.

    Returns detailed lifecycle information for the specified agent.
    """
    try:
        status = agent_service.get_agent_lifecycle_status(agent_id)
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        return status
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent lifecycle status",
        )

@router.get("/lifecycle/statuses", response_model=Dict[UUID, Dict[str, Any]])
async def get_all_agent_lifecycle_statuses(
    agent_service: AgentService = Depends(get_agent_service)
) -> Dict[UUID, Dict[str, Any]]:
    """
    Get all agent lifecycle statuses.

    Returns lifecycle information for all agents in the system.
    """
    try:
        return agent_service.get_all_agent_lifecycle_statuses()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent lifecycle statuses",
        )

@router.post("/{agent_id}/lifecycle/start", response_model=AgentResponse)
async def start_agent_lifecycle(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Start an agent through lifecycle management.

    Transitions agent to ONLINE state and makes it available for tasks.
    """
    try:
        agent = await agent_service.start_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        return agent
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start agent",
        )

@router.post("/{agent_id}/lifecycle/stop", response_model=AgentResponse)
async def stop_agent_lifecycle(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Stop an agent through lifecycle management.

    Transitions agent to OFFLINE state and stops task processing.
    """
    try:
        agent = await agent_service.stop_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        return agent
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop agent",
        )

@router.post("/{agent_id}/lifecycle/maintenance", response_model=AgentResponse)
async def put_in_maintenance(
    agent_id: UUID,
    reason: str = "Scheduled maintenance",
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Put agent in maintenance mode.

    Transitions agent to MAINTENANCE state for scheduled maintenance.
    """
    try:
        # Get lifecycle service from agent service
        lifecycle_service = agent_service.lifecycle_service

        success = await lifecycle_service.put_in_maintenance(agent_id, reason)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot put agent in maintenance mode"
            )

        # Update database status
        await agent_service.agent_repository.update_agent_status(
            agent_id, AgentStatus.MAINTENANCE
        )

        agent = await agent_service.get_by_id(agent_id)
        return await agent_service._to_agent_response(agent) if agent else None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to put agent in maintenance mode",
        )

@router.post("/{agent_id}/lifecycle/resume", response_model=AgentResponse)
async def resume_from_maintenance(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentResponse:
    """
    Resume agent from maintenance mode.

    Transitions agent from MAINTENANCE to ONLINE state.
    """
    try:
        # Get lifecycle service from agent service
        lifecycle_service = agent_service.lifecycle_service

        success = await lifecycle_service.resume_from_maintenance(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent is not in maintenance mode"
            )

        # Update database status
        await agent_service.agent_repository.update_agent_status(
            agent_id, AgentStatus.ONLINE
        )

        agent = await agent_service.get_by_id(agent_id)
        return await agent_service._to_agent_response(agent) if agent else None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume agent from maintenance",
        )
```

### Phase 2: Hugging Face Integration

#### 2.1 HF Space Lifecycle Sync

**Objective**: Sync HF Space status with lifecycle states

**Changes Required**:

```python
# devcycle/huggingface/lifecycle_sync.py

from typing import Dict, Optional
from uuid import UUID

from ..core.agents.lifecycle import AgentLifecycleService, AgentLifecycleState
from .client import HuggingFaceClient

class HFLifecycleSync:
    """Sync Hugging Face Space status with agent lifecycle states."""

    # Mapping from HF Space states to lifecycle states
    HF_TO_LIFECYCLE_STATES = {
        "building": AgentLifecycleState.DEPLOYING,
        "running": AgentLifecycleState.ONLINE,
        "sleeping": AgentLifecycleState.IDLE,
        "error": AgentLifecycleState.ERROR,
        "paused": AgentLifecycleState.SUSPENDED,
        "stopped": AgentLifecycleState.OFFLINE,
    }

    def __init__(self, lifecycle_service: AgentLifecycleService, hf_client: HuggingFaceClient):
        self.lifecycle_service = lifecycle_service
        self.hf_client = hf_client
        self.agent_to_space_mapping: Dict[UUID, str] = {}

    def register_agent_space(self, agent_id: UUID, space_id: str) -> None:
        """Register mapping between agent and HF space."""
        self.agent_to_space_mapping[agent_id] = space_id

    async def sync_space_status(self, agent_id: UUID) -> bool:
        """Sync HF space status with agent lifecycle state."""
        space_id = self.agent_to_space_mapping.get(agent_id)
        if not space_id:
            return False

        try:
            # Get HF space status
            space_status = await self.hf_client.get_space_runtime(space_id)
            if not space_status:
                return False

            # Map to lifecycle state
            hf_state = space_status.get("stage", "stopped")
            target_state = self.HF_TO_LIFECYCLE_STATES.get(hf_state)

            if not target_state:
                return False

            # Get lifecycle manager
            manager = self.lifecycle_service.get_manager(agent_id)

            # Check if transition is valid and perform it
            if manager.can_transition_to(target_state):
                return await manager.transition_to(
                    target_state,
                    reason=f"HF space status: {hf_state}",
                    triggered_by="hf_sync"
                )

            return False

        except Exception as e:
            # Log error and return False
            return False

    async def sync_all_agent_spaces(self) -> Dict[UUID, bool]:
        """Sync all registered agent spaces."""
        results = {}

        for agent_id in self.agent_to_space_mapping:
            results[agent_id] = await self.sync_space_status(agent_id)

        return results
```

#### 2.2 Update HF Space Management

**Objective**: Integrate lifecycle sync with HF space operations

**Changes Required**:

```python
# devcycle/huggingface/space.py

from ..core.agents.lifecycle import AgentLifecycleService

class HuggingFaceSpace:
    def __init__(self, client: HuggingFaceClient, repo_id: str, lifecycle_service: Optional[AgentLifecycleService] = None):
        self.client = client
        self.repo_id = repo_id
        self.lifecycle_service = lifecycle_service
        self.logger = get_logger(f"huggingface.space.{repo_id}")

    async def create_space_with_lifecycle(self, config: SpaceConfig, agent_id: UUID) -> bool:
        """Create space and register with lifecycle service."""
        # Create space
        success = self.create_space(config)
        if not success:
            return False

        # Register with lifecycle service if available
        if self.lifecycle_service:
            await self.lifecycle_service.register_agent(agent_id)
            await self.lifecycle_service.deploy_agent(agent_id)

        return True

    async def get_space_status_with_lifecycle(self, agent_id: UUID) -> Dict[str, Any]:
        """Get space status with lifecycle information."""
        # Get basic space status
        status = self.get_space_status()

        # Add lifecycle information if available
        if self.lifecycle_service:
            lifecycle_status = self.lifecycle_service.get_agent_status(agent_id)
            status["lifecycle"] = lifecycle_status

        return status
```

### Phase 3: Enhanced Features

#### 3.1 Event-Driven Integration

**Objective**: Add event handlers for lifecycle state changes

**Changes Required**:

```python
# devcycle/core/services/agent_service.py

class AgentService(BaseService[Agent]):
    def __init__(self, ...):
        # ... existing initialization ...

        # Register lifecycle event handlers
        self._register_lifecycle_handlers()

    def _register_lifecycle_handlers(self) -> None:
        """Register event handlers for lifecycle state changes."""
        # Register handlers for all agents
        self.lifecycle_service.on_event("post_transition", self._on_agent_state_change)

    async def _on_agent_state_change(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle agent state change events."""
        agent_id = data.get("agent_id")
        from_state = data.get("from_state")
        to_state = data.get("to_state")

        if not agent_id:
            return

        # Update database status
        await self.agent_repository.update_agent_status(agent_id, AgentStatus(to_state.value))

        # Log state change
        self.logger.info(f"Agent {agent_id} transitioned from {from_state} to {to_state}")

        # Handle specific state transitions
        if to_state == AgentLifecycleState.ERROR:
            await self._handle_agent_error(agent_id, data.get("reason", "Unknown error"))
        elif to_state == AgentLifecycleState.OFFLINE:
            await self._handle_agent_offline(agent_id)
        elif to_state == AgentLifecycleState.ONLINE:
            await self._handle_agent_online(agent_id)

    async def _handle_agent_error(self, agent_id: UUID, error_reason: str) -> None:
        """Handle agent error state."""
        # Update error count and last error
        await self.agent_repository.update_agent_health(
            agent_id,
            error_message=error_reason
        )

        # Send notification or alert
        self.logger.error(f"Agent {agent_id} entered error state: {error_reason}")

    async def _handle_agent_offline(self, agent_id: UUID) -> None:
        """Handle agent going offline."""
        # Cancel any pending tasks
        pending_tasks = await self.task_repository.get_tasks_by_agent(agent_id)
        for task in pending_tasks:
            if task.status in ["pending", "running"]:
                await self.task_repository.update_task_status(
                    task.id, "cancelled", error="Agent went offline"
                )

    async def _handle_agent_online(self, agent_id: UUID) -> None:
        """Handle agent coming online."""
        # Agent is now available for new tasks
        self.logger.info(f"Agent {agent_id} is now online and available")
```

#### 3.2 Health Monitoring Integration

**Objective**: Integrate lifecycle states with health monitoring

**Changes Required**:

```python
# devcycle/core/services/agent_availability_service.py

from ..agents.lifecycle import AgentLifecycleService

class AgentAvailabilityService:
    def __init__(self, agent_repository: AgentRepository, lifecycle_service: Optional[AgentLifecycleService] = None):
        self.agent_repository = agent_repository
        self.lifecycle_service = lifecycle_service or AgentLifecycleService()

    async def is_agent_available(self, agent_id: UUID) -> bool:
        """Check if agent is available using lifecycle service."""
        # First check lifecycle state
        manager = self.lifecycle_service.get_manager(agent_id)
        if not manager.is_available_for_tasks():
            return False

        # Then check traditional availability criteria
        return await self._check_traditional_availability(agent_id)

    async def get_available_agents_by_capability(self, capability: str) -> List[UUID]:
        """Get available agents by capability using lifecycle service."""
        # Get agents with capability
        agents = await self.agent_repository.get_agents_by_capability(capability)

        # Filter by lifecycle availability
        available_agents = []
        for agent in agents:
            if await self.is_agent_available(agent.id):
                available_agents.append(agent.id)

        return available_agents
```

## Implementation Timeline

### Week 1: Core Integration
- [ ] Update AgentService with lifecycle integration
- [ ] Update dependency injection
- [ ] Add basic lifecycle API endpoints
- [ ] Write integration tests

### Week 2: API Enhancement
- [ ] Add comprehensive lifecycle API endpoints
- [ ] Update existing endpoints to use lifecycle
- [ ] Add lifecycle status to agent responses
- [ ] Test API integration

### Week 3: HF Integration
- [ ] Implement HF lifecycle sync
- [ ] Update HF space management
- [ ] Add HF space lifecycle endpoints
- [ ] Test HF integration

### Week 4: Advanced Features
- [ ] Implement event-driven integration
- [ ] Add health monitoring integration
- [ ] Add lifecycle metrics and monitoring
- [ ] Performance testing and optimization

## Testing Strategy

### Unit Tests
- Test lifecycle integration in AgentService
- Test API endpoint integration
- Test HF space lifecycle sync
- Test event handling

### Integration Tests
- Test complete agent lifecycle workflows
- Test HF space integration
- Test API endpoint functionality
- Test error handling and recovery

### Performance Tests
- Test lifecycle state transition performance
- Test concurrent agent operations
- Test memory usage with large numbers of agents
- Test API response times

## Migration Strategy

### Backward Compatibility
- All existing API endpoints continue to work
- Existing agent operations remain unchanged
- Database schema remains compatible
- Gradual migration of features

### Feature Flags
- Use feature flags to enable/disable lifecycle features
- Allow gradual rollout of new functionality
- Easy rollback if issues are discovered

### Data Migration
- No database migration required
- Existing agent data remains valid
- New lifecycle data is added incrementally

## Success Criteria

### Functional Requirements
- [ ] All existing agent operations work with lifecycle integration
- [ ] New lifecycle API endpoints function correctly
- [ ] HF space integration works seamlessly
- [ ] Event handling works for all state transitions
- [ ] Health monitoring integrates with lifecycle states

### Performance Requirements
- [ ] No degradation in existing API performance
- [ ] Lifecycle state transitions complete within 100ms
- [ ] System handles 1000+ concurrent agents
- [ ] Memory usage remains stable

### Quality Requirements
- [ ] 90%+ test coverage for new integration code
- [ ] All integration tests pass
- [ ] No breaking changes to existing APIs
- [ ] Comprehensive documentation

## Risk Mitigation

### Technical Risks
- **State Synchronization**: Ensure database and lifecycle states stay in sync
- **Performance Impact**: Monitor performance impact of lifecycle overhead
- **Memory Usage**: Monitor memory usage with lifecycle state history

### Mitigation Strategies
- **Comprehensive Testing**: Extensive testing of state synchronization
- **Performance Monitoring**: Continuous monitoring of performance metrics
- **Memory Management**: Implement state history limits and cleanup
- **Rollback Plan**: Feature flags allow quick rollback if needed

## Conclusion

This integration plan provides a comprehensive approach to integrating the Agent Lifecycle Management System with existing DevCycle components. The phased approach ensures minimal disruption while providing enhanced functionality and better agent management capabilities.

The integration will result in:
- **Enhanced Agent Management**: Comprehensive lifecycle management for all agents
- **Better Monitoring**: Real-time visibility into agent states and health
- **Improved Reliability**: Better error handling and recovery mechanisms
- **Seamless HF Integration**: Automatic synchronization with Hugging Face Spaces
- **Event-Driven Architecture**: Reactive system that responds to state changes
- **Backward Compatibility**: All existing functionality continues to work

This foundation will support the next phases of agent architecture development, including communication patterns, orchestration, and advanced monitoring capabilities.
