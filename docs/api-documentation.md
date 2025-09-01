# DevCycle API Documentation

## Overview

The DevCycle API provides a RESTful interface for managing AI agents, handling messages, and monitoring system health. The API is built with FastAPI and automatically generates interactive documentation.

## Accessing Documentation

### Interactive Documentation (Swagger UI)
- **URL**: `http://localhost:8000/docs`
- **Description**: Interactive API explorer where you can test endpoints directly
- **Features**:
  - Try out API calls
  - View request/response schemas
  - See example requests and responses

### Alternative Documentation (ReDoc)
- **URL**: `http://localhost:8000/redoc`
- **Description**: Clean, readable documentation format
- **Features**:
  - Better for reading and understanding
  - Organized by tags
  - Detailed schema information

### OpenAPI Schema
- **URL**: `http://localhost:8000/openapi.json`
- **Description**: Machine-readable API specification
- **Use Cases**:
  - Generate client SDKs
  - Import into API testing tools
  - Integration with other tools

## API Versioning

The API uses URL path versioning:
- **Current Version**: v1
- **Base URL**: `/api/v1/`
- **Version Info**: Available at `/api/version`

### Version Information Endpoint
```http
GET /api/version
```

Response:
```json
{
  "current_version": "v1",
  "supported_versions": ["v1", "v2"],
  "deprecated_versions": [],
  "versioning_strategy": "URL path versioning",
  "deprecation_policy": "Versions are supported for at least 12 months after deprecation"
}
```

## Authentication

The API uses JWT-based authentication via FastAPI Users.

### Authentication Endpoints
- **Login**: `POST /api/v1/auth/jwt/login`
- **Logout**: `POST /api/v1/auth/jwt/logout`
- **Current User**: `GET /api/v1/auth/me`

### Protected vs Public Endpoints

**Public Endpoints** (No authentication required):
- `/api/v1/health/*` - Health check endpoints
- `/api/v1/auth/jwt/login` - Login endpoint
- `/api/v1/auth/jwt/logout` - Logout endpoint

**Protected Endpoints** (Authentication required):
- `/api/v1/agents/*` - All agent management operations
- `/api/v1/messages/*` - All message operations
- `/api/v1/auth/me` - Current user information
- `/api/v1/auth/users/*` - User management

## Standard Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456"
}
```

### Error Response
```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "message": "Invalid request data",
  "details": {
    "field": "email",
    "issue": "Invalid email format"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456",
  "path": "/api/v1/agents"
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  },
  "message": "Data retrieved successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456"
}
```

## Health Check Endpoints

### Basic Health Check
```http
GET /api/v1/health
```

**Purpose**: Lightweight health check for load balancers and basic monitoring

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

**Purpose**: Comprehensive health check with component status and metrics

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

**Purpose**: Kubernetes readiness probe endpoint

### Liveness Check
```http
GET /api/v1/health/live
```

**Purpose**: Kubernetes liveness probe endpoint

## Agent Management

### Register Agent
```http
POST /api/v1/agents
```

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

### List Agents
```http
GET /api/v1/agents
```

**Query Parameters**:
- `agent_type`: Filter by agent type
- `status_filter`: Filter by agent status
- `capability`: Filter by capability
- `limit`: Maximum number of results (1-1000, default: 100)
- `offset`: Number of results to skip (default: 0)

### Get Agent by ID
```http
GET /api/v1/agents/{agent_id}
```

### Update Agent
```http
PUT /api/v1/agents/{agent_id}
```

### Delete Agent
```http
DELETE /api/v1/agents/{agent_id}
```

## Message Handling

### Send Message
```http
POST /api/v1/messages/send
```

**Authentication**: Required

**Request Body**:
```json
{
  "agent_id": "agent_123",
  "action": "analyze_business_requirement",
  "data": {
    "requirement": "User authentication system",
    "priority": "high"
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

### Route Message
```http
POST /api/v1/messages/route
```

## Error Handling

### HTTP Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Response Format
All errors follow a consistent format with:
- Error type/code
- Human-readable message
- Additional details (when applicable)
- Request path and timestamp

## Rate Limiting

Rate limiting is applied to authentication endpoints:
- **Limit**: 10 requests per minute per IP
- **Window**: 60 seconds
- **Response**: 429 Too Many Requests when exceeded

## Security Features

### Security Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

### CORS Configuration
Configurable CORS settings for cross-origin requests.

## Development and Testing

### Local Development
1. Start the API server: `poetry run uvicorn devcycle.api.app:app --reload`
2. Access documentation: `http://localhost:8000/docs`
3. Test endpoints using the interactive documentation

### Testing
- Unit tests: `poetry run pytest tests/unit/`
- Integration tests: `poetry run pytest tests/integration/`
- E2E tests: `poetry run pytest tests/e2e/`

## Best Practices

### Request Headers
```http
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

### Response Handling
- Always check the `success` field in responses
- Handle errors gracefully using the error response format
- Use pagination for large datasets
- Implement proper retry logic for transient errors

### Authentication
- Store JWT tokens securely
- Implement token refresh logic
- Handle authentication errors appropriately

## Support and Resources

- **Interactive Documentation**: `/docs`
- **API Schema**: `/openapi.json`
- **Version Information**: `/api/version`
- **Health Status**: `/api/v1/health`
