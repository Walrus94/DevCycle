# Security Monitoring and Audit Logging

This document describes the comprehensive security monitoring and audit logging system implemented in DevCycle API.

## Overview

The security monitoring system provides:

- **Structured Security Event Logging**: Comprehensive logging of all security-related events
- **Real-time Anomaly Detection**: Automatic detection of suspicious patterns and activities
- **Kibana Integration**: Centralized log management and visualization
- **Audit Trail API**: Administrative endpoints for security event queries
- **Alert Management**: Automated alerting for security incidents

## Architecture

### Components

1. **Security Logger** (`devcycle/core/logging/security.py`)
   - Structured logging for security events
   - Event categorization and severity levels
   - Kibana integration for log correlation

2. **Security Monitor** (`devcycle/core/monitoring/security_monitor.py`)
   - Real-time anomaly detection
   - Pattern recognition for suspicious activities
   - Alert generation and management

3. **Security Logging Middleware** (`devcycle/api/middleware/security_logging.py`)
   - Request/response logging with security context
   - User authentication tracking
   - Client information extraction

4. **Audit API Routes** (`devcycle/api/routes/audit.py`)
   - Administrative endpoints for security event queries
   - User activity tracking
   - Kibana dashboard integration

5. **Kibana Integration**
   - Dashboard configuration
   - Index patterns for security events
   - Automated setup scripts

## Security Event Types

### Authentication Events
- `auth_success`: Successful authentication
- `auth_failure`: Failed authentication attempts
- `auth_blocked`: Blocked authentication attempts
- `logout`: User logout events
- `session_expired`: Session expiration

### Authorization Events
- `access_denied`: Access denied to resources
- `admin_action`: Administrative actions
- `role_changed`: User role changes

### User Management Events
- `user_created`: New user creation
- `user_deleted`: User deletion
- `password_changed`: Password changes

### Security Events
- `rate_limit_exceeded`: Rate limiting violations
- `suspicious_activity`: Suspicious user behavior
- `security_alert`: Security alerts and notifications

### API Events
- `api_key_used`: API key usage
- `api_key_revoked`: API key revocation
- `data_access`: Data access events
- `configuration_change`: Configuration changes

## Severity Levels

- **LOW**: Informational events (successful logins, normal operations)
- **MEDIUM**: Warning events (failed logins, access denied)
- **HIGH**: Critical events (suspicious activity, multiple failures)
- **CRITICAL**: Emergency events (security alerts, system compromises)

## Configuration

### Environment Variables

```bash
# Kibana Configuration
KIBANA_ENABLED=true
KIBANA_BASE_URL=http://localhost:5601
KIBANA_INDEX_PATTERN=devcycle-security-*
KIBANA_SECURITY_DASHBOARD_ID=security-monitoring-dashboard
KIBANA_ENVIRONMENT=production

# Security Monitoring
SECURITY_MONITORING_ENABLED=true
SECURITY_ALERT_EMAIL=security@devcycle.ai
SECURITY_ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

### API Configuration

```python
# In devcycle/core/config/settings.py
class APIConfig(BaseSettings):
    kibana: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": False,
            "base_url": "http://localhost:5601",
            "index_pattern": "devcycle-security-*",
            "security_dashboard_id": "security-monitoring-dashboard",
            "environment": "development"
        }
    )
```

## Usage

### Basic Security Logging

```python
from devcycle.core.logging.security import SecurityLogger, SecurityEventType

# Initialize logger
security_logger = SecurityLogger()

# Log authentication success
security_logger.log_auth_success(
    user_id="user_123",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0"
)

# Log authentication failure
security_logger.log_auth_failure(
    email="user@example.com",
    ip_address="192.168.1.100",
    reason="Invalid credentials"
)

# Log suspicious activity
security_logger.log_suspicious_activity(
    user_id="user_123",
    ip_address="192.168.1.100",
    activity="Multiple failed login attempts"
)
```

### Security Monitoring

```python
from devcycle.core.monitoring.security_monitor import SecurityMonitor

# Initialize monitor
monitor = SecurityMonitor()

# Start monitoring
await monitor.start_monitoring()

# Record events
monitor.record_event(SecurityEventType.AUTH_SUCCESS, {
    "user_id": "user_123",
    "ip_address": "192.168.1.100"
})

# Get active alerts
alerts = monitor.get_active_alerts()

# Get monitoring statistics
stats = monitor.get_monitoring_stats()
```

### Audit API Usage

#### Get Security Events

```bash
GET /api/v1/admin/audit/security-events
Authorization: Bearer <admin_token>

# Query parameters
?event_type=auth_failure
&user_id=user_123
&ip_address=192.168.1.100
&severity=high
&start_date=2024-01-01T00:00:00Z
&end_date=2024-01-31T23:59:59Z
&limit=100
&offset=0
```

#### Get User Activity

```bash
GET /api/v1/admin/audit/user-activity/user_123
Authorization: Bearer <admin_token>

# Query parameters
?days=7
&event_type=auth_success
&limit=50
```

#### Get Security Alerts

```bash
GET /api/v1/admin/audit/security-alerts
Authorization: Bearer <admin_token>

# Query parameters
?active_only=true
&severity=high
&limit=50
```

#### Get Monitoring Statistics

```bash
GET /api/v1/admin/audit/monitoring-stats
Authorization: Bearer <admin_token>
```

#### Get Kibana Dashboard

```bash
GET /api/v1/admin/audit/kibana-dashboard
Authorization: Bearer <admin_token>

# Query parameters
?time_range=24h
&filters={"event_type":"auth_failure"}
```

## Kibana Setup

### Prerequisites

- Elasticsearch running on port 9200
- Kibana running on port 5601
- Docker and Docker Compose (for containerized setup)

### Automated Setup

```bash
# Make script executable
chmod +x scripts/setup-kibana.sh

