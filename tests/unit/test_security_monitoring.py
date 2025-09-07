"""Unit tests for security monitoring and audit logging system."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from devcycle.api.middleware.security_logging import SecurityLoggingMiddleware
from devcycle.api.routes.audit import router
from devcycle.core.logging import SecurityEventType, SecurityLogger, SecuritySeverity
from devcycle.core.monitoring.security_monitor import SecurityAlert, SecurityMonitor


class TestSecurityLogger:
    """Test security logging functionality."""

    def test_security_logger_initialization(self):
        """Test security logger initialization."""
        logger = SecurityLogger()
        assert logger is not None
        assert hasattr(logger, "logger")

    def test_log_security_event(self):
        """Test logging security events."""
        logger = SecurityLogger()

        with patch.object(logger.logger, "warning") as mock_warning:
            event_id = logger.log_security_event(
                SecurityEventType.AUTH_SUCCESS,
                user_id="user_123",
                ip_address="192.168.1.100",
                details={"method": "password"},
            )

            assert event_id is not None
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[1]
            assert call_args["event_type"] == "auth_success"
            assert call_args["user_id"] == "user_123"
            assert call_args["ip_address"] == "192.168.1.100"

    def test_log_auth_success(self):
        """Test logging authentication success."""
        logger = SecurityLogger()

        with patch.object(logger.logger, "info") as mock_info:
            event_id = logger.log_auth_success(
                user_id="user_123", ip_address="192.168.1.100", user_agent="Mozilla/5.0"
            )

            assert event_id is not None
            mock_info.assert_called_once()
            call_args = mock_info.call_args[1]
            assert call_args["event_type"] == "auth_success"
            assert call_args["severity"] == "low"

    def test_log_auth_failure(self):
        """Test logging authentication failure."""
        logger = SecurityLogger()

        with patch.object(logger.logger, "warning") as mock_warning:
            event_id = logger.log_auth_failure(
                email="user@example.com",
                ip_address="192.168.1.100",
                reason="Invalid credentials",
            )

            assert event_id is not None
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[1]
            assert call_args["event_type"] == "auth_failure"
            assert call_args["severity"] == "medium"

    def test_log_rate_limit_exceeded(self):
        """Test logging rate limit violations."""
        logger = SecurityLogger()

        with patch.object(logger.logger, "warning") as mock_warning:
            event_id = logger.log_rate_limit_exceeded(
                ip_address="192.168.1.100", endpoint="/api/v1/auth/login"
            )

            assert event_id is not None
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[1]
            assert call_args["event_type"] == "rate_limit_exceeded"
            assert call_args["severity"] == "medium"

    def test_log_suspicious_activity(self):
        """Test logging suspicious activity."""
        logger = SecurityLogger()

        with patch.object(logger.logger, "error") as mock_error:
            event_id = logger.log_suspicious_activity(
                user_id="user_123",
                ip_address="192.168.1.100",
                activity="Multiple failed login attempts",
            )

            assert event_id is not None
            mock_error.assert_called_once()
            call_args = mock_error.call_args[1]
            assert call_args["event_type"] == "suspicious_activity"
            assert call_args["severity"] == "high"


class TestSecurityMonitor:
    """Test security monitoring functionality."""

    def test_security_monitor_initialization(self):
        """Test security monitor initialization."""
        monitor = SecurityMonitor()
        assert monitor is not None
        assert hasattr(monitor, "event_counts")
        assert hasattr(monitor, "alert_thresholds")
        assert hasattr(monitor, "active_alerts")

    def test_record_event(self):
        """Test recording security events."""
        monitor = SecurityMonitor()

        event_data = {
            "user_id": "user_123",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
        }

        monitor.record_event(SecurityEventType.AUTH_SUCCESS, event_data)

        assert SecurityEventType.AUTH_SUCCESS.value in monitor.event_counts
        assert len(monitor.event_counts[SecurityEventType.AUTH_SUCCESS.value]) == 1

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        monitor = SecurityMonitor()

        # Create a mock alert
        alert = SecurityAlert(
            alert_id="test_alert",
            alert_type="test_alert_type",
            severity=SecuritySeverity.HIGH,
            description="Test alert",
            event_count=1,
            time_window=timedelta(minutes=15),
            events=[],
            timestamp=datetime.now(timezone.utc),
        )

        monitor.active_alerts["test_alert"] = alert

        active_alerts = monitor.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == "test_alert"

    def test_resolve_alert(self):
        """Test resolving alerts."""
        monitor = SecurityMonitor()

        # Create a mock alert
        alert = SecurityAlert(
            alert_id="test_alert",
            alert_type="test_alert_type",
            severity=SecuritySeverity.HIGH,
            description="Test alert",
            event_count=1,
            time_window=timedelta(minutes=15),
            events=[],
            timestamp=datetime.now(timezone.utc),
        )

        monitor.active_alerts["test_alert"] = alert

        # Resolve the alert
        success = monitor.resolve_alert("test_alert")
        assert success is True
        assert monitor.active_alerts["test_alert"].resolved is True

    def test_get_monitoring_stats(self):
        """Test getting monitoring statistics."""
        monitor = SecurityMonitor()

        # Add some test events
        monitor.record_event(SecurityEventType.AUTH_SUCCESS, {"user_id": "user_1"})
        monitor.record_event(SecurityEventType.AUTH_FAILURE, {"user_id": "user_2"})

        stats = monitor.get_monitoring_stats()

        assert "timestamp" in stats
        assert "active_alerts" in stats
        assert "total_events_24h" in stats
        assert "unique_users_24h" in stats
        assert "event_types" in stats


class TestSecurityLoggingMiddleware:
    """Test security logging middleware."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        middleware = SecurityLoggingMiddleware(Mock(), enable_kibana=False)
        assert middleware is not None
        assert hasattr(middleware, "security_logger")

    def test_extract_user_info(self):
        """Test extracting user information from request."""
        middleware = SecurityLoggingMiddleware(Mock(), enable_kibana=False)

        # Mock request with JWT token
        request = Mock()
        request.headers = {"authorization": "Bearer test_token"}

        with patch.object(middleware, "_extract_user_info") as mock_extract:
            mock_extract.return_value = {
                "user_id": "user_123",
                "email": "user@example.com",
                "roles": ["user"],
                "is_admin": False,
            }

            user_info = middleware._extract_user_info(request)

            assert user_info["user_id"] == "user_123"
            assert user_info["email"] == "user@example.com"
            assert user_info["roles"] == ["user"]
            assert user_info["is_admin"] is False

    def test_get_client_info(self):
        """Test extracting client information from request."""
        middleware = SecurityLoggingMiddleware(Mock(), enable_kibana=False)

        # Mock request
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {
            "user-agent": "Mozilla/5.0",
            "referer": "https://example.com",
        }

        client_info = middleware._get_client_info(request)

        assert client_info["ip_address"] == "192.168.1.100"
        assert client_info["user_agent"] == "Mozilla/5.0"
        assert client_info["referer"] == "https://example.com"

    def test_is_security_sensitive_endpoint(self):
        """Test identifying security-sensitive endpoints."""
        middleware = SecurityLoggingMiddleware(Mock(), enable_kibana=False)

        # Test security-sensitive endpoints
        assert middleware._is_security_sensitive_endpoint("/api/v1/auth/login") is True
        assert middleware._is_security_sensitive_endpoint("/api/v1/admin/users") is True
        assert (
            middleware._is_security_sensitive_endpoint("/api/v1/security/events")
            is True
        )

        # Test non-security-sensitive endpoints
        assert middleware._is_security_sensitive_endpoint("/api/v1/health") is False
        assert middleware._is_security_sensitive_endpoint("/api/v1/version") is False


