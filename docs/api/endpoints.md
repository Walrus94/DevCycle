# API Endpoints Reference

This document provides a comprehensive reference for all DevCycle API endpoints, including request/response schemas, examples, and detailed descriptions.

## Base URL

All API endpoints are prefixed with `/api/v1/`:

- **Development**: `http://localhost:8000/api/v1/`
- **Production**: `https://api.devcycle.ai/api/v1/`

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

## Health & Monitoring

### Basic Health Check

```http
GET /api/v1/health
```

**Description**: Lightweight health check for load balancers and basic monitoring.

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "service": "DevCycle API",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Detailed Health Check

```http
GET /api/v1/health/detailed
```

**Description**: Comprehensive health check with component status and metrics.

**Authentication**: Not required

**Response**:
```json
{
  "status": "healthy",
  "service": "DevCycle API",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "healthy",
    "configuration": "healthy",
    "logging": "healthy"
  },
  "metrics": {
    "response_time_ms": 15.2,
    "uptime": "2d 5h 30m"
  }
}
```

### Readiness Check

```http
GET /api/v1/health/ready
```

**Description**: Kubernetes readiness probe endpoint.

**Authentication**: Not required

**Response**:
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "DevCycle API",
  "checks": {
    "configuration": "ready",
    "logging": "ready"
  }
}
```

### Liveness Check

```http
GET /api/v1/health/live
```

**Description**: Kubernetes liveness probe endpoint.

**Authentication**: Not required

**Response**:
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "DevCycle API"
}
```

## Agent Management

### Register Agent

```http
POST /api/v1/agents
```

**Description**: Register a new agent with the system.

**Authentication**: Required

**Request Body**:
```json
{
  "name": "business_analyst_01",
  "type": "business_analyst",
  "description": "AI agent for business requirement analysis",
  "version": "1.0.0",
  "capabilities": ["analyze_requirements", "generate_documentation"],
  "configuration": {
    "max_concurrent_tasks": 5,
    "timeout_seconds": 300
  }
}
```

**Response** (201 Created):
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "type": "business_analyst",
  "status": "registered",
  "description": "AI agent for business requirement analysis",
  "version": "1.0.0",
  "capabilities": ["analyze_requirements", "generate_documentation"],
  "configuration": {
    "max_concurrent_tasks": 5,
    "timeout_seconds": 300
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_heartbeat": null
}
```

### List Agents

```http
GET /api/v1/agents
```

**Description**: List all agents with optional filtering and pagination.

**Authentication**: Required

**Query Parameters**:
- `agent_type` (optional): Filter by agent type
- `status_filter` (optional): Filter by agent status
- `capability` (optional): Filter by capability
- `limit` (optional): Maximum number of results (1-1000, default: 100)
- `offset` (optional): Number of results to skip (default: 0)

**Example**:
```http
GET /api/v1/agents?agent_type=business_analyst&limit=50&offset=0
```

**Response**:
```json
[
  {
    "id": "agent_123",
    "name": "business_analyst_01",
    "type": "business_analyst",
    "status": "online",
    "description": "AI agent for business requirement analysis",
    "version": "1.0.0",
    "capabilities": ["analyze_requirements", "generate_documentation"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "last_heartbeat": "2024-01-15T11:30:00Z"
  }
]
```

### Get Agent by ID

```http
GET /api/v1/agents/{agent_id}
```

**Description**: Get detailed information about a specific agent.

**Authentication**: Required

**Path Parameters**:
- `agent_id`: UUID of the agent

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "type": "business_analyst",
  "status": "online",
  "description": "AI agent for business requirement analysis",
  "version": "1.0.0",
  "capabilities": ["analyze_requirements", "generate_documentation"],
  "configuration": {
    "max_concurrent_tasks": 5,
    "timeout_seconds": 300
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_heartbeat": "2024-01-15T11:30:00Z"
}
```

### Update Agent

```http
PUT /api/v1/agents/{agent_id}
```

**Description**: Update agent information.

**Authentication**: Required

**Request Body**:
```json
{
  "description": "Updated description",
  "version": "1.1.0",
  "capabilities": ["analyze_requirements", "generate_documentation", "validate_requirements"],
  "configuration": {
    "max_concurrent_tasks": 10,
    "timeout_seconds": 600
  }
}
```

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "type": "business_analyst",
  "status": "online",
  "description": "Updated description",
  "version": "1.1.0",
  "capabilities": ["analyze_requirements", "generate_documentation", "validate_requirements"],
  "configuration": {
    "max_concurrent_tasks": 10,
    "timeout_seconds": 600
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z",
  "last_heartbeat": "2024-01-15T11:30:00Z"
}
```

### Delete Agent

```http
DELETE /api/v1/agents/{agent_id}
```

**Description**: Permanently remove an agent from the system.

**Authentication**: Required

**Response**: 204 No Content

### Get Online Agents

```http
GET /api/v1/agents/online
```

**Description**: Get all agents that are currently online and available.

**Authentication**: Required

**Response**:
```json
[
  {
    "id": "agent_123",
    "name": "business_analyst_01",
    "type": "business_analyst",
    "status": "online",
    "last_heartbeat": "2024-01-15T11:30:00Z"
  }
]
```

### Search Agents

```http
GET /api/v1/agents/search
```

**Description**: Search agents by query and filters.

**Authentication**: Required

**Query Parameters**:
- `query` (required): Search query (minimum 1 character)
- `agent_type` (optional): Filter by agent type
- `status_filter` (optional): Filter by agent status
- `limit` (optional): Maximum number of results (1-100, default: 50)

**Example**:
```http
GET /api/v1/agents/search?query=business&agent_type=business_analyst&limit=10
```

### Get Agent Types

```http
GET /api/v1/agents/types
```

**Description**: Get all available agent types.

**Authentication**: Not required

**Response**:
```json
[
  "business_analyst",
  "code_generator",
  "test_engineer",
  "deployment_engineer"
]
```

### Get Agent Capabilities

```http
GET /api/v1/agents/capabilities
```

**Description**: Get all available agent capabilities.

**Authentication**: Not required

**Response**:
```json
[
  "analyze_requirements",
  "generate_documentation",
  "validate_requirements",
  "generate_code",
  "run_tests",
  "deploy_application"
]
```

### Send Agent Heartbeat

```http
POST /api/v1/agents/{agent_id}/heartbeat
```

**Description**: Send heartbeat to update agent status.

**Authentication**: Required

**Request Body**:
```json
{
  "status": "online",
  "current_tasks": 2,
  "max_tasks": 5,
  "health_metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "response_time_ms": 120
  }
}
```

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "status": "online",
  "last_heartbeat": "2024-01-15T11:30:00Z",
  "health_metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "response_time_ms": 120
  }
}
```