# Run setup script
./scripts/setup-kibana.sh

# Or with custom configuration
KIBANA_URL=http://kibana:5601 \
ELASTICSEARCH_URL=http://elasticsearch:9200 \
./scripts/setup-kibana.sh
```

### Manual Setup

1. **Create Index Pattern**
   ```bash
   curl -X POST "http://localhost:5601/api/saved_objects/index-pattern" \
     -H "Content-Type: application/json" \
     -H "kbn-xsrf: true" \
     -d '{
       "attributes": {
         "title": "devcycle-security-*",
         "timeFieldName": "@timestamp"
       }
     }'
   ```

2. **Import Dashboard**
   ```bash
   curl -X POST "http://localhost:5601/api/saved_objects/_import" \
     -H "Content-Type: application/json" \
     -H "kbn-xsrf: true" \
     --data-binary @kibana/security-dashboard.json
   ```

3. **Import Index Pattern**
   ```bash
   curl -X POST "http://localhost:5601/api/saved_objects/_import" \
     -H "Content-Type: application/json" \
     -H "kbn-xsrf: true" \
     --data-binary @kibana/security-index-pattern.json
   ```

## Dashboard Features

### Security Events Timeline
- Timeline view of all security events
- Filterable by event type, severity, and time range
- Real-time updates

### Event Types Distribution
- Pie chart showing distribution of event types
- Helps identify common security patterns
- Drill-down capabilities

### Top IP Addresses
- Bar chart of IP addresses by event count
- Identifies potential attack sources
- Geographic mapping support

### Security Alerts
- Table of active security alerts
- Alert severity and status tracking
- Resolution workflow

### Security Events Table
- Detailed table of all security events
- Sortable and filterable columns
- Export capabilities

## Alerting Rules

### Authentication Failures
- **Threshold**: 5 failures in 15 minutes
- **Severity**: HIGH
- **Action**: Generate alert, block IP temporarily

### Rate Limiting Violations
- **Threshold**: 3 violations in 10 minutes
- **Severity**: MEDIUM
- **Action**: Generate alert, increase rate limit

### Suspicious Activity
- **Threshold**: 2 suspicious activities in 30 minutes
- **Severity**: HIGH
- **Action**: Generate alert, require additional authentication

### Access Denied
- **Threshold**: 10 denials in 20 minutes
- **Severity**: MEDIUM
- **Action**: Generate alert, review access patterns

## Monitoring Patterns

### Rapid Failed Logins
- Multiple failed login attempts from same IP
- Time window: 5 minutes
- Threshold: 3 attempts

### Multiple IP Addresses
- User accessing from multiple IP addresses
- Time window: 1 hour
- Threshold: 3 different IPs

### Unusual Hours
- Activity during unusual hours (2 AM - 6 AM)
- Time window: 24 hours
- Threshold: 1 occurrence

## Integration with External Systems

### Slack Notifications
```python
# Configure Slack webhook for alerts
SECURITY_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Email Notifications
```python
# Configure email for critical alerts
SECURITY_ALERT_EMAIL=security@devcycle.ai
```

### SIEM Integration
- Export logs to external SIEM systems
- Support for common log formats (CEF, LEEF)
- Real-time log streaming

## Performance Considerations

### Log Volume
- Estimated 1000-10000 events per day for medium traffic
- Log retention: 90 days for detailed logs, 1 year for summaries
- Compression enabled for storage efficiency

### Monitoring Overhead
- Minimal impact on API performance (< 1ms per request)
- Asynchronous processing for heavy operations
- Configurable sampling for high-traffic scenarios

### Storage Requirements
- Elasticsearch cluster sizing based on log volume
- Recommended: 3 nodes, 8GB RAM, 100GB storage per node
- Index lifecycle management for automatic cleanup

## Security Considerations

### Log Protection
- All security logs are encrypted at rest
- Access control for audit endpoints
- Audit trail for log access

### Data Privacy
- PII masking in logs where required
- Configurable data retention policies
- GDPR compliance features

### Access Control
- Admin-only access to audit endpoints
- Role-based access to different log levels
- API key authentication for external integrations

## Troubleshooting

### Common Issues

1. **Kibana Dashboard Not Loading**
   - Check Elasticsearch connectivity
   - Verify index pattern exists
   - Check Kibana logs for errors

2. **Security Events Not Appearing**
   - Verify middleware is enabled
   - Check log level configuration
   - Verify Elasticsearch indexing

3. **Alerts Not Generating**
   - Check monitoring thresholds
   - Verify event recording
   - Check alert configuration

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("devcycle.core.logging.security").setLevel(logging.DEBUG)
logging.getLogger("devcycle.core.monitoring.security_monitor").setLevel(logging.DEBUG)
```

### Health Checks

```bash
# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Check Kibana health
curl http://localhost:5601/api/status

# Check security monitoring
curl http://localhost:8000/api/v1/admin/audit/monitoring-stats
```

## Future Enhancements

### Planned Features
- Machine learning-based anomaly detection
- Geographic IP analysis
- User behavior analytics
- Automated incident response
- Integration with threat intelligence feeds

### Roadmap
- Q1 2024: ML-based anomaly detection
- Q2 2024: Advanced user behavior analytics
- Q3 2024: Automated incident response
- Q4 2024: Threat intelligence integration

## Support

For questions or issues with the security monitoring system:

- **Documentation**: [Security Monitoring Guide](../docs/security-monitoring.md)
- **API Reference**: [Audit API Documentation](../docs/api/audit.md)
- **Support**: security@devcycle.ai
- **Issues**: [GitHub Issues](https://github.com/devcycle/issues)