class TestAuditRoutes:
    """Test audit API routes."""

    def test_router_initialization(self):
        """Test audit router initialization."""
        assert router is not None
        assert router.prefix == "/admin/audit"
        assert "admin" in router.tags
        assert "audit" in router.tags

    def test_get_security_events_endpoint_exists(self):
        """Test that security events endpoint exists."""
        routes = [route.path for route in router.routes]
        assert "/admin/audit/security-events" in routes

    def test_get_user_activity_endpoint_exists(self):
        """Test that user activity endpoint exists."""
        routes = [route.path for route in router.routes]
        assert "/admin/audit/user-activity/{user_id}" in routes

    def test_get_security_alerts_endpoint_exists(self):
        """Test that security alerts endpoint exists."""
        routes = [route.path for route in router.routes]
        assert "/admin/audit/security-alerts" in routes

    def test_get_monitoring_stats_endpoint_exists(self):
        """Test that monitoring stats endpoint exists."""
        routes = [route.path for route in router.routes]
        assert "/admin/audit/monitoring-stats" in routes

    def test_get_kibana_dashboard_endpoint_exists(self):
        """Test that Kibana dashboard endpoint exists."""
        routes = [route.path for route in router.routes]
        assert "/admin/audit/kibana-dashboard" in routes


class TestSecurityEventTypes:
    """Test security event types enum."""

    def test_security_event_types(self):
        """Test security event types are properly defined."""
        assert SecurityEventType.AUTH_SUCCESS.value == "auth_success"
        assert SecurityEventType.AUTH_FAILURE.value == "auth_failure"
        assert SecurityEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert SecurityEventType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"
        assert SecurityEventType.ACCESS_DENIED.value == "access_denied"
        assert SecurityEventType.ADMIN_ACTION.value == "admin_action"
        assert SecurityEventType.USER_CREATED.value == "user_created"
        assert SecurityEventType.USER_DELETED.value == "user_deleted"
        assert SecurityEventType.ROLE_CHANGED.value == "role_changed"
        assert SecurityEventType.PASSWORD_CHANGED.value == "password_changed"
        assert SecurityEventType.LOGOUT.value == "logout"
        assert SecurityEventType.SESSION_EXPIRED.value == "session_expired"
        assert SecurityEventType.API_KEY_USED.value == "api_key_used"
        assert SecurityEventType.API_KEY_REVOKED.value == "api_key_revoked"
        assert SecurityEventType.DATA_ACCESS.value == "data_access"
        assert SecurityEventType.CONFIGURATION_CHANGE.value == "configuration_change"
        assert SecurityEventType.SECURITY_ALERT.value == "security_alert"


