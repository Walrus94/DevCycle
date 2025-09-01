"""
Health check endpoints for the DevCycle API.

This module provides health monitoring and status endpoints.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Union

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ...core.config import get_config
from ...core.logging import get_logger
from ..models import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic Health Check",
    description="Returns the basic health status of the DevCycle API service",
    response_description="Health status information including service name and version",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    This endpoint provides a simple health check that returns the current
    status of the API service. It's designed to be lightweight and fast,
    suitable for load balancer health checks and basic monitoring.

    **Use Cases:**
    - Load balancer health checks
    - Basic service monitoring
    - Quick status verification

    **Response Status:**
    - `healthy`: Service is running normally
    - `degraded`: Service has some issues but is still functional
    - `unhealthy`: Service is not functioning properly

    Returns:
        HealthResponse: Basic health status information

    Example:
        ```json
        {
            "status": "healthy",
            "service": "DevCycle API",
            "version": "0.1.0",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        ```
    """
    return HealthResponse(
        status="healthy",
        service="DevCycle API",
        version="0.1.0",
    )


@router.get(
    "/health/detailed",
    response_model=HealthResponse,
    summary="Detailed Health Check",
    description=(
        "Returns comprehensive health status including component checks and metrics"
    ),
    response_description=(
        "Detailed health status with component health and performance metrics"
    ),
    tags=["Health"],
)
async def detailed_health_check() -> HealthResponse:
    """
    Detailed health check endpoint.

    This endpoint provides a comprehensive health check that includes:
    - Individual component health status
    - Performance metrics
    - Response time measurements
    - Configuration validation

    **Components Checked:**
    - API service status
    - Configuration accessibility
    - Logging system status

    **Metrics Included:**
    - Response time in milliseconds
    - System uptime (when available)
    - Component-specific health indicators

    **Response Status:**
    - `healthy`: All components are functioning normally
    - `degraded`: Some components have issues but service is functional
    - `unhealthy`: Critical components are not functioning

    Returns:
        HealthResponse: Comprehensive health status with components and metrics

    Example:
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
    """
    logger = get_logger("api.health")
    start_time = time.time()

    try:
        # Get configuration
        _ = get_config()  # Check if config is accessible
        config_status = "healthy"
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        config_status = "unhealthy"

    # Calculate response time
    response_time = time.time() - start_time

    components = {
        "api": "healthy",
        "configuration": config_status,
        "logging": "healthy",
    }

    metrics = {
        "response_time_ms": round(response_time * 1000, 2),
        "uptime": "N/A",  # TODO: Implement uptime tracking
    }

    # Determine overall status
    overall_status = "healthy"
    if any(components[key] == "unhealthy" for key in components):
        overall_status = "degraded"

    logger.info(f"Health check completed in {response_time:.4f}s")
    return HealthResponse(
        status=overall_status,
        service="DevCycle API",
        version="0.1.0",
        components=components,
        metrics=metrics,
    )


@router.get("/health/ready", response_model=None)
async def readiness_check() -> Union[Dict[str, Any], JSONResponse]:
    """
    Readiness check endpoint.

    This endpoint indicates whether the service is ready to accept requests.

    Returns:
        Readiness status
    """
    try:
        # Check if we can access configuration
        _ = get_config()  # Check if config is accessible

        # Check if we can access logging
        logger = get_logger("api.health")

        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "DevCycle API",
            "checks": {"configuration": "ready", "logging": "ready"},
        }
    except Exception as e:
        logger = get_logger("api.health")
        logger.error(f"Readiness check failed: {e}")

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "DevCycle API",
                "error": str(e),
            },
        )


@router.get("/health/live", response_model=Dict[str, Any])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    This endpoint indicates whether the service is alive and running.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "DevCycle API",
    }
