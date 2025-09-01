# Logging and Monitoring

This document describes the logging and monitoring strategy for the DevCycle system, designed for production environments with Kibana integration.

## Overview

The DevCycle system uses structured logging with `structlog` to provide comprehensive, searchable logs that integrate seamlessly with Kibana and other log aggregation systems.

## Logging Architecture

### Core Components

1. **Structured Logging**: All logs are structured JSON format for easy parsing and analysis
2. **Service Metadata**: Each log entry includes service information for filtering
3. **Correlation IDs**: Request tracing across services
4. **Event Types**: Categorized events for better monitoring
5. **Performance Metrics**: Built-in performance logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information about system operation
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error conditions that don't stop the system
- **CRITICAL**: Critical errors that may cause system failure

## Log Structure

### Standard Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "logger": "devcycle.api.routes.agents",
  "message": "Agent registered successfully",
  "event_type": "agent_registration",
  "service_name": "devcycle",
  "service_version": "0.1.0",
  "environment": "production",
  "hostname": "api-server-01",
  "correlation_id": "abc12345",
  "agent_id": "agent-123",
  "agent_name": "business_analyst_01",
  "agent_type": "business_analyst",
  "user_id": "user-456"
}
```

### Event Types

The system uses standardized event types for better monitoring:

#### Authentication Events
- `user_registration`: User account creation
- `user_login`: Successful authentication
- `user_logout`: User session termination
- `password_reset_request`: Password reset initiated
- `email_verification_request`: Email verification requested

#### Agent Events
- `agent_registration`: New agent registered
- `agent_started`: Agent started execution
- `agent_stopped`: Agent stopped
- `agent_error`: Agent encountered an error
- `agent_heartbeat`: Agent health check

#### Message Events
- `message_sent`: Message sent to agent
- `message_received`: Message received by agent
- `message_processed`: Message processing completed
- `message_failed`: Message processing failed

#### System Events
- `api_request`: API endpoint accessed
- `api_response`: API response sent
- `database_query`: Database operation
- `kafka_message`: Kafka message processed
- `performance_metric`: Performance measurement

## Kibana Integration

### Index Patterns

Create index patterns in Kibana for:
- `devcycle-logs-*`: All application logs
- `devcycle-metrics-*`: Performance metrics
- `devcycle-events-*`: Business events

### Recommended Dashboards

1. **System Health Dashboard**
   - Error rates by service
   - Response time percentiles
   - Active users and agents
   - System resource usage

2. **Agent Monitoring Dashboard**
   - Agent status distribution
   - Message processing rates
   - Agent error rates
   - Performance metrics

3. **Security Dashboard**
   - Authentication events
   - Failed login attempts
   - Suspicious activity
   - Access patterns

4. **Business Metrics Dashboard**
   - User activity
   - Feature usage
   - Business process completion rates
   - SLA compliance

### Kibana Queries

#### Find all errors in the last hour
```
event_type:error AND timestamp:[now-1h TO now]
```

#### Monitor agent performance
```
event_type:agent_heartbeat AND agent_type:business_analyst
```

#### Track user authentication
```
event_type:user_login AND timestamp:[now-24h TO now]
```

#### Monitor API performance
```
event_type:api_response AND response_time:>1000
```

## Configuration

### Environment Variables

```bash
# Logging level
LOG_LEVEL=INFO

# Log file path (optional)
LOG_FILE=/var/log/devcycle/app.log

# JSON output for production
JSON_OUTPUT=true

# Service metadata
SERVICE_NAME=devcycle
SERVICE_VERSION=0.1.0
ENVIRONMENT=production
```

### Logging Configuration

```python
from devcycle.core.logging import setup_logging

# Setup logging for production
setup_logging(
    level="INFO",
    log_file=Path("/var/log/devcycle/app.log"),
    json_output=True
)
```

## Best Practices

### 1. Use Structured Logging

```python
# Good: Structured logging
logger.info(
    "User authenticated",
    user_id=str(user.id),
    user_email=user.email,
    event_type="user_login",
    ip_address=request.client.host
)

# Bad: String formatting
logger.info(f"User {user.email} logged in from {request.client.host}")
```

### 2. Include Context

Always include relevant context in log entries:
- User IDs for user-related events
- Agent IDs for agent-related events
- Request IDs for API requests
- Correlation IDs for distributed tracing

### 3. Use Appropriate Log Levels

- **DEBUG**: Development and troubleshooting
- **INFO**: Normal operation events
- **WARNING**: Potential issues that don't affect functionality
- **ERROR**: Errors that affect functionality but don't stop the system
- **CRITICAL**: Errors that may cause system failure

### 4. Avoid Sensitive Data

Never log:
- Passwords or authentication tokens
- Personal identification information
- Credit card numbers or financial data
- API keys or secrets

### 5. Performance Considerations

- Use async logging where possible
- Batch log entries for high-volume scenarios
- Use appropriate log levels to reduce noise
- Consider log rotation and retention policies

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Error Rates**
   - 4xx/5xx HTTP response rates
   - Application error rates
   - Database error rates

2. **Performance Metrics**
   - Response time percentiles (p50, p95, p99)
   - Throughput (requests per second)
   - Resource utilization (CPU, memory, disk)

3. **Business Metrics**
   - User activity levels
   - Agent processing rates
   - Message queue depths
   - Feature usage statistics

### Alerting Rules

1. **Critical Alerts**
   - Error rate > 5% for 5 minutes
   - Response time p95 > 2 seconds for 10 minutes
   - System resource usage > 90% for 5 minutes

2. **Warning Alerts**
   - Error rate > 1% for 10 minutes
   - Response time p95 > 1 second for 15 minutes
   - Unusual authentication patterns

3. **Info Alerts**
   - New agent registrations
   - High message volumes
   - Feature usage milestones

## Log Retention

### Retention Policies

- **Production**: 30 days for INFO and above, 7 days for DEBUG
- **Staging**: 14 days for all levels
- **Development**: 7 days for all levels

### Archival Strategy

- Compress logs older than 7 days
- Archive logs older than 30 days to cold storage
- Delete logs older than 1 year

## Troubleshooting

### Common Issues

1. **High Log Volume**
   - Review log levels
   - Implement log sampling for DEBUG logs
   - Use structured logging to reduce redundancy

2. **Missing Logs**
   - Check log file permissions
   - Verify logging configuration
   - Monitor disk space

3. **Performance Impact**
   - Use async logging
   - Implement log batching
   - Consider log sampling for high-volume events

### Debugging Tips

1. **Use Correlation IDs** to trace requests across services
2. **Filter by Event Type** to focus on specific functionality
3. **Use Time Ranges** to narrow down issues
4. **Check Service Metadata** to identify problematic components

## Examples

### API Request Logging

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Log request
    logger.info(
        "API request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        response_time=time.time() - start_time,
        event_type="api_request",
        user_id=getattr(request.state, 'user_id', None)
    )

    return response
```

### Agent Activity Logging

```python
def log_agent_activity(agent_name: str, action: str, status: str = "started", details: Optional[Dict[str, Any]] = None):
    """Log agent activity with structured data."""
    logger.info(
        f"Agent {action}",
        agent_name=agent_name,
        action=action,
        status=status,
        event_type="agent_activity",
        **(details or {})
    )
```

### Performance Logging

```python
@log_performance("agent_processing")
async def process_agent_request(agent_id: str, request_data: Dict[str, Any]):
    """Process agent request with performance logging."""
    # Processing logic here
    pass
```

This logging and monitoring strategy ensures comprehensive observability of the DevCycle system while maintaining performance and providing actionable insights for operations teams.
