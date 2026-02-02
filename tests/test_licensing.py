"""Tests for src/licensing.py"""

import pytest
from unittest.mock import Mock, patch

from src.licensing import LicenseManager, fetch_and_verify_licenses


class TestLicenseManager:
    """Tests for LicenseManager class."""

    def test_init(self):
        mock_client = Mock()
        manager = LicenseManager(mock_client)
        assert manager.client == mock_client
        assert manager.progress_callback is None

    def test_init_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        manager = LicenseManager(mock_client, progress_callback=callback)
        assert manager.progress_callback == callback

    def test_update_progress_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        manager = LicenseManager(mock_client, progress_callback=callback)

        manager._update_progress("Fetching licenses...")
        callback.assert_called_with("Fetching licenses...")

    def test_update_progress_without_callback(self):
        mock_client = Mock()
        manager = LicenseManager(mock_client)
        manager._update_progress("Test")  # Should not raise

    def test_fetch_licenses_success(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "License fetched successfully"
        manager = LicenseManager(mock_client)

        result = manager.fetch_licenses()

        assert "successfully" in result.lower()

    def test_fetch_licenses_failed(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "License fetch failed"
        manager = LicenseManager(mock_client)

        with pytest.raises(RuntimeError, match="failed"):
            manager.fetch_licenses()

    def test_fetch_licenses_unable_to_connect(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Unable to connect to license server"
        manager = LicenseManager(mock_client)

        with pytest.raises(RuntimeError, match="license server"):
            manager.fetch_licenses()

    def test_fetch_licenses_invalid_auth_code(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Invalid auth code"
        manager = LicenseManager(mock_client)

        with pytest.raises(RuntimeError, match="auth code"):
            manager.fetch_licenses()

    def test_fetch_licenses_no_clear_status(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "License operation completed"
        manager = LicenseManager(mock_client)

        result = manager.fetch_licenses()
        assert result == "License operation completed"

    def test_fetch_licenses_exception(self):
        mock_client = Mock()
        mock_client.send_command.side_effect = Exception("Network error")
        manager = LicenseManager(mock_client)

        with pytest.raises(Exception):
            manager.fetch_licenses()

    def test_get_license_info(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "License info output"
        manager = LicenseManager(mock_client)

        result = manager.get_license_info()

        mock_client.send_command.assert_called_with("request license info")
        assert result == "License info output"

    def test_verify_licenses_active_threat_prevention(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Threat Prevention: Active"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is True

    def test_verify_licenses_active_pandb(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "PanDB URL Filtering: Active"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is True

    def test_verify_licenses_active_wildfire(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "WildFire: Active"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is True

    def test_verify_licenses_active_globalprotect(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "GlobalProtect Gateway: Active"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is True

    def test_verify_licenses_active_valid(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "License valid until 2027"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is True

    def test_verify_licenses_not_active(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "No licenses installed"
        manager = LicenseManager(mock_client)

        assert manager.verify_licenses_active() is False


class TestFetchAndVerifyLicenses:
    """Tests for fetch_and_verify_licenses function."""

    @patch('src.licensing.PANOSSSHClient')
    def test_fetch_and_verify_success(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "License fetched successfully",  # fetch_licenses
            "Threat Prevention: Active",  # verify
        ]
        mock_client_class.return_value = mock_client

        result = fetch_and_verify_licenses("10.0.0.1", "admin", "password")

        assert result is True
        mock_client.connect.assert_called()
        mock_client.disconnect.assert_called()

    @patch('src.licensing.PANOSSSHClient')
    def test_fetch_and_verify_with_callback(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "License fetched successfully",
            "Threat Prevention: Active",
        ]
        mock_client_class.return_value = mock_client

        callback = Mock()
        result = fetch_and_verify_licenses(
            "10.0.0.1", "admin", "password",
            progress_callback=callback
        )

        assert result is True
        callback.assert_called()

    @patch('src.licensing.PANOSSSHClient')
    def test_fetch_and_verify_not_active(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "License fetched successfully",
            "No licenses",  # Not active
        ]
        mock_client_class.return_value = mock_client

        result = fetch_and_verify_licenses("10.0.0.1", "admin", "password")

        assert result is True  # Still returns True as fetch succeeded

    @patch('src.licensing.time.sleep')
    @patch('src.licensing.PANOSSSHClient')
    def test_fetch_and_verify_retry_success(self, mock_client_class, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            Exception("First attempt failed"),
            "License fetched successfully",
            "Threat Prevention: Active",
        ]
        mock_client_class.return_value = mock_client

        result = fetch_and_verify_licenses(
            "10.0.0.1", "admin", "password",
            max_retries=3, retry_delay=1
        )

        assert result is True

    @patch('src.licensing.time.sleep')
    @patch('src.licensing.PANOSSSHClient')
    def test_fetch_and_verify_all_retries_fail(self, mock_client_class, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.side_effect = Exception("Failed")
        mock_client_class.return_value = mock_client

        with pytest.raises(RuntimeError, match="failed after"):
            fetch_and_verify_licenses(
                "10.0.0.1", "admin", "password",
                max_retries=2, retry_delay=1
            )

        mock_client.disconnect.assert_called()
