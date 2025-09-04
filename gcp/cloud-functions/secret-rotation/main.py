"""
GCP Cloud Function for automated secret rotation.

This function can be triggered by Cloud Scheduler to automatically rotate
secrets in GCP Secret Manager. It supports different rotation strategies
for different types of secrets.
"""

import json
import logging
import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from google.api_core import exceptions as gcp_exceptions
from google.cloud import secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_secure_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    return secrets.token_urlsafe(32)


def rotate_secret(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Cloud Function to rotate secrets in GCP Secret Manager.

    This function can be triggered by Cloud Scheduler or Pub/Sub.

    Args:
        event: Event data (can contain secret_id, environment, etc.)
        context: Function context

    Returns:
        Result dictionary with success status and details
    """
    try:
        # Initialize Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set")

        # Parse event data
        secret_id = event.get("secret_id")
        environment = event.get("environment", "prod")
        rotation_type = event.get("rotation_type", "auto")

        if not secret_id:
            raise ValueError("secret_id is required in event data")

        logger.info(
            f"Starting rotation for secret: {secret_id} in environment: {environment}"
        )

        # Generate new secret value based on type
        new_value = _generate_secret_value(secret_id, rotation_type)

        # Create/update secret
        result = _update_secret(client, project_id, secret_id, new_value, environment)

        # Log rotation event
        _log_rotation_event(secret_id, environment, rotation_type, result)

        return {
            "success": True,
            "secret_id": secret_id,
            "environment": environment,
            "rotation_type": rotation_type,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error rotating secret: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def _generate_secret_value(secret_id: str, rotation_type: str) -> str:
    """Generate a new secret value based on the secret type."""
    secret_id_lower = secret_id.lower()

    if "jwt" in secret_id_lower or "secret-key" in secret_id_lower:
        return generate_jwt_secret()
    elif "password" in secret_id_lower:
        return generate_secure_password()
    elif "token" in secret_id_lower:
        # For API tokens, we might need to call external APIs
        # For now, generate a secure token
        return secrets.token_urlsafe(48)
    else:
        # Default: generate a secure random string
        return secrets.token_urlsafe(32)


def _update_secret(
    client: secretmanager.SecretManagerServiceClient,
    project_id: str,
    secret_id: str,
    new_value: str,
    environment: str,
) -> Dict[str, Any]:
    """Update secret in GCP Secret Manager."""
    secret_name = f"{environment}-{secret_id}"
    parent = f"projects/{project_id}"

    try:
        # Create secret if it doesn't exist
        try:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            logger.info(f"Created new secret: {secret_name}")
        except gcp_exceptions.AlreadyExists:
            logger.info(f"Secret already exists: {secret_name}")

        # Add new secret version
        response = client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_name}",
                "payload": {"data": new_value.encode("UTF-8")},
            }
        )

        logger.info(f"Added new version to secret: {secret_name}")

        return {
            "action": "updated",
            "secret_name": secret_name,
            "version": response.name.split("/")[-1],
        }

    except Exception as e:
        logger.error(f"Error updating secret {secret_name}: {e}")
        raise


def _log_rotation_event(
    secret_id: str, environment: str, rotation_type: str, result: Dict[str, Any]
) -> None:
    """Log secret rotation event for audit purposes."""
    log_entry = {
        "event_type": "secret_rotation",
        "secret_id": secret_id,
        "environment": environment,
        "rotation_type": rotation_type,
        "timestamp": datetime.utcnow().isoformat(),
        "result": result,
    }

    logger.info(f"Secret rotation completed: {json.dumps(log_entry)}")

    # In a real implementation, you might want to:
    # 1. Send to Cloud Logging
    # 2. Send to monitoring systems
    # 3. Send notifications to security team
    # 4. Update audit databases


def bulk_rotate_secrets(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Cloud Function to rotate multiple secrets at once.

    Args:
        event: Event data containing list of secrets to rotate
        context: Function context

    Returns:
        Result dictionary with success status and details
    """
    try:
        secrets_to_rotate = event.get("secrets", [])
        environment = event.get("environment", "prod")

        if not secrets_to_rotate:
            raise ValueError("secrets list is required in event data")

        results = []
        for secret_config in secrets_to_rotate:
            secret_id = secret_config.get("secret_id")
            rotation_type = secret_config.get("rotation_type", "auto")

            if not secret_id:
                logger.warning("Skipping secret without secret_id")
                continue

            # Rotate individual secret
            result = rotate_secret(
                {
                    "secret_id": secret_id,
                    "environment": environment,
                    "rotation_type": rotation_type,
                },
                context,
            )

            results.append(result)

        success_count = sum(1 for r in results if r.get("success", False))

        return {
            "success": success_count == len(results),
            "total_secrets": len(results),
            "successful_rotations": success_count,
            "failed_rotations": len(results) - success_count,
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in bulk secret rotation: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def validate_secrets(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Cloud Function to validate that all required secrets exist and are accessible.

    Args:
        event: Event data
        context: Function context

    Returns:
        Validation results
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        environment = event.get("environment", "prod")

        required_secrets = [
            "jwt-secret-key",
            "database-password",
            "redis-password",
            "huggingface-token",
        ]

        validation_results = {}

        for secret_id in required_secrets:
            secret_name = f"projects/{project_id}/secrets/{environment}-{secret_id}/versions/latest"

            try:
                response = client.access_secret_version(request={"name": secret_name})
                secret_value = response.payload.data.decode("UTF-8")

                validation_results[secret_id] = {
                    "exists": True,
                    "accessible": True,
                    "length": len(secret_value),
                    "version": response.name.split("/")[-1],
                }

            except gcp_exceptions.NotFound:
                validation_results[secret_id] = {
                    "exists": False,
                    "accessible": False,
                    "error": "Secret not found",
                }
            except Exception as e:
                validation_results[secret_id] = {
                    "exists": True,
                    "accessible": False,
                    "error": str(e),
                }

        all_valid = all(
            result.get("accessible", False) for result in validation_results.values()
        )

        return {
            "success": all_valid,
            "environment": environment,
            "validation_results": validation_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error validating secrets: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