## Message Handling

### Send Message

```http
POST /api/v1/messages/send
```

**Description**: Send a message to a specific agent.

**Authentication**: Required

**Request Body**:
```json
{
  "agent_id": "agent_123",
  "action": "analyze_business_requirement",
  "data": {
    "requirement": "User authentication system",
    "priority": "high",
    "deadline": "2024-01-20T10:00:00Z"
  },
  "priority": "normal",
  "ttl": 3600,
  "metadata": {
    "source": "api",
    "user_id": "user_456"
  }
}
```

**Response** (201 Created):
```json
{
  "message_id": "msg_789",
  "agent_id": "agent_123",
  "action": "analyze_business_requirement",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "data": {
    "requirement": "User authentication system",
    "priority": "high",
    "deadline": "2024-01-20T10:00:00Z"
  },
  "priority": "normal",
  "ttl": 3600,
  "metadata": {
    "source": "api",
    "user_id": "user_456"
  }
}
```

### Broadcast Message

```http
POST /api/v1/messages/broadcast
```

**Description**: Send the same message to multiple agents.

**Authentication**: Required

**Request Body**:
```json
{
  "agent_types": ["business_analyst", "code_generator"],
  "exclude_agents": ["agent_456"],
  "action": "system_maintenance_notice",
  "data": {
    "message": "System maintenance scheduled for 2 hours",
    "start_time": "2024-01-16T02:00:00Z"
  },
  "priority": "high"
}
```

