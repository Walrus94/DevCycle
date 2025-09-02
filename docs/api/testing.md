# API Testing Guide

This guide provides comprehensive instructions for testing the DevCycle API, including authentication, endpoint testing, and best practices.

## Testing Environment Setup

### Prerequisites

- **API Server**: Running DevCycle API server
- **Testing Tools**: Choose from cURL, Postman, pytest, or custom scripts
- **Authentication**: Valid user credentials

### Environment URLs

- **Development**: `http://localhost:8000`
- **Testing**: `http://localhost:8000` (with test database)
- **Staging**: `https://staging-api.devcycle.ai`
- **Production**: `https://api.devcycle.ai`

## Authentication Testing

### 1. Login Test

Test the authentication endpoint to obtain a JWT token:

```bash
# cURL
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword" \
  -v
```

**Expected Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 2. Token Validation Test

Test that the token works for authenticated endpoints:

```bash
# Store token in variable
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Test authenticated endpoint
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response** (200 OK):
```json
{
  "id": "user_123",
  "email": "test@example.com",
  "username": "testuser",
  "role": "developer",
  "is_active": true
}
```

### 3. Invalid Token Test

Test error handling with invalid tokens:

```bash
# Test with invalid token
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer invalid_token" \
  -v
```

**Expected Response** (401 Unauthorized):
```json
{
  "success": false,
  "detail": "Not authenticated",
  "path": "/api/v1/auth/me",
  "message": "Authentication failed"
}
```

### 4. Rate Limiting Test

Test rate limiting on authentication endpoints:

```bash
# Make multiple rapid requests
for i in {1..15}; do
  curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=wrongpassword" \
    -w "Status: %{http_code}\n"
done
```

**Expected**: After 10 requests, should return 429 Too Many Requests.

## Health Check Testing

### 1. Basic Health Check

```bash
curl -X GET "http://localhost:8000/api/v1/health" \
  -v
```

**Expected Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "DevCycle API",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Detailed Health Check

```bash
curl -X GET "http://localhost:8000/api/v1/health/detailed" \
  -v
```

**Expected Response** (200 OK):
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

### 3. Readiness Check

```bash
curl -X GET "http://localhost:8000/api/v1/health/ready" \
  -v
```

### 4. Liveness Check

```bash
curl -X GET "http://localhost:8000/api/v1/health/live" \
  -v
```

## Agent Management Testing

### 1. Register Agent

```bash
TOKEN="your_jwt_token_here"

curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_agent_01",
    "type": "business_analyst",
    "description": "Test agent for API testing",
    "version": "1.0.0",
    "capabilities": ["analyze_requirements"],
    "configuration": {
      "max_concurrent_tasks": 3,
      "timeout_seconds": 300
    }
  }' \
  -v
```

**Expected Response** (201 Created):
```json
{
  "id": "agent_123",
  "name": "test_agent_01",
  "type": "business_analyst",
  "status": "registered",
  "description": "Test agent for API testing",
  "version": "1.0.0",
  "capabilities": ["analyze_requirements"],
  "configuration": {
    "max_concurrent_tasks": 3,
    "timeout_seconds": 300
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_heartbeat": null
}
```

### 2. List Agents

```bash
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

### 3. Get Agent by ID

```bash
AGENT_ID="agent_123"

curl -X GET "http://localhost:8000/api/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

### 4. Update Agent

```bash
curl -X PUT "http://localhost:8000/api/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated test agent description",
    "version": "1.1.0",
    "capabilities": ["analyze_requirements", "generate_documentation"]
  }' \
  -v
```

### 5. Send Heartbeat

```bash
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/heartbeat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "online",
    "current_tasks": 1,
    "max_tasks": 3,
    "health_metrics": {
      "cpu_usage": 25.5,
      "memory_usage": 45.2,
      "response_time_ms": 100
    }
  }' \
  -v
```

### 6. Delete Agent

```bash
curl -X DELETE "http://localhost:8000/api/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

**Expected Response**: 204 No Content

## Message Handling Testing

### 1. Send Message

```bash
curl -X POST "http://localhost:8000/api/v1/messages/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_123",
    "action": "analyze_business_requirement",
    "data": {
      "requirement": "User authentication system",
      "priority": "high"
    },
    "priority": "normal",
    "ttl": 3600,
    "metadata": {
      "source": "api_test",
      "test_id": "test_001"
    }
  }' \
  -v
```

### 2. Broadcast Message

