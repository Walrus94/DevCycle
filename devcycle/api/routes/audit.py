"""
Audit Trail API Endpoints.

Administrative endpoints for security event queries and audit trail access.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ...core.auth.decorators import require_admin
from ...core.config.settings import get_config
from ...core.monitoring.security_monitor import SecurityMonitor

router = APIRouter(prefix="/admin/audit", tags=["admin", "audit"])


class SecurityEventResponse(BaseModel):
    """Security event response model."""

    event_id: str
    event_type: str
    timestamp: datetime
    severity: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    additional_context: Dict[str, Any] = Field(default_factory=dict)


class SecurityAlertResponse(BaseModel):
    """Security alert response model."""

    alert_id: str
    alert_type: str
    severity: str
    description: str
    event_count: int
    time_window: str
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resolved: bool
    events: List[Dict[str, Any]] = Field(default_factory=list)


class MonitoringStatsResponse(BaseModel):
    """Monitoring statistics response model."""

    timestamp: datetime
    active_alerts: int
    total_events_24h: int
    unique_users_24h: int
    unique_ips_24h: int
    event_types: Dict[str, int]
    alert_severity_distribution: Dict[str, int]


class KibanaDashboardResponse(BaseModel):
    """Kibana dashboard configuration response."""

    dashboard_url: str
    index_pattern: str
    time_range: str
    filters: Dict[str, Any] = Field(default_factory=dict)


@router.get("/security-events", response_model=List[SecurityEventResponse])
@require_admin
async def get_security_events(
    request: Request,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for filtering"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
) -> List[SecurityEventResponse]:
    """Get security audit trail with filtering options."""
    try:
        # In a real implementation, this would query from a database or log storage
        # For now, we'll return mock data that demonstrates the structure

        # Mock security events for demonstration
        mock_events = [
            {
                "event_id": "evt_001",
                "event_type": "auth_failure",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=5),
                "severity": "medium",
                "user_id": None,
                "ip_address": "192.168.1.100",
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ),
                "details": {
                    "email": "user@example.com",
                    "reason": "Invalid credentials",
                },
                "additional_context": {
                    "endpoint": "/api/v1/auth/login",
                    "method": "POST",
                },
            },
            {
                "event_id": "evt_002",
                "event_type": "auth_success",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10),
                "severity": "low",
                "user_id": "user_123",
                "ip_address": "192.168.1.101",
                "user_agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                ),
                "details": {"email": "user@example.com", "login_method": "password"},
                "additional_context": {
                    "endpoint": "/api/v1/auth/login",
                    "method": "POST",
                },
            },
        ]

        # Apply filters
        filtered_events = mock_events

        if event_type:
            filtered_events = [
                e for e in filtered_events if e["event_type"] == event_type
            ]

        if user_id:
            filtered_events = [
                e for e in filtered_events if e.get("user_id") == user_id
            ]

        if ip_address:
            filtered_events = [
                e for e in filtered_events if e.get("ip_address") == ip_address
            ]

        if severity:
            filtered_events = [e for e in filtered_events if e["severity"] == severity]

        if start_date:
            filtered_events = [
                e
                for e in filtered_events
                if isinstance(e["timestamp"], datetime) and e["timestamp"] >= start_date
            ]

        if end_date:
            filtered_events = [
                e
                for e in filtered_events
                if isinstance(e["timestamp"], datetime) and e["timestamp"] <= end_date
            ]

        # Apply pagination
        paginated_events = filtered_events[offset : offset + limit]

        return [
            SecurityEventResponse(
                event_id=str(event["event_id"]),
                event_type=str(event["event_type"]),
                timestamp=(
                    event["timestamp"]
                    if isinstance(event["timestamp"], datetime)
                    else datetime.now(timezone.utc)
                ),
                severity=str(event["severity"]),
                user_id=str(event["user_id"]) if event["user_id"] else None,
                ip_address=str(event["ip_address"]) if event["ip_address"] else None,
                user_agent=str(event["user_agent"]) if event["user_agent"] else None,
                details=event["details"] if isinstance(event["details"], dict) else {},
                additional_context=cast(
                    Dict[str, Any],
                    (
                        event["additional_context"]
                        if isinstance(event.get("additional_context"), dict)
                        else {}
                    ),
                ),
            )
            for event in paginated_events
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security events: {str(e)}",
        )


@router.get("/user-activity/{user_id}", response_model=List[SecurityEventResponse])
@require_admin
async def get_user_activity(
    user_id: str,
    request: Request,
    days: int = Query(7, le=30, description="Number of days to look back"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, le=500, description="Maximum number of events to return"),
) -> List[SecurityEventResponse]:
    """Get activity audit trail for specific user."""
    try:
        # Mock user activity data
        mock_activities = [
            {
                "event_id": f"user_act_{i}",
                "event_type": "auth_success",
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=i),
                "severity": "low",
                "user_id": user_id,
                "ip_address": f"192.168.1.{100 + i}",
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ),
                "details": {"endpoint": "/api/v1/dashboard", "method": "GET"},
                "additional_context": {
                    "session_id": f"session_{i}",
                    "user_roles": ["user"],
                },
            }
            for i in range(1, min(limit + 1, 10))
        ]

        # Apply filters
        filtered_activities = mock_activities

        if event_type:
            filtered_activities = [
                a for a in filtered_activities if a["event_type"] == event_type
            ]

        return [
            SecurityEventResponse(
                event_id=str(activity["event_id"]),
                event_type=str(activity["event_type"]),
                timestamp=(
                    activity["timestamp"]
                    if isinstance(activity["timestamp"], datetime)
                    else datetime.now(timezone.utc)
                ),
                severity=str(activity["severity"]),
                user_id=str(activity["user_id"]) if activity["user_id"] else None,
                ip_address=(
                    str(activity["ip_address"]) if activity["ip_address"] else None
                ),
                user_agent=(
                    str(activity["user_agent"]) if activity["user_agent"] else None
                ),
                details=(
                    activity["details"] if isinstance(activity["details"], dict) else {}
                ),
                additional_context=cast(
                    Dict[str, Any],
                    (
                        activity["additional_context"]
                        if isinstance(activity.get("additional_context"), dict)
                        else {}
                    ),
                ),
            )
            for activity in filtered_activities[:limit]
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user activity: {str(e)}",
        )


@router.get("/security-alerts", response_model=List[SecurityAlertResponse])
@require_admin
async def get_security_alerts(
    request: Request,
    active_only: bool = Query(True, description="Return only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    limit: int = Query(50, le=200, description="Maximum number of alerts to return"),
) -> List[SecurityAlertResponse]:
    """Get security alerts."""
    try:
        # Get alerts from security monitor
        security_monitor = SecurityMonitor()

        if active_only:
            alerts = security_monitor.get_active_alerts()
        else:
            alerts = security_monitor.get_alert_history(limit)

        # Apply severity filter
        if severity:
            alerts = [alert for alert in alerts if alert.severity.value == severity]

        # Convert to response format
        alert_responses = []
        for alert in alerts[:limit]:
            alert_responses.append(
                SecurityAlertResponse(
                    alert_id=alert.alert_id,
                    alert_type=alert.alert_type,
                    severity=alert.severity.value,
                    description=alert.description,
                    event_count=alert.event_count,
                    time_window=str(alert.time_window),
                    timestamp=alert.timestamp,
                    user_id=alert.user_id,
                    ip_address=alert.ip_address,
                    resolved=alert.resolved,
                    events=alert.events,
                )
            )

        return alert_responses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security alerts: {str(e)}",
        )


@router.post("/security-alerts/{alert_id}/resolve")
@require_admin
async def resolve_security_alert(alert_id: str, request: Request) -> Dict[str, Any]:
    """Resolve a security alert."""
    try:
        security_monitor = SecurityMonitor()
        success = security_monitor.resolve_alert(alert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        return {"message": "Alert resolved successfully", "alert_id": alert_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}",
        )


@router.get("/monitoring-stats", response_model=MonitoringStatsResponse)
@require_admin
async def get_monitoring_stats(request: Request) -> MonitoringStatsResponse:
    """Get security monitoring statistics."""
    try:
        security_monitor = SecurityMonitor()
        stats = security_monitor.get_monitoring_stats()

        return MonitoringStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monitoring stats: {str(e)}",
        )


@router.get("/kibana-dashboard", response_model=KibanaDashboardResponse)
@require_admin
async def get_kibana_dashboard(
    request: Request,
    time_range: str = Query("24h", description="Time range for dashboard"),
    filters: Optional[str] = Query(
        None, description="JSON string of additional filters"
    ),
) -> KibanaDashboardResponse:
    """Get Kibana dashboard configuration for security monitoring."""
    try:
        settings = get_config()

        # Parse additional filters if provided
        additional_filters = {}
        if filters:
            try:
                additional_filters = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid filters JSON format",
                )

        # Construct Kibana dashboard URL
        base_url = settings.kibana.get("base_url", "http://localhost:5601")
        dashboard_id = settings.kibana.get(
            "security_dashboard_id", "security-monitoring"
        )

        dashboard_url = f"{base_url}/app/dashboards#/view/{dashboard_id}"

        # Add time range and filters to URL
        params = {
            "_g": {"time": {"from": f"now-{time_range}", "to": "now"}},
            "filters": additional_filters,
        }

        # Encode parameters
        import urllib.parse

        encoded_params = urllib.parse.urlencode({"params": json.dumps(params)})
        dashboard_url += f"?{encoded_params}"

        return KibanaDashboardResponse(
            dashboard_url=dashboard_url,
            index_pattern=settings.kibana.get("index_pattern", "devcycle-security-*"),
            time_range=time_range,
            filters=additional_filters,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Kibana dashboard URL: {str(e)}",
        )


@router.get("/export-events")
@require_admin
async def export_security_events(
    request: Request,
    format: str = Query("json", description="Export format (json, csv)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for filtering"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(
        1000, le=10000, description="Maximum number of events to export"
    ),
) -> Dict[str, Any]:
    """Export security events for analysis."""
    try:
        # Get filtered events (same logic as get_security_events)
        # This would integrate with actual data storage in production

        if format == "csv":
            # Generate CSV export
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            writer.writerow(
                [
                    "event_id",
                    "event_type",
                    "timestamp",
                    "severity",
                    "user_id",
                    "ip_address",
                    "user_agent",
                    "details",
                    "additional_context",
                ]
            )

            # Write mock data
            writer.writerow(
                [
                    "evt_001",
                    "auth_failure",
                    "2024-01-01T10:00:00Z",
                    "medium",
                    "",
                    "192.168.1.100",
                    "Mozilla/5.0...",
                    '{"reason": "Invalid credentials"}',
                    '{"endpoint": "/api/v1/auth/login"}',
                ]
            )

            csv_content = output.getvalue()
            output.close()

            return {
                "content": csv_content,
                "content_type": "text/csv",
                "filename": (
                    f"security_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                ),
            }

        else:  # JSON format
            # Mock JSON export
            events = [
                {
                    "event_id": "evt_001",
                    "event_type": "auth_failure",
                    "timestamp": "2024-01-01T10:00:00Z",
                    "severity": "medium",
                    "user_id": None,
                    "ip_address": "192.168.1.100",
                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    ),
                    "details": {"reason": "Invalid credentials"},
                    "additional_context": {"endpoint": "/api/v1/auth/login"},
                }
            ]

            return {
                "content": json.dumps(events, indent=2),
                "content_type": "application/json",
                "filename": (
                    f"security_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                ),
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export security events: {str(e)}",
        )
