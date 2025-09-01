"""
Message validation middleware for DevCycle.

This module provides middleware for validating message requests,
including request size validation, content validation, and message structure validation.
"""

import json
from typing import Any, Callable, Dict, List

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .validation import MessageValidationConfig, ValidationResult
from .validation_errors import MessageSizeError, MessageValidationError

# Import the validator class that will be implemented
# from .validator import MessageValidator


class MessageValidationMiddleware:
    """Middleware for validating message requests."""

    def __init__(self, validation_config: MessageValidationConfig):
        """Initialize the middleware with validation configuration."""
        self.config = validation_config
        # self.validator = MessageValidator(validation_config)

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request through validation middleware."""
        try:
            # Validate request size
            await self._validate_request_size(request)

            # Validate content type
            await self._validate_content_type(request)

            # Validate message structure (if applicable)
            if request.url.path.startswith("/api/v1/messages"):
                await self._validate_message_structure(request)

            # Continue to the next middleware/endpoint
            response = await call_next(request)
            return response

        except HTTPException as e:
            # Re-raise HTTP exceptions as-is
            raise e
        except Exception as e:
            # Handle unexpected errors
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal validation error",
                    "detail": str(e),
                    "error_code": "VALIDATION_INTERNAL_ERROR",
                },
            )

    async def _validate_request_size(self, request: Request) -> None:
        """Validate that the request size is within limits."""
        content_length = request.headers.get("content-length")

        if content_length:
            size = int(content_length)
            if size > self.config.max_message_size_bytes:
                raise MessageSizeError(
                    actual_size=size,
                    max_size=self.config.max_message_size_bytes,
                    size_type="request",
                )

    async def _validate_content_type(self, request: Request) -> None:
        """Validate the content type of the request."""
        content_type = request.headers.get("content-type", "")

        # For message endpoints, require JSON content type
        if request.url.path.startswith("/api/v1/messages") and request.method in [
            "POST",
            "PUT",
            "PATCH",
        ]:
            if not content_type.startswith("application/json"):
                raise MessageValidationError(
                    errors=[
                        f"Invalid content type: {content_type}. "
                        f"Expected application/json"
                    ],
                    error_code="INVALID_CONTENT_TYPE",
                )

    async def _validate_message_structure(self, request: Request) -> None:
        """Validate the structure of message requests."""
        if request.method not in ["POST", "PUT", "PATCH"]:
            return

        try:
            # Read and parse the request body
            body = await request.body()

            if not body:
                return  # Empty body is acceptable for some endpoints

            # Parse JSON
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise MessageValidationError(
                    errors=[f"Invalid JSON format: {str(e)}"],
                    error_code="INVALID_JSON_FORMAT",
                )

            # Validate data size
            data_size = len(json.dumps(data).encode("utf-8"))
            if data_size > self.config.max_data_size_bytes:
                raise MessageSizeError(
                    actual_size=data_size,
                    max_size=self.config.max_data_size_bytes,
                    size_type="data",
                )

            # Basic structure validation
            if not isinstance(data, dict):
                raise MessageValidationError(
                    errors=["Request body must be a JSON object"],
                    error_code="INVALID_REQUEST_STRUCTURE",
                )

            # Validate required fields based on endpoint
            await self._validate_endpoint_specific_structure(request.url.path, data)

        except (MessageValidationError, MessageSizeError):
            # Re-raise validation errors
            raise
        except Exception as e:
            # Handle other errors
            raise MessageValidationError(
                errors=[f"Error validating message structure: {str(e)}"],
                error_code="STRUCTURE_VALIDATION_ERROR",
            )

    async def _validate_endpoint_specific_structure(
        self, path: str, data: Dict[str, Any]
    ) -> None:
        """Validate structure based on specific endpoint."""
        errors = []

        if "/send" in path:
            # Validate send message structure
            if "agent_id" not in data:
                errors.append("Missing required field: agent_id")
            if "action" not in data:
                errors.append("Missing required field: action")

            # Validate agent_id format
            if "agent_id" in data and not isinstance(data["agent_id"], str):
                errors.append("agent_id must be a string")

            # Validate action format
            if "action" in data and not isinstance(data["action"], str):
                errors.append("action must be a string")

        elif "/broadcast" in path:
            # Validate broadcast message structure
            if "agent_types" not in data:
                errors.append("Missing required field: agent_types")
            if "action" not in data:
                errors.append("Missing required field: action")

            # Validate agent_types format
            if "agent_types" in data:
                if not isinstance(data["agent_types"], list):
                    errors.append("agent_types must be a list")
                elif not data["agent_types"]:
                    errors.append("agent_types cannot be empty")

        elif "/route" in path:
            # Validate route message structure
            if "capabilities" not in data:
                errors.append("Missing required field: capabilities")
            if "action" not in data:
                errors.append("Missing required field: action")

            # Validate capabilities format
            if "capabilities" in data:
                if not isinstance(data["capabilities"], list):
                    errors.append("capabilities must be a list")
                elif not data["capabilities"]:
                    errors.append("capabilities cannot be empty")

        if errors:
            raise MessageValidationError(
                errors=errors, error_code="INVALID_REQUEST_STRUCTURE"
            )


class MessageValidator:
    """Core message validation logic."""

    def __init__(self, validation_config: MessageValidationConfig):
        """Initialize the message validator."""
        self.config = validation_config

    async def validate_message_send(
        self, request_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a message send request."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate required fields
        if "agent_id" not in request_data:
            errors.append("Missing required field: agent_id")
        if "action" not in request_data:
            errors.append("Missing required field: action")

        # Validate field types
        if "agent_id" in request_data and not isinstance(request_data["agent_id"], str):
            errors.append("agent_id must be a string")
        if "action" in request_data and not isinstance(request_data["action"], str):
            errors.append("action must be a string")

        # Validate field lengths
        if "agent_id" in request_data and isinstance(request_data["agent_id"], str):
            if len(request_data["agent_id"]) == 0:
                errors.append("agent_id cannot be empty")
            elif len(request_data["agent_id"]) > 100:
                errors.append("agent_id too long (max 100 characters)")

        if "action" in request_data and isinstance(request_data["action"], str):
            if len(request_data["action"]) == 0:
                errors.append("action cannot be empty")
            elif len(request_data["action"]) > 200:
                errors.append("action too long (max 200 characters)")

        # Validate priority if present
        if "priority" in request_data and request_data["priority"] is not None:
            valid_priorities = ["low", "normal", "high", "urgent"]
            if request_data["priority"] not in valid_priorities:
                errors.append(f"Invalid priority: {request_data['priority']}")

        # Validate TTL if present
        if "ttl" in request_data and request_data["ttl"] is not None:
            if not isinstance(request_data["ttl"], int):
                errors.append("ttl must be an integer")
            elif request_data["ttl"] < 0 or request_data["ttl"] > 86400:
                errors.append("ttl must be between 0 and 86400 seconds")

        # Validate data payload size
        if "data" in request_data:
            data_str = json.dumps(request_data["data"])
            data_size = len(data_str.encode("utf-8"))
            if data_size > self.config.max_data_size_bytes:
                errors.append(
                    f"Data payload too large: {data_size} bytes "
                    f"(max {self.config.max_data_size_bytes})"
                )

        # Validate allowed actions if configured
        if self.config.allowed_actions and "action" in request_data:
            if request_data["action"] not in self.config.allowed_actions:
                errors.append(f"Action '{request_data['action']}' not allowed")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings if self.config.enable_warnings else [],
        )

    async def validate_message_broadcast(
        self, request_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a message broadcast request."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate required fields
        if "agent_types" not in request_data:
            errors.append("Missing required field: agent_types")
        if "action" not in request_data:
            errors.append("Missing required field: action")

        # Validate agent_types
        if "agent_types" in request_data:
            if not isinstance(request_data["agent_types"], list):
                errors.append("agent_types must be a list")
            elif len(request_data["agent_types"]) == 0:
                errors.append("agent_types cannot be empty")
            elif len(request_data["agent_types"]) > 10:
                errors.append("Too many agent types (max 10)")
            else:
                valid_types = [
                    "business_analyst",
                    "developer",
                    "tester",
                    "deployer",
                    "monitor",
                    "custom",
                ]
                for agent_type in request_data["agent_types"]:
                    if agent_type not in valid_types:
                        errors.append(f"Invalid agent type: {agent_type}")

        # Validate action (same as send)
        if "action" in request_data and not isinstance(request_data["action"], str):
            errors.append("action must be a string")
        elif "action" in request_data and isinstance(request_data["action"], str):
            if len(request_data["action"]) == 0:
                errors.append("action cannot be empty")
            elif len(request_data["action"]) > 200:
                errors.append("action too long (max 200 characters)")

        # Validate exclude_agent_ids if present
        if (
            "exclude_agent_ids" in request_data
            and request_data["exclude_agent_ids"] is not None
        ):
            if not isinstance(request_data["exclude_agent_ids"], list):
                errors.append("exclude_agent_ids must be a list")
            else:
                for agent_id in request_data["exclude_agent_ids"]:
                    if not isinstance(agent_id, str):
                        errors.append("All exclude_agent_ids must be strings")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings if self.config.enable_warnings else [],
        )

    async def validate_message_route(
        self, request_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a message route request."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate required fields
        if "capabilities" not in request_data:
            errors.append("Missing required field: capabilities")
        if "action" not in request_data:
            errors.append("Missing required field: action")

        # Validate capabilities
        if "capabilities" in request_data:
            if not isinstance(request_data["capabilities"], list):
                errors.append("capabilities must be a list")
            elif len(request_data["capabilities"]) == 0:
                errors.append("capabilities cannot be empty")
            elif len(request_data["capabilities"]) > 5:
                errors.append("Too many capabilities (max 5)")
            else:
                valid_capabilities = [
                    "text_processing",
                    "code_generation",
                    "testing",
                    "deployment",
                    "monitoring",
                    "analysis",
                    "planning",
                ]
                for capability in request_data["capabilities"]:
                    if capability not in valid_capabilities:
                        errors.append(f"Invalid capability: {capability}")

        # Validate action (same as send)
        if "action" in request_data and not isinstance(request_data["action"], str):
            errors.append("action must be a string")
        elif "action" in request_data and isinstance(request_data["action"], str):
            if len(request_data["action"]) == 0:
                errors.append("action cannot be empty")
            elif len(request_data["action"]) > 200:
                errors.append("action too long (max 200 characters)")

        # Validate load_balancing if present
        if (
            "load_balancing" in request_data
            and request_data["load_balancing"] is not None
        ):
            valid_strategies = ["round_robin", "least_busy", "random"]
            if request_data["load_balancing"] not in valid_strategies:
                errors.append(
                    f"Invalid load balancing strategy: {request_data['load_balancing']}"
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings if self.config.enable_warnings else [],
        )
