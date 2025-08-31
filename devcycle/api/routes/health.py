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

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "DevCycle API",
        "version": "0.1.0",
    }


@router.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint.

    Returns:
        Comprehensive health status information
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

    health_data: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "DevCycle API",
        "version": "0.1.0",
        "components": {
            "api": "healthy",
            "configuration": config_status,
            "logging": "healthy",
        },
        "metrics": {
            "response_time_ms": round(response_time * 1000, 2),
            "uptime": "N/A",  # TODO: Implement uptime tracking
        },
    }

    # Determine overall status
    components_dict = health_data["components"]
    if any(components_dict[key] == "unhealthy" for key in components_dict):
        health_data["status"] = "degraded"

    logger.info(f"Health check completed in {response_time:.4f}s")
    return health_data


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
