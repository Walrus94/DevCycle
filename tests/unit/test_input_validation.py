"""
Test cases for XSS validation (DOTM-472).

This module tests the simplified XSS validation system.
"""

import pytest

from devcycle.core.validation.input import XSSValidator


class TestXSSValidator:
    """Test XSS validation functionality."""

    def test_validate_no_xss_valid_input(self):
        """Test that valid input passes XSS validation."""
        valid_inputs = [
            "Hello World",
            "User123",
            "This is a normal description",
            "Version 1.0.0",
            "test@example.com",
            "Simple text with numbers 123",
        ]

        for input_text in valid_inputs:
            result = XSSValidator.validate_no_xss(input_text)
            assert result == input_text

    def test_validate_no_xss_script_tags(self):
        """Test that script tags are blocked."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<script src='evil.js'></script>",
            "Hello <script>alert('xss')</script> World",
            "<script>document.cookie='stolen'</script>",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous content detected"
            ):
                XSSValidator.validate_no_xss(input_text)

    def test_validate_no_xss_javascript_protocol(self):
        """Test that javascript: protocol is blocked."""
        malicious_inputs = [
            "javascript:alert('xss')",
            "javascript:void(0)",
            "javascript:document.location='http://evil.com'",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous content detected"
            ):
                XSSValidator.validate_no_xss(input_text)

    def test_validate_no_xss_event_handlers(self):
        """Test that event handlers are blocked."""
        malicious_inputs = [
            "onclick=alert('xss')",
            "onload=malicious()",
            "onmouseover=steal()",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous content detected"
            ):
                XSSValidator.validate_no_xss(input_text)

    def test_validate_no_xss_iframe_tags(self):
        """Test that iframe tags are blocked."""
        malicious_inputs = [
            "<iframe src='evil.com'></iframe>",
            "<iframe></iframe>",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous content detected"
            ):
                XSSValidator.validate_no_xss(input_text)

    def test_validate_no_xss_non_string_input(self):
        """Test that non-string input is returned as-is."""
        non_string_inputs = [123, None, [], {}, True]

        for input_value in non_string_inputs:
            result = XSSValidator.validate_no_xss(input_value)
            assert result == input_value

    def test_validate_no_sql_injection_valid_input(self):
        """Test that valid input passes SQL injection validation."""
        valid_inputs = [
            "Hello World",
            "User123",
            "This is a normal description",
            "Version 1.0.0",
            "test@example.com",
        ]

        for input_text in valid_inputs:
            result = XSSValidator.validate_no_sql_injection(input_text)
            assert result == input_text

    def test_validate_no_sql_injection_select_statements(self):
        """Test that SELECT statements are blocked."""
        malicious_inputs = [
            "SELECT * FROM users",
            "select password from users",
            "SELECT username, password FROM users WHERE id = 1",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous SQL pattern detected"
            ):
                XSSValidator.validate_no_sql_injection(input_text)

    def test_validate_no_sql_injection_or_conditions(self):
        """Test that OR conditions are blocked."""
        malicious_inputs = [
            "admin OR 1=1",
            "user OR password=password",
            "OR username=admin",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous SQL pattern detected"
            ):
                XSSValidator.validate_no_sql_injection(input_text)

    def test_validate_no_sql_injection_union_attacks(self):
        """Test that UNION attacks are blocked."""
        malicious_inputs = [
            "UNION SELECT * FROM users",
            "union select password from users",
        ]

        for input_text in malicious_inputs:
            with pytest.raises(
                ValueError, match="Potentially dangerous SQL pattern detected"
            ):
                XSSValidator.validate_no_sql_injection(input_text)

    def test_validate_no_sql_injection_non_string_input(self):
        """Test that non-string input is returned as-is."""
        non_string_inputs = [123, None, [], {}, True]

        for input_value in non_string_inputs:
            result = XSSValidator.validate_no_sql_injection(input_value)
            assert result == input_value
