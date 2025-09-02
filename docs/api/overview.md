# API Overview

The DevCycle API provides a comprehensive RESTful interface for managing AI agents, handling inter-agent communication, and monitoring system health. Built with FastAPI, the API offers automatic OpenAPI documentation generation, robust authentication, and extensive agent lifecycle management capabilities.

## Key Features

- **Agent Management**: Complete lifecycle management from registration to deployment
- **Message Routing**: Intelligent message routing between agents with load balancing
- **Health Monitoring**: Comprehensive health checks and system monitoring
- **Authentication**: Secure JWT-based authentication with role-based access control
- **Versioning**: API versioning with backward compatibility
- **Rate Limiting**: Built-in rate limiting for security and performance
- **Interactive Documentation**: Auto-generated Swagger UI and ReDoc documentation

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

The API uses JWT-based authentication via FastAPI Users with enhanced security features.

### Authentication Endpoints
- **Login**: `POST /api/v1/auth/jwt/login`
- **Logout**: `POST /api/v1/auth/jwt/logout`
- **Current User**: `GET /api/v1/auth/me`
- **Session Management**: `GET /api/v1/auth/sessions`

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
  "request_id": "req_123456"
}
```

## Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:
- **Limit**: 10 requests per minute per IP address
- **Window**: 60 seconds
- **Response**: HTTP 429 Too Many Requests

## Security Features

### Security Headers
All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### CORS Configuration
- **Development**: Permissive CORS for local development
- **Production**: Restricted to specific origins
- **Credentials**: Configurable per environment

## API Endpoints

### Health & Monitoring
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed system health
- `GET /api/version` - API version information

### Authentication
- `POST /api/v1/auth/jwt/login` - User login
- `POST /api/v1/auth/jwt/logout` - User logout
- `GET /api/v1/auth/me` - Current user info
- `GET /api/v1/auth/sessions` - Active sessions

### Agent Management
- `GET /api/v1/agents` - List all agents
- `POST /api/v1/agents` - Create new agent
- `GET /api/v1/agents/{id}` - Get agent details
- `PUT /api/v1/agents/{id}` - Update agent
- `DELETE /api/v1/agents/{id}` - Delete agent

### Message Handling
- `POST /api/v1/messages` - Send message
- `GET /api/v1/messages` - List messages
- `GET /api/v1/messages/{id}` - Get message details

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Server Error |

## SDKs and Client Libraries

### Python Client
```python
from devcycle import DevCycleClient

client = DevCycleClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# List agents
agents = client.agents.list()

# Send message
response = client.messages.send(
    content="Hello, world!",
    recipient="agent-123"
)
```

### JavaScript/TypeScript Client
```typescript
import { DevCycleClient } from '@devcycle/client';

const client = new DevCycleClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// List agents
const agents = await client.agents.list();

// Send message
const response = await client.messages.send({
  content: 'Hello, world!',
  recipient: 'agent-123'
});
```

## Testing the API

### Using cURL
```bash
# Health check
curl -X GET "http://localhost:8000/api/v1/health"

# Login
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password"

# List agents (with token)
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Using Postman
1. Import the OpenAPI schema from `http://localhost:8000/openapi.json`
2. Set up authentication with JWT tokens
3. Test endpoints interactively

## Next Steps

- **[Authentication Guide](authentication.md)** - Detailed authentication setup and security
- **[Endpoints Reference](endpoints.md)** - Complete endpoint documentation with examples
- **[Testing Guide](testing.md)** - Comprehensive API testing guide
- **[Architecture Overview](../architecture/overview.md)** - System architecture and design
- **[Getting Started Guide](../getting-started/quick-start.md)** - Set up your development environment
