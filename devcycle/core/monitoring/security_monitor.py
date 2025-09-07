"""
Security Event Monitoring System.

Real-time security event monitoring with anomaly detection and Kibana integration.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

import structlog

from ..logging import SecurityEventType, SecurityLogger, SecuritySeverity


@dataclass
class SecurityAlert:
    """Security alert data structure."""

    alert_id: str
    alert_type: str
    severity: SecuritySeverity
    description: str
    event_count: int
    time_window: timedelta
    events: List[Dict[str, Any]]
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resolved: bool = False


class SecurityMonitor:
    """Monitor security events and detect anomalies with Kibana integration."""

    def __init__(self, kibana_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize security monitor."""
        self.kibana_config = kibana_config or {}
        self.security_logger = SecurityLogger()
        self.logger = structlog.get_logger("security_monitor")

        # Event storage for monitoring
        self.event_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.user_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.ip_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))

        # Alert thresholds
        self.alert_thresholds = {
            SecurityEventType.AUTH_FAILURE: {
                "count": 5,
                "window": timedelta(minutes=15),
                "severity": SecuritySeverity.HIGH,
            },
            SecurityEventType.RATE_LIMIT_EXCEEDED: {
                "count": 3,
                "window": timedelta(minutes=10),
                "severity": SecuritySeverity.MEDIUM,
            },
            SecurityEventType.SUSPICIOUS_ACTIVITY: {
                "count": 2,
                "window": timedelta(minutes=30),
                "severity": SecuritySeverity.HIGH,
            },
            SecurityEventType.ACCESS_DENIED: {
                "count": 10,
                "window": timedelta(minutes=20),
                "severity": SecuritySeverity.MEDIUM,
            },
        }

        # Suspicious patterns
        self.suspicious_patterns = {
            "rapid_failed_logins": {
                "threshold": 3,
                "window": timedelta(minutes=5),
                "description": "Rapid failed login attempts",
            },
            "multiple_ip_addresses": {
                "threshold": 3,
                "window": timedelta(hours=1),
                "description": "User accessing from multiple IP addresses",
            },
            "unusual_hours": {
                "threshold": 1,
                "window": timedelta(hours=24),
                "description": "Activity during unusual hours",
            },
        }

        # Alert storage
        self.active_alerts: Dict[str, SecurityAlert] = {}
        self.alert_history: List[SecurityAlert] = []

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

    def _setup_kibana_integration(self) -> None:
        """Set up Kibana integration for monitoring data."""
        if self.kibana_config.get("enabled", False):
            # Configure structured logging for Kibana
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
                    self._kibana_monitoring_processor,
                    structlog.processors.JSONRenderer(),
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )

    def _kibana_monitoring_processor(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process monitoring data for Kibana integration."""
        # Add Kibana fields for monitoring
        event_dict["@timestamp"] = event_dict.get("timestamp")
        event_dict["service"] = "devcycle-security-monitor"
        event_dict["monitoring"] = True
        event_dict["alert_type"] = event_dict.get("alert_type", "monitoring")

        return event_dict

    async def start_monitoring(self) -> None:
        """Start the security monitoring system."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Security monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the security monitoring system."""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Security monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Run the main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_anomalies()
                await self._check_suspicious_patterns()
                await self._cleanup_old_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error("Security monitoring error", error=str(e))
                await asyncio.sleep(30)  # Wait before retrying

    async def _check_anomalies(self) -> None:
        """Check for security anomalies and generate alerts."""
        current_time = datetime.now(timezone.utc)

        for event_type, threshold_config in self.alert_thresholds.items():
            if event_type.value in self.event_counts:
                recent_events = [
                    event
                    for event in self.event_counts[event_type.value]
                    if current_time - event["timestamp"] <= threshold_config["window"]
                ]

                if len(recent_events) >= int(
                    cast(int, threshold_config.get("count", 5))
                ):
                    await self._generate_alert(
                        event_type,
                        recent_events,
                        SecuritySeverity(threshold_config["severity"]),
                    )

    async def _check_suspicious_patterns(self) -> None:
        """Check for suspicious activity patterns."""
        current_time = datetime.now(timezone.utc)

        # Check rapid failed logins
        await self._check_rapid_failed_logins(current_time)

        # Check multiple IP addresses
        await self._check_multiple_ip_addresses(current_time)

        # Check unusual hours
        await self._check_unusual_hours(current_time)

    async def _check_rapid_failed_logins(self, current_time: datetime) -> None:
        """Check for rapid failed login attempts."""
        pattern = self.suspicious_patterns["rapid_failed_logins"]
        window = pattern["window"]
        threshold = pattern["threshold"]

        # Group by IP address
        ip_failures = defaultdict(list)
        for event in self.event_counts[SecurityEventType.AUTH_FAILURE.value]:
            if current_time - event["timestamp"] <= window:
                ip_failures[event.get("ip_address", "unknown")].append(event)

        for ip, failures in ip_failures.items():
            if len(failures) >= int(
                threshold if isinstance(threshold, (int, str)) else 5
            ):
                await self._generate_suspicious_alert(
                    "rapid_failed_logins",
                    f"Rapid failed login attempts from {ip}",
                    failures,
                    SecuritySeverity.HIGH,
                )

    async def _check_multiple_ip_addresses(self, current_time: datetime) -> None:
        """Check for users accessing from multiple IP addresses."""
        pattern = self.suspicious_patterns["multiple_ip_addresses"]
        window = pattern["window"]
        threshold = pattern["threshold"]

        # Group by user ID
        user_ips = defaultdict(set)
        for event in self.event_counts[SecurityEventType.AUTH_SUCCESS.value]:
            if current_time - event["timestamp"] <= window:
                user_id = event.get("user_id")
                ip_address = event.get("ip_address")
                if user_id and ip_address:
                    user_ips[user_id].add(ip_address)

        for user_id, ips in user_ips.items():
            if len(ips) >= int(threshold if isinstance(threshold, (int, str)) else 3):
                await self._generate_suspicious_alert(
                    "multiple_ip_addresses",
                    f"User {user_id} accessing from {len(ips)} different IPs",
                    list(ips),
                    SecuritySeverity.MEDIUM,
                    user_id=user_id,
                )

    async def _check_unusual_hours(self, current_time: datetime) -> None:
        """Check for activity during unusual hours."""
        pattern = self.suspicious_patterns["unusual_hours"]
        window = pattern["window"]

        # Define unusual hours (e.g., 2 AM to 6 AM)
        unusual_hours = set(range(2, 6))

        for event_type in [
            SecurityEventType.AUTH_SUCCESS.value,
            SecurityEventType.ACCESS_DENIED.value,
        ]:
            for event in self.event_counts[event_type]:
                if current_time - event["timestamp"] <= window:
                    event_hour = event["timestamp"].hour
                    if event_hour in unusual_hours:
                        await self._generate_suspicious_alert(
                            "unusual_hours",
                            f"Activity during unusual hours ({event_hour}:00)",
                            [event],
                            SecuritySeverity.LOW,
                            user_id=event.get("user_id"),
                        )

    async def _generate_alert(
        self,
        event_type: SecurityEventType,
        events: List[Dict[str, Any]],
        severity: SecuritySeverity,
    ) -> None:
        """Generate security alert."""
        alert_id = f"alert_{int(datetime.now().timestamp())}"

        alert = SecurityAlert(
            alert_id=alert_id,
            alert_type=f"threshold_exceeded_{event_type.value}",
            severity=severity,
            description=f"{event_type.value} threshold exceeded",
            event_count=len(events),
            time_window=timedelta(minutes=15),
            events=events,
            timestamp=datetime.now(timezone.utc),
            user_id=events[0].get("user_id") if events else None,
            ip_address=events[0].get("ip_address") if events else None,
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Log alert
        self.security_logger.log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=alert.user_id,
            ip_address=alert.ip_address,
            details={
                "alert_id": alert_id,
                "alert_type": alert.alert_type,
                "description": alert.description,
                "event_count": alert.event_count,
                "events": events,
            },
            severity=alert.severity,
        )

        # Log to Kibana
        self.logger.warning(
            "Security alert generated",
            alert_id=alert_id,
            alert_type=alert.alert_type,
            severity=severity.value,
            event_count=len(events),
            user_id=alert.user_id,
            ip_address=alert.ip_address,
        )

    async def _generate_suspicious_alert(
        self,
        pattern_type: str,
        description: str,
        events: List[Any],
        severity: SecuritySeverity,
        user_id: Optional[str] = None,
    ) -> None:
        """Generate suspicious activity alert."""
        alert_id = f"suspicious_{pattern_type}_{int(datetime.now().timestamp())}"

        alert = SecurityAlert(
            alert_id=alert_id,
            alert_type=f"suspicious_{pattern_type}",
            severity=severity,
            description=description,
            event_count=len(events),
            time_window=timedelta(minutes=30),
            events=events,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Log alert
        self.security_logger.log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=alert.user_id,
            details={
                "alert_id": alert_id,
                "alert_type": alert.alert_type,
                "description": alert.description,
                "pattern_type": pattern_type,
                "events": events,
            },
            severity=alert.severity,
        )

    def record_event(
        self, event_type: SecurityEventType, event_data: Dict[str, Any]
    ) -> None:
        """Record a security event for monitoring."""
        event_data["timestamp"] = datetime.now(timezone.utc)
        self.event_counts[event_type.value].append(event_data)

        # Track user activity
        if "user_id" in event_data:
            self.user_activity[event_data["user_id"]].append(event_data)

        # Track IP activity
        if "ip_address" in event_data:
            self.ip_activity[event_data["ip_address"]].append(event_data)

    async def _cleanup_old_events(self) -> None:
        """Remove events older than the monitoring window."""
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(hours=24)  # Keep 24 hours of data

        # Clean up event counts
        for event_type in self.event_counts:
            self.event_counts[event_type] = deque(
                [
                    event
                    for event in self.event_counts[event_type]
                    if event["timestamp"] > cutoff_time
                ],
                maxlen=1000,
            )

        # Clean up user activity
        for user_id in self.user_activity:
            self.user_activity[user_id] = deque(
                [
                    event
                    for event in self.user_activity[user_id]
                    if event["timestamp"] > cutoff_time
                ],
                maxlen=500,
            )

        # Clean up IP activity
        for ip_address in self.ip_activity:
            self.ip_activity[ip_address] = deque(
                [
                    event
                    for event in self.ip_activity[ip_address]
                    if event["timestamp"] > cutoff_time
                ],
                maxlen=500,
            )

    def get_active_alerts(self) -> List[SecurityAlert]:
        """Get all active security alerts."""
        return [alert for alert in self.active_alerts.values() if not alert.resolved]

    def get_alert_history(self, limit: int = 100) -> List[SecurityAlert]:
        """Get alert history."""
        return self.alert_history[-limit:]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a security alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            return True
        return False

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics for Kibana dashboards."""
        current_time = datetime.now(timezone.utc)

        stats = {
            "timestamp": current_time.isoformat(),
            "active_alerts": len(self.get_active_alerts()),
            "total_events_24h": sum(
                len(events) for events in self.event_counts.values()
            ),
            "unique_users_24h": len(self.user_activity),
            "unique_ips_24h": len(self.ip_activity),
            "event_types": {
                event_type: len(events)
                for event_type, events in self.event_counts.items()
            },
            "alert_severity_distribution": {
                severity.value: len(
                    [
                        alert
                        for alert in self.active_alerts.values()
                        if alert.severity == severity and not alert.resolved
                    ]
                )
                for severity in SecuritySeverity
            },
        }

        return stats


# Global security monitor instance
security_monitor = SecurityMonitor()