```bash
curl -X POST "http://localhost:8000/api/v1/messages/broadcast" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_types": ["business_analyst"],
    "action": "test_broadcast",
    "data": {
      "message": "This is a test broadcast message"
    },
    "priority": "normal"
  }' \
  -v
```

### 3. Route Message

```bash
curl -X POST "http://localhost:8000/api/v1/messages/route" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": ["analyze_requirements"],
    "action": "analyze_business_requirement",
    "data": {
      "requirement": "User authentication system"
    },
    "load_balancing": "least_busy",
    "priority": "normal"
  }' \
  -v
```

### 4. Get Message History

```bash
curl -X GET "http://localhost:8000/api/v1/messages/history?limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

### 5. Get Queue Status

```bash
curl -X GET "http://localhost:8000/api/v1/messages/queue/status" \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

## Python Testing with pytest

### Test Setup

Create a test file `test_api.py`:

```python
import pytest
import requests
from typing import Dict, Any

class TestDevCycleAPI:
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v1"
        self.token = None
        self.agent_id = None

    def setup_method(self):
        """Setup for each test method."""
        self.login()
        self.create_test_agent()

    def teardown_method(self):
        """Cleanup after each test method."""
        if self.agent_id:
            self.delete_agent(self.agent_id)

    def login(self) -> str:
        """Login and get authentication token."""
        response = requests.post(
            f"{self.base_url}/auth/jwt/login",
            data={
                "username": "test@example.com",
                "password": "testpassword"
            }
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        return self.token

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        return {"Authorization": f"Bearer {self.token}"}

    def create_test_agent(self) -> str:
        """Create a test agent."""
        response = requests.post(
            f"{self.base_url}/agents",
            headers=self.get_headers(),
            json={
                "name": "test_agent_pytest",
                "type": "business_analyst",
                "description": "Test agent for pytest",
                "version": "1.0.0",
                "capabilities": ["analyze_requirements"],
                "configuration": {
                    "max_concurrent_tasks": 3,
                    "timeout_seconds": 300
                }
            }
        )
        assert response.status_code == 201
        self.agent_id = response.json()["id"]
        return self.agent_id

    def delete_agent(self, agent_id: str):
        """Delete a test agent."""
        response = requests.delete(
            f"{self.base_url}/agents/{agent_id}",
            headers=self.get_headers()
        )
        assert response.status_code == 204

    def test_health_check(self):
        """Test basic health check endpoint."""
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "DevCycle API"

    def test_authentication(self):
        """Test authentication flow."""
        # Test login
        response = requests.post(
            f"{self.base_url}/auth/jwt/login",
            data={
                "username": "test@example.com",
                "password": "testpassword"
            }
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        assert token is not None

        # Test authenticated endpoint
        response = requests.get(
            f"{self.base_url}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == "test@example.com"

    def test_agent_crud(self):
        """Test agent CRUD operations."""
        # Test list agents
        response = requests.get(
            f"{self.base_url}/agents",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)

        # Test get agent by ID
        response = requests.get(
            f"{self.base_url}/agents/{self.agent_id}",
            headers=self.get_headers()
        )
        assert response.status_code == 200
        agent = response.json()
        assert agent["id"] == self.agent_id
        assert agent["name"] == "test_agent_pytest"

        # Test update agent
        response = requests.put(
            f"{self.base_url}/agents/{self.agent_id}",
            headers=self.get_headers(),
            json={
                "description": "Updated test agent description",
                "version": "1.1.0"
            }
        )
        assert response.status_code == 200
        updated_agent = response.json()
        assert updated_agent["description"] == "Updated test agent description"
        assert updated_agent["version"] == "1.1.0"

    def test_message_sending(self):
        """Test message sending functionality."""
        response = requests.post(
            f"{self.base_url}/messages/send",
            headers=self.get_headers(),
            json={
                "agent_id": self.agent_id,
                "action": "test_action",
                "data": {"test": "data"},
                "priority": "normal"
            }
        )
        assert response.status_code == 201
        message = response.json()
        assert message["agent_id"] == self.agent_id
        assert message["action"] == "test_action"
        assert message["status"] == "pending"

    def test_error_handling(self):
        """Test error handling."""
        # Test 404 for non-existent agent
        response = requests.get(
            f"{self.base_url}/agents/non-existent-id",
            headers=self.get_headers()
        )
        assert response.status_code == 404

        # Test 401 for missing authentication
        response = requests.get(f"{self.base_url}/agents")
        assert response.status_code == 401

        # Test 422 for validation error
        response = requests.post(
            f"{self.base_url}/agents",
            headers=self.get_headers(),
            json={
                "name": "",  # Invalid empty name
                "type": "invalid_type"  # Invalid type
            }
        )
        assert response.status_code == 422

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Running Python Tests

```bash
# Install pytest
pip install pytest requests

