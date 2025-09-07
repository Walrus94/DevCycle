"""
Security Logging Middleware.

Enhanced logging middleware with security event tracking and Kibana integration.
"""

import time
from typing import Any, Dict, Optional, cast

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from ...core.logging import SecurityEventType, SecurityLogger, SecuritySeverity


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced security logging middleware with Kibana integration."""

    def __init__(self, app: Any, enable_kibana: bool = True) -> None:
        """Initialize security logging middleware."""
        super().__init__(app)
        self.security_logger = SecurityLogger()
        self.enable_kibana = enable_kibana
        self._setup_kibana_integration()

    def _setup_kibana_integration(self) -> None:
        """Set up Kibana integration for structured logging."""
        if self.enable_kibana:
            # Configure structured logging for Kibana
            import structlog

            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    # Custom processor for Kibana integration
                    self._kibana_processor,
                    structlog.processors.JSONRenderer(),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )

    def _kibana_processor(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add Kibana-specific fields to log events."""
        # Add Kibana index pattern
        event_dict["@timestamp"] = event_dict.get("timestamp")
        event_dict["service"] = "devcycle-api"
        event_dict["environment"] = "production"  # This should come from config

        # Add security-specific fields for Kibana dashboards
        if "event_type" in event_dict:
            event_dict["security_event"] = True
            event_dict["event_category"] = "security"

            # Add severity mapping for Kibana
            severity_mapping = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            event_dict["severity_level"] = severity_mapping.get(
                event_dict.get("severity", "medium"), 2
            )

        return event_dict

    def _extract_user_info(self, request: Request) -> Dict[str, Any]:
        """Extract user information from JWT token."""
        user_info = {}

        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # For now, we'll just extract basic info without full JWT validation
                # In production, this should use proper JWT validation
                token = auth_header[7:]
                if token and len(token) > 10:  # Basic token validation
                    user_info = {
                        "user_id": "extracted_from_token",  # Placeholder
                        "email": "user@example.com",  # Placeholder
                        "roles": ["user"],  # Placeholder
                        "is_admin": False,  # Placeholder
                    }
        except Exception:  # nosec B110 - Intentional pass for token validation
            # Invalid token or other error, continue without user info
            pass

        return user_info

    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request."""
        client_info = {}

        # Get client IP
        if request.client:
            client_info["ip_address"] = request.client.host
        else:
            # Check for forwarded headers
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                client_info["ip_address"] = forwarded_for.split(",")[0].strip()
            else:
                client_info["ip_address"] = "unknown"

        # Get user agent
        client_info["user_agent"] = request.headers.get("user-agent", "unknown")

        # Get referer
        client_info["referer"] = request.headers.get("referer", "")

        return client_info

    def _is_security_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint is security-sensitive."""
        security_endpoints = [
            "/api/v1/auth/",
            "/api/v1/admin/",
            "/api/v1/users/",
            "/api/v1/security/",
            "/api/v1/audit/",
        ]
        return any(path.startswith(endpoint) for endpoint in security_endpoints)

    async def dispatch(self, request: Request, call_next: Any) -> StarletteResponse:
        """Process request with security logging."""
        start_time = time.time()

        # Extract information
        client_info = self._get_client_info(request)
        user_info = self._extract_user_info(request)

        # Determine if this is a security-sensitive request
        is_security_sensitive = self._is_security_sensitive_endpoint(request.url.path)

        # Log request
        request_details = {
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "is_security_sensitive": is_security_sensitive,
            "user_authenticated": bool(user_info.get("user_id")),
            "user_roles": user_info.get("roles", []),
            "is_admin": user_info.get("is_admin", False),
        }

        # Log security-sensitive requests
        if is_security_sensitive:
            if user_info.get("user_id"):
                self.security_logger.log_security_event(
                    SecurityEventType.ACCESS_DENIED,  # Updated based on response
                    user_id=user_info["user_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    details=request_details,
                    severity=SecuritySeverity.LOW,
                )
            else:
                self.security_logger.log_auth_failure(
                    email="unknown",
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    reason="Unauthenticated access to security endpoint",
                )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log security-relevant exceptions
            self.security_logger.log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_info.get("user_id"),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                details={
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    **request_details,
                },
                severity=SecuritySeverity.HIGH,
            )
            raise

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response based on status code
        response_details = {
            "status_code": response.status_code,
            "process_time": process_time,
            **request_details,
        }

        if response.status_code == 401:
            self.security_logger.log_auth_failure(
                email=user_info.get("email", "unknown"),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                reason="Unauthorized access",
            )
        elif response.status_code == 403:
            self.security_logger.log_security_event(
                SecurityEventType.ACCESS_DENIED,
                user_id=user_info.get("user_id"),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                request=request,
                details={
                    "resource": request.url.path,
                    "reason": "Insufficient permissions",
                    **response_details,
                },
                severity=SecuritySeverity.MEDIUM,
            )
        elif response.status_code == 429:
            self.security_logger.log_rate_limit_exceeded(
                ip_address=client_info["ip_address"],
                endpoint=request.url.path,
            )
        elif response.status_code >= 500:
            # Log server errors as suspicious activity
            self.security_logger.log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_info.get("user_id"),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                details={"activity": "Server error occurred", **response_details},
                severity=SecuritySeverity.MEDIUM,
            )
        elif is_security_sensitive and response.status_code < 400:
            # Log successful access to security-sensitive endpoints
            self.security_logger.log_security_event(
                SecurityEventType.ACCESS_DENIED,  # This will be updated to success
                user_id=user_info.get("user_id"),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                details={
                    "activity": "Successful access to security endpoint",
                    **response_details,
                },
                severity=SecuritySeverity.LOW,
            )

        # Add security headers for Kibana correlation
        if isinstance(response, StarletteResponse):
            response.headers["X-Request-ID"] = request_details.get(
                "request_id", "unknown"
            )
            response.headers["X-Process-Time"] = str(process_time)

        return cast(StarletteResponse, response)


class KibanaIntegrationMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for Kibana integration and log correlation."""

    def __init__(
        self, app: Any, kibana_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize Kibana integration middleware."""
        super().__init__(app)
        self.kibana_config = kibana_config or {}
        self._setup_kibana_fields()

    def _setup_kibana_fields(self) -> None:
        """Set up Kibana-specific fields for better log correlation."""
        self.kibana_fields = {
            "service_name": "devcycle-api",
            "service_version": "1.0.0",
            "environment": self.kibana_config.get("environment", "production"),
            "log_level": "info",
            "message_type": "security_event",
        }

    async def dispatch(self, request: Request, call_next: Any) -> StarletteResponse:
        """Add Kibana correlation fields to requests."""
        # Add correlation ID for tracing
        correlation_id = request.headers.get(
            "X-Correlation-ID", f"req_{int(time.time())}"
        )

        # Add to request state for use in other middleware
        request.state.correlation_id = correlation_id
        request.state.kibana_fields = self.kibana_fields.copy()

        response = await call_next(request)

        # Add correlation headers to response
        if hasattr(response, "headers"):
            response.headers["X-Correlation-ID"] = correlation_id

        return cast(StarletteResponse, response)
