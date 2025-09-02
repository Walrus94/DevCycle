# Authentication & Authorization

The DevCycle API uses JWT-based authentication with enhanced security features including token blacklisting, session monitoring, and role-based access control.

## Authentication Overview

### JWT Token Structure

The API uses JSON Web Tokens (JWT) for authentication with the following structure:

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user_id",
    "email": "user@example.com",
    "role": "developer",
    "permissions": ["agent:read", "agent:write", "message:send"],
    "iat": 1642248000,
    "exp": 1642251600,
    "jti": "token_id"
  }
}
```

### Token Expiration

- **Access Token**: 15 minutes
- **Refresh Token**: 7 days
- **Session Token**: 24 hours

## Authentication Endpoints

### Login

```http
POST /api/v1/auth/jwt/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=your_password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Logout

```http
POST /api/v1/auth/jwt/logout
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

### Get Current User

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "username": "developer",
  "role": "developer",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Get Active Sessions

```http
GET /api/v1/auth/sessions
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_123",
      "created_at": "2024-01-15T10:30:00Z",
      "last_accessed": "2024-01-15T11:30:00Z",
      "expires_at": "2024-01-16T10:30:00Z",
      "is_current": true
    }
  ],
  "total_sessions": 1,
  "max_sessions": 5
}
```

## Authorization

### Role-Based Access Control (RBAC)

The API implements role-based access control with the following roles:

#### Developer Role
- **Permissions**:
  - `agent:read` - View agents
  - `agent:write` - Create, update, delete agents
  - `message:send` - Send messages to agents
  - `message:read` - View message history
  - `health:read` - View health status

#### Admin Role
- **Permissions**: All developer permissions plus:
  - `user:read` - View user information
  - `user:write` - Create, update, delete users
  - `system:admin` - System administration
  - `agent:admin` - Agent administration
  - `message:admin` - Message administration

#### System Role
- **Permissions**: All permissions for system operations
  - Used for internal system communication
  - Not available for regular users

### Permission Checking

The API automatically checks permissions for each endpoint:

```python
# Example permission check in endpoint
@router.get("/agents")
async def list_agents(
    user: User = Depends(current_active_user),
    required_permission: str = "agent:read"
):
    # FastAPI Users automatically validates user and permissions
    # Additional permission checks can be added here
    pass
```

## Security Features

### Token Blacklisting

The API implements token blacklisting to invalidate tokens immediately:

```http
POST /api/v1/auth/jwt/logout
Authorization: Bearer <access_token>
```

This adds the token to a blacklist, preventing its reuse even if it hasn't expired.

### Session Monitoring

The API tracks active sessions and provides session management:

- **Session Limits**: Maximum 5 concurrent sessions per user
- **Session Timeout**: 24 hours of inactivity
- **Session Invalidation**: Immediate on logout

### Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:

- **Limit**: 10 requests per minute per IP address
- **Window**: 60 seconds
- **Response**: HTTP 429 Too Many Requests when exceeded

### Security Headers

All responses include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

## Using Authentication in API Calls

### cURL Examples

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=your_password"

# Use token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Python Examples

```python
import requests

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/jwt/login",
    data={
        "username": "user@example.com",
        "password": "your_password"
    }
)

access_token = login_response.json()["access_token"]

# Use token in subsequent requests
headers = {"Authorization": f"Bearer {access_token}"}
agents_response = requests.get(
    "http://localhost:8000/api/v1/agents",
    headers=headers
)
```

### JavaScript Examples

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/jwt/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: 'username=user@example.com&password=your_password'
});

const { access_token } = await loginResponse.json();

// Use token in subsequent requests
const agentsResponse = await fetch('http://localhost:8000/api/v1/agents', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

## Error Handling

### Authentication Errors

#### 401 Unauthorized
```json
{
  "success": false,
  "detail": "Not authenticated",
  "path": "/api/v1/agents"
}
```

#### 403 Forbidden
```json
{
  "success": false,
  "detail": "Not enough permissions",
  "path": "/api/v1/agents",
  "message": "Insufficient permissions for this operation"
}
```

#### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded",
  "message": "Too many requests. Limit: 10 per 60 seconds"
}
```

### Token Expiration

When a token expires, the API returns a 401 status. The client should:

1. Attempt to refresh the token using the refresh token
2. If refresh fails, redirect to login
3. Retry the original request with the new token

## Best Practices

### Token Storage

- **Web Applications**: Store tokens in httpOnly cookies when possible
- **Mobile Applications**: Use secure storage (Keychain, Keystore)
- **Desktop Applications**: Use secure credential storage
- **Never**: Store tokens in localStorage or sessionStorage for sensitive applications

### Token Refresh

Implement automatic token refresh:

```python
class APIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None

    async def login(self):
        response = await self._post("/auth/jwt/login", {
            "username": self.username,
            "password": self.password
        })
        self.access_token = response["access_token"]
        self.refresh_token = response.get("refresh_token")

    async def _make_request(self, method, endpoint, **kwargs):
        if not self.access_token:
            await self.login()

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs["headers"] = headers

        try:
            return await self._request(method, endpoint, **kwargs)
        except HTTPException as e:
            if e.status_code == 401:
                # Token expired, try to refresh
                await self.refresh_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                return await self._request(method, endpoint, **kwargs)
            raise
```

### Error Handling

Always handle authentication errors gracefully:

```python
try:
    response = await api_client.get_agents()
except HTTPException as e:
    if e.status_code == 401:
        # Handle authentication error
        await redirect_to_login()
    elif e.status_code == 403:
        # Handle permission error
        show_permission_error()
    else:
        # Handle other errors
        show_generic_error()
```

## Next Steps

- **[Endpoints Reference](endpoints.md)** - Complete endpoint documentation
- **[API Testing Guide](testing.md)** - Testing authentication and endpoints
- **[SDK Documentation](sdk.md)** - Client library usage
- **[Security Architecture](../architecture/security.md)** - Comprehensive security design