# Run tests
pytest test_api.py -v

# Run with coverage
pytest test_api.py --cov=devcycle.api -v
```

## Postman Testing

### 1. Import OpenAPI Schema

1. Open Postman
2. Click "Import"
3. Enter URL: `http://localhost:8000/openapi.json`
4. Click "Import"

### 2. Set Up Environment

Create a new environment with variables:

```json
{
  "base_url": "http://localhost:8000/api/v1",
  "token": "",
  "agent_id": ""
}
```

### 3. Authentication Setup

Create a pre-request script for the login endpoint:

```javascript
// Set environment variable for token
pm.test("Login successful", function () {
    var jsonData = pm.response.json();
    pm.environment.set("token", jsonData.access_token);
});
```

### 4. Test Collection Structure

Organize tests in collections:

- **Authentication**
  - Login
  - Get Current User
  - Logout
- **Health Checks**
  - Basic Health
  - Detailed Health
  - Readiness
  - Liveness
- **Agent Management**
  - Register Agent
  - List Agents
  - Get Agent
  - Update Agent
  - Delete Agent
- **Message Handling**
  - Send Message
  - Broadcast Message
  - Route Message
  - Get History

### 5. Automated Testing

Set up Postman tests with assertions:

```javascript
// Test response status
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Test response structure
pm.test("Response has required fields", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
    pm.expect(jsonData).to.have.property('name');
    pm.expect(jsonData).to.have.property('status');
});

// Test response time
pm.test("Response time is less than 1000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(1000);
});
```

## Load Testing

### Using Apache Bench (ab)

```bash
# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/api/v1/health

# Test authenticated endpoint (with token)
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" \
   http://localhost:8000/api/v1/agents
```

### Using wrk

```bash
# Install wrk
# Ubuntu/Debian: sudo apt install wrk
# macOS: brew install wrk

# Test health endpoint
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/health

# Test with Lua script for authenticated requests
wrk -t12 -c400 -d30s -s auth_test.lua http://localhost:8000/api/v1/agents
```

Create `auth_test.lua`:

```lua
-- Get token first
local token = "your_jwt_token_here"

wrk.method = "GET"
wrk.headers["Authorization"] = "Bearer " .. token
```

## Security Testing

### 1. SQL Injection Testing

```bash
# Test with SQL injection attempts
curl -X GET "http://localhost:8000/api/v1/agents?name='; DROP TABLE agents; --" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. XSS Testing

```bash
# Test with XSS payload
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<script>alert(\"XSS\")</script>",
    "type": "business_analyst",
    "description": "Test agent"
  }'
```

### 3. CSRF Testing

```bash
# Test CSRF protection
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Origin: http://malicious-site.com" \
  -d '{
    "name": "malicious_agent",
    "type": "business_analyst",
    "description": "CSRF test"
  }'
```

## Best Practices

### 1. Test Data Management

- Use unique test data for each test run
- Clean up test data after tests
- Use test-specific prefixes for resources

### 2. Error Testing

- Test all error scenarios (400, 401, 403, 404, 422, 429, 500)
- Verify error response formats
- Test edge cases and boundary conditions

### 3. Performance Testing

- Test response times under normal load
- Test rate limiting behavior
- Monitor memory and CPU usage during tests

### 4. Security Testing

- Test authentication and authorization
- Test input validation
- Test security headers
- Test rate limiting

### 5. Documentation

- Document test scenarios
- Keep test data up to date
- Maintain test environment configurations

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check token expiration
   - Verify credentials
   - Check rate limiting

2. **Connection Issues**
   - Verify server is running
   - Check network connectivity
   - Verify URL and port

3. **Validation Errors**
   - Check request format
   - Verify required fields
   - Check data types

4. **Performance Issues**
   - Check server resources
   - Monitor response times
   - Check for bottlenecks

### Debug Tips

1. Use verbose output (`-v` flag with cURL)
2. Check server logs
3. Use Postman console for debugging
4. Enable debug logging in tests

## Next Steps

- **[Authentication Guide](authentication.md)** - Detailed authentication setup
- **[Endpoints Reference](endpoints.md)** - Complete endpoint documentation
- **[API Overview](overview.md)** - Return to API overview
- **[Development Guidelines](../development/guidelines.md)** - Development practices