**Response** (201 Created):
```json
{
  "broadcast_id": "broadcast_123",
  "total_agents": 5,
  "successful_sends": 4,
  "failed_sends": 1,
  "skipped_agents": 0,
  "message_ids": ["msg_789", "msg_790", "msg_791", "msg_792"],
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Route Message

```http
POST /api/v1/messages/route
```

**Description**: Automatically route a message to the best available agent.

**Authentication**: Required

**Request Body**:
```json
{
  "capabilities": ["analyze_requirements"],
  "action": "analyze_business_requirement",
  "data": {
    "requirement": "User authentication system"
  },
  "load_balancing": "least_busy",
  "priority": "normal"
}
```

**Response** (201 Created):
```json
{
  "message_id": "msg_793",
  "selected_agent_id": "agent_123",
  "routing_strategy": "least_busy",
  "available_agents": 3,
  "agent_capabilities": ["analyze_requirements", "generate_documentation"],
  "agent_load": {
    "current_tasks": 2,
    "max_tasks": 5,
    "status": "online"
  },
  "routing_reason": "Agent selected based on capabilities and load balancing",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Message History

```http
GET /api/v1/messages/history
```

**Description**: Get message history with optional filtering.

**Authentication**: Required

**Query Parameters**:
- `agent_id` (optional): Filter by agent ID
- `message_type` (optional): Filter by message type
- `status` (optional): Filter by message status
- `limit` (optional): Maximum number of messages (1-1000, default: 100)
- `offset` (optional): Number of messages to skip (default: 0)

**Response**:
```json
[
  {
    "message_id": "msg_789",
    "agent_id": "agent_123",
    "action": "analyze_business_requirement",
    "message_type": "command",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:32:00Z",
    "execution_time_ms": 120000,
    "data_size_bytes": 1024,
    "priority": "normal"
  }
]
```

### Get Message Detail

```http
GET /api/v1/messages/{message_id}
```

**Description**: Get detailed information about a specific message.

**Authentication**: Required

**Response**:
```json
{
  "message_id": "msg_789",
  "agent_id": "agent_123",
  "action": "analyze_business_requirement",
  "message_type": "command",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:00Z",
  "completed_at": "2024-01-15T10:32:00Z",
  "execution_time_ms": 120000,
  "data": {
    "requirement": "User authentication system",
    "priority": "high"
  },
  "data_size_bytes": 1024,
  "priority": "normal",
  "ttl": 3600,
  "metadata": {
    "source": "api",
    "user_id": "user_456"
  },
  "retry_count": 0,
  "max_retries": 3,
  "queue_position": null,
  "processing_started_at": "2024-01-15T10:30:15Z"
}
```

### Get Queue Status

```http
GET /api/v1/messages/queue/status
```

**Description**: Get current message queue status and statistics.

**Authentication**: Required

**Response**:
```json
{
  "queue_name": "default",
  "total_messages": 150,
  "pending_messages": 25,
  "processing_messages": 5,
  "completed_messages": 100,
  "failed_messages": 10,
  "retry_messages": 10,
  "average_processing_time_ms": 1200,
  "queue_health": "healthy",
  "last_activity": "2024-01-15T11:30:00Z",
  "metrics": {
    "throughput_messages_per_minute": 45,
    "error_rate_percent": 6.7,
    "average_queue_depth": 30
  }
}
```

### Retry Message

```http
POST /api/v1/messages/queue/retry/{message_id}
```

**Description**: Retry a failed message.

**Authentication**: Required

**Response**:
```json
{
  "message_id": "msg_789",
  "retry_attempt": 1,
  "max_retries": 3,
  "retry_delay_seconds": 30,
  "original_error": "Connection timeout",
  "retry_reason": "Message failed due to network issues",
  "scheduled_at": "2024-01-15T11:35:00Z",
  "status": "retrying"
}
```

### Cancel Message

```http
DELETE /api/v1/messages/queue/{message_id}
```

**Description**: Cancel a pending message.

**Authentication**: Required

**Response**:
```json
{
  "message_id": "msg_789",
  "cancelled": true,
  "previous_status": "pending",
  "cancellation_reason": "User requested cancellation",
  "cancelled_at": "2024-01-15T11:30:00Z"
}
```

## Agent Lifecycle Management

### Get Agent Lifecycle Status

```http
GET /api/v1/agents/{agent_id}/lifecycle
```

**Description**: Get detailed lifecycle information for an agent.

**Authentication**: Required

**Response**:
```json
{
  "agent_id": "agent_123",
  "current_state": "online",
  "state_history": [
    {
      "state": "registered",
      "timestamp": "2024-01-15T10:30:00Z",
      "reason": "Agent registered"
    },
    {
      "state": "deployed",
      "timestamp": "2024-01-15T10:35:00Z",
      "reason": "Agent deployed"
    },
    {
      "state": "online",
      "timestamp": "2024-01-15T10:40:00Z",
      "reason": "Agent started"
    }
  ],
  "next_available_transitions": ["maintenance", "offline"],
  "lifecycle_health": "healthy"
}
```

### Start Agent

```http
POST /api/v1/agents/{agent_id}/lifecycle/start
```

**Description**: Start an agent through lifecycle management.

**Authentication**: Required

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "status": "online",
  "lifecycle_state": "online",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

### Stop Agent

```http
POST /api/v1/agents/{agent_id}/lifecycle/stop
```

**Description**: Stop an agent through lifecycle management.

**Authentication**: Required

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "status": "offline",
  "lifecycle_state": "offline",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

### Deploy Agent

```http
POST /api/v1/agents/{agent_id}/lifecycle/deploy
```

**Description**: Deploy an agent through lifecycle management.

**Authentication**: Required

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "status": "deployed",
  "lifecycle_state": "deployed",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

### Put Agent in Maintenance

```http
POST /api/v1/agents/{agent_id}/lifecycle/maintenance
```

**Description**: Put an agent in maintenance mode.

**Authentication**: Required

**Request Body**:
```json
{
  "reason": "Scheduled maintenance"
}
```

**Response**:
```json
{
  "id": "agent_123",
  "name": "business_analyst_01",
  "status": "maintenance",
  "lifecycle_state": "maintenance",
  "maintenance_reason": "Scheduled maintenance",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "path": "/api/v1/agents"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "detail": "Not authenticated",
  "path": "/api/v1/agents",
  "message": "Authentication failed"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions",
  "path": "/api/v1/agents"
}
```

### 404 Not Found
```json
{
  "detail": "Agent not found",
  "path": "/api/v1/agents/agent_123"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email format",
      "type": "value_error.email"
    }
  ],
  "path": "/api/v1/agents"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded",
  "message": "Too many requests. Limit: 10 per 60 seconds"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "path": "/api/v1/agents"
}
```

## Next Steps

- **[Authentication Guide](authentication.md)** - Detailed authentication setup
- **[API Testing Guide](testing.md)** - Testing endpoints and authentication
- **[SDK Documentation](sdk.md)** - Client library usage
- **[API Overview](overview.md)** - Return to API overview
