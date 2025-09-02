"""
Enhanced input validation and sanitization for security.

This module provides XSS protection utilities for the DevCycle application.
"""

import re
from typing import Any


class XSSValidator:
    """Validator for XSS protection that can be used in Pydantic models."""

    @staticmethod
    def validate_no_xss(v: Any) -> Any:
        """Validate that string doesn't contain XSS patterns."""
        if not isinstance(v, str):
            return v

        # Check for common XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>.*?</style>",
            r"expression\s*\(",
            r"url\s*\(",
            r"@import",
        ]

        for pattern in xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous content detected: {pattern}")

        return v

    @staticmethod
    def validate_no_sql_injection(v: Any) -> Any:
        """Validate that string doesn't contain SQL injection patterns."""
        if not isinstance(v, str):
            return v

        # Check for common SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
            r"(\b(OR|AND)\s+\w+\s*LIKE\s+\w+)",
            r"(\b(OR|AND)\s+\w+\s*IN\s*\([^)]+\))",
            r"(\b(OR|AND)\s+\w+\s*BETWEEN\s+\w+\s+AND\s+\w+)",
            r"(\b(OR|AND)\s+\w+\s*IS\s+NULL)",
            r"(\b(OR|AND)\s+\w+\s*IS\s+NOT\s+NULL)",
            r"(\b(OR|AND)\s+\w+\s*EXISTS\s*\([^)]+\))",
            r"(\b(OR|AND)\s+\w+\s*NOT\s+EXISTS\s*\([^)]+\))",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    f"Potentially dangerous SQL pattern detected: {pattern}"
                )

            return v
