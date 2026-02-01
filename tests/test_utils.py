"""Tests for src/utils.py"""

import pytest
from src.utils import (
    validate_ip_address,
    validate_subnet_mask,
    validate_password,
    validate_panos_version,
    format_duration,
    get_error_suggestion,
)


class TestValidateIPAddress:
    """Tests for validate_ip_address function."""

    def test_valid_ip_addresses(self):
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("255.255.255.255") is True
        assert validate_ip_address("0.0.0.0") is True
        assert validate_ip_address("172.16.0.1") is True

    def test_invalid_ip_addresses(self):
        assert validate_ip_address("") is False
        assert validate_ip_address("192.168.1") is False
        assert validate_ip_address("192.168.1.256") is False
        assert validate_ip_address("192.168.1.-1") is False
        assert validate_ip_address("192.168.1.1.1") is False
        assert validate_ip_address("abc.def.ghi.jkl") is False
        assert validate_ip_address("192.168.1.1a") is False

    def test_ip_with_whitespace(self):
        assert validate_ip_address("  192.168.1.1  ") is True
        assert validate_ip_address(" 10.0.0.1 ") is True


class TestValidateSubnetMask:
    """Tests for validate_subnet_mask function."""

    def test_valid_subnet_masks(self):
        assert validate_subnet_mask("255.255.255.0") is True
        assert validate_subnet_mask("255.255.0.0") is True
        assert validate_subnet_mask("255.0.0.0") is True
        assert validate_subnet_mask("255.255.255.255") is True
        assert validate_subnet_mask("255.255.255.128") is True
        assert validate_subnet_mask("255.255.255.192") is True
        assert validate_subnet_mask("255.255.255.224") is True
        assert validate_subnet_mask("255.255.255.240") is True
        assert validate_subnet_mask("255.255.255.248") is True
        assert validate_subnet_mask("255.255.255.252") is True

    def test_invalid_subnet_masks(self):
        assert validate_subnet_mask("255.255.255.1") is False
        assert validate_subnet_mask("255.0.255.0") is False
        assert validate_subnet_mask("192.168.1.1") is False
        assert validate_subnet_mask("0.255.255.255") is False


class TestValidatePassword:
    """Tests for validate_password function."""

    def test_valid_passwords(self):
        valid, msg = validate_password("Abcd1234")
        assert valid is True
        assert msg == ""

        valid, msg = validate_password("MyP@ssw0rd!")
        assert valid is True

        valid, msg = validate_password("Test1234567890123456789012345")  # 29 chars
        assert valid is True

    def test_password_too_short(self):
        valid, msg = validate_password("Abc123")
        assert valid is False
        assert "at least 8 characters" in msg

    def test_password_too_long(self):
        valid, msg = validate_password("A" * 32 + "a1")
        assert valid is False
        assert "31 characters or less" in msg

    def test_password_missing_uppercase(self):
        valid, msg = validate_password("abcd1234")
        assert valid is False
        assert "uppercase" in msg

    def test_password_missing_lowercase(self):
        valid, msg = validate_password("ABCD1234")
        assert valid is False
        assert "lowercase" in msg

    def test_password_missing_number(self):
        valid, msg = validate_password("Abcdefgh")
        assert valid is False
        assert "number" in msg


class TestValidatePanosVersion:
    """Tests for validate_panos_version function."""

    def test_valid_versions(self):
        valid, msg = validate_panos_version("11.2.4")
        assert valid is True
        assert msg == ""

        valid, msg = validate_panos_version("10.1.0")
        assert valid is True

        valid, msg = validate_panos_version("12.1.4")
        assert valid is True

    def test_valid_hotfix_versions(self):
        valid, msg = validate_panos_version("11.2.10-h2")
        assert valid is True

        valid, msg = validate_panos_version("10.2.9-h1")
        assert valid is True

        valid, msg = validate_panos_version("11.1.13-h1")
        assert valid is True

    def test_invalid_version_formats(self):
        valid, msg = validate_panos_version("")
        assert valid is False

        valid, msg = validate_panos_version("11.2")
        assert valid is False
        assert "Invalid version format" in msg

        valid, msg = validate_panos_version("11")
        assert valid is False

        valid, msg = validate_panos_version("11.2.4.5")
        assert valid is False

        valid, msg = validate_panos_version("abc")
        assert valid is False

    def test_invalid_hotfix_format(self):
        valid, msg = validate_panos_version("11.2.4-hotfix")
        assert valid is False

        valid, msg = validate_panos_version("11.2.4-h")
        assert valid is False

    def test_version_with_whitespace(self):
        valid, msg = validate_panos_version("  11.2.4  ")
        assert valid is True

    def test_major_version_range(self):
        valid, msg = validate_panos_version("8.0.0")
        assert valid is False
        assert "between 9 and 99" in msg

        valid, msg = validate_panos_version("9.0.0")
        assert valid is True


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_seconds(self):
        assert format_duration(30) == "30 seconds"
        assert format_duration(59) == "59 seconds"

    def test_minutes(self):
        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3599) == "59m 59s"

    def test_hours(self):
        assert format_duration(3600) == "1h 0m"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7200) == "2h 0m"


class TestGetErrorSuggestion:
    """Tests for get_error_suggestion function."""

    def test_authentication_error(self):
        error = Exception("Authentication failed")
        suggestion = get_error_suggestion(error)
        assert "username and password" in suggestion

    def test_timeout_error(self):
        error = Exception("Connection timed out")
        suggestion = get_error_suggestion(error)
        assert "unreachable" in suggestion

    def test_connection_refused(self):
        error = Exception("Connection refused")
        suggestion = get_error_suggestion(error)
        assert "SSH" in suggestion

    def test_license_error(self):
        error = Exception("License fetch failed")
        suggestion = get_error_suggestion(error)
        assert "internet access" in suggestion

    def test_generic_error(self):
        error = Exception("Something went wrong")
        suggestion = get_error_suggestion(error)
        assert "logs" in suggestion