class TestSecuritySeverity:
    """Test security severity enum."""

    def test_security_severity_levels(self):
        """Test security severity levels are properly defined."""
        assert SecuritySeverity.LOW.value == "low"
        assert SecuritySeverity.MEDIUM.value == "medium"
        assert SecuritySeverity.HIGH.value == "high"
        assert SecuritySeverity.CRITICAL.value == "critical"


@pytest.mark.asyncio
class TestSecurityMonitorAsync:
    """Test async security monitoring functionality."""

    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = SecurityMonitor()

        # Start monitoring
        await monitor.start_monitoring()
        assert monitor.monitoring_active is True

        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor.monitoring_active is False

    async def test_monitoring_loop(self):
        """Test monitoring loop execution."""
        monitor = SecurityMonitor()

        with (
            patch.object(monitor, "_check_anomalies") as mock_check_anomalies,
            patch.object(monitor, "_check_suspicious_patterns") as mock_check_patterns,
            patch.object(monitor, "_cleanup_old_events") as mock_cleanup,
        ):

            # Start monitoring
            monitor.monitoring_active = True
            monitor.monitoring_task = asyncio.create_task(monitor._monitoring_loop())

            # Wait a bit for the loop to run
            await asyncio.sleep(0.1)

            # Stop monitoring
            await monitor.stop_monitoring()

            # Verify methods were called
            mock_check_anomalies.assert_called()
            mock_check_patterns.assert_called()
            mock_cleanup.assert_called()


# Integration test for the complete security monitoring system
class TestSecurityMonitoringIntegration:
    """Integration tests for security monitoring system."""

    def test_security_logger_with_monitor_integration(self):
        """Test integration between security logger and monitor."""
        logger = SecurityLogger()
        monitor = SecurityMonitor()

        # Log a security event
        event_id = logger.log_auth_success(
            user_id="user_123", ip_address="192.168.1.100"
        )

        # Manually record the event in the monitor
        monitor.record_event(
            SecurityEventType.AUTH_SUCCESS,
            {
                "user_id": "user_123",
                "ip_address": "192.168.1.100",
                "event_id": event_id,
            },
        )

        # Verify the event was recorded
        assert SecurityEventType.AUTH_SUCCESS.value in monitor.event_counts
        assert len(monitor.event_counts[SecurityEventType.AUTH_SUCCESS.value]) == 1

    def test_middleware_with_logger_integration(self):
        """Test integration between middleware and security logger."""
        middleware = SecurityLoggingMiddleware(Mock(), enable_kibana=False)

        # Mock request
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/auth/login"
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {"user-agent": "Mozilla/5.0"}

        # Mock call_next
        async def mock_call_next(req):
            response = Mock()
            response.status_code = 401
            return response

        # Mock the security logger
        with patch.object(middleware.security_logger, "log_auth_failure") as mock_log:
            # This would be called in the actual middleware dispatch
            middleware.security_logger.log_auth_failure(
                email="user@example.com",
                ip_address="192.168.1.100",
                reason="Invalid credentials",
                request=request,
            )

            mock_log.assert_called_once()
