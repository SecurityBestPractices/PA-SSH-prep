"""Tests for PANOSUpgrader class in src/panos_upgrade.py"""

import pytest
from unittest.mock import Mock, patch

from src.panos_upgrade import PANOSUpgrader, upgrade_firewall


class TestPANOSUpgrader:
    """Tests for PANOSUpgrader class."""

    def test_init(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        assert upgrader.host == "10.0.0.1"
        assert upgrader.username == "admin"
        assert upgrader.password == "password"
        assert upgrader.progress_callback is None
        assert upgrader.client is None

    def test_init_with_callback(self):
        callback = Mock()
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password", progress_callback=callback)
        assert upgrader.progress_callback == callback

    def test_update_progress_with_callback(self):
        callback = Mock()
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password", progress_callback=callback)

        upgrader._update_progress("Upgrading...")
        callback.assert_called_with("Upgrading...")

    def test_update_progress_without_callback(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader._update_progress("Test")  # Should not raise

    @patch('src.panos_upgrade.PANOSSSHClient')
    def test_connect(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.connect()

        mock_client.connect.assert_called()
        assert upgrader.client == mock_client

    def test_disconnect(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        mock_client = Mock()
        upgrader.client = mock_client

        upgrader.disconnect()

        mock_client.disconnect.assert_called()
        assert upgrader.client is None

    def test_disconnect_no_client(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.disconnect()  # Should not raise

    def test_get_current_version(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.get_panos_version.return_value = "11.2.4"

        version = upgrader.get_current_version()
        assert version == "11.2.4"

    def test_get_current_version_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader.get_current_version()

    def test_check_available_versions(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "Available versions..."

        result = upgrader.check_available_versions()
        assert result == "Available versions..."

    def test_check_available_versions_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader.check_available_versions()

    def test_download_software_with_patch(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download succeeded"

        with patch.object(upgrader, '_download_version') as mock_download:
            upgrader.download_software("11.2.4")
            # Should download base (11.2.0) and then 11.2.4
            assert mock_download.call_count == 2

    def test_download_software_base_version(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download succeeded"

        with patch.object(upgrader, '_download_version') as mock_download:
            upgrader.download_software("11.2.0")
            # Should only download 11.2.0
            mock_download.assert_called_once_with("11.2.0", 1800)

    def test_download_software_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader.download_software("11.2.4")

    def test_download_version_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader._download_version("11.2.4", 600)

    def test_wait_for_software_download_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader._wait_for_software_download("11.2.4", 60)

    def test_wait_for_software_install_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader._wait_for_software_install("11.2.4", 60)

    def test_install_software_immediate_success(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "software installed successfully"

        upgrader.install_software("11.2.4")

    def test_download_version_already_downloaded(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "already downloaded"

        upgrader._download_version("11.2.4", 600)
        # Should not raise

    def test_download_version_job_enqueued(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download job enqueued"

        with patch.object(upgrader, '_wait_for_software_download'):
            upgrader._download_version("11.2.4", 600)

    def test_download_version_success(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download succeeded successfully"

        upgrader._download_version("11.2.4", 600)

    def test_download_version_failed(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download failed: error"

        with pytest.raises(RuntimeError, match="Failed to download"):
            upgrader._download_version("11.2.4", 600)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_download_success(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10, 20]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "11.2.4  yes  downloaded"

        upgrader._wait_for_software_download("11.2.4", 60)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_download_timeout(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 100, 200]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "downloading 50%"

        with pytest.raises(RuntimeError, match="timed out"):
            upgrader._wait_for_software_download("11.2.4", 10)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_download_failed(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "download failed"

        with pytest.raises(RuntimeError, match="failed"):
            upgrader._wait_for_software_download("11.2.4", 60)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_download_progress(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10, 20, 30]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        callback = Mock()
        upgrader.progress_callback = callback
        upgrader.client = Mock()
        upgrader.client.send_command.side_effect = [
            "downloading 50%",
            "downloading 75%",
            "11.2.4  yes  downloaded",
        ]

        upgrader._wait_for_software_download("11.2.4", 120)
        assert callback.call_count >= 2

    def test_install_software(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "install succeeded"

        upgrader.install_software("11.2.4")

    def test_install_software_job_enqueued(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "install job enqueued"

        with patch.object(upgrader, '_wait_for_software_install'):
            upgrader.install_software("11.2.4")

    def test_install_software_failed(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "install failed"

        with pytest.raises(RuntimeError, match="Failed to install"):
            upgrader.install_software("11.2.4")

    def test_install_software_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader.install_software("11.2.4")

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_install_success(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10, 20]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "installed 11.2.4"

        upgrader._wait_for_software_install("11.2.4", 60)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_install_running(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10, 20, 30]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.side_effect = [
            "running install",
            "pending",
            "installed 11.2.4",
        ]

        upgrader._wait_for_software_install("11.2.4", 120)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_install_failed(self, mock_time, mock_sleep):
        # The code catches the RuntimeError from "failed" status and continues the loop
        # So we need to cause a timeout. Use iterator that returns incrementing values.
        call_count = [0]
        def time_side_effect():
            call_count[0] += 1
            # Return values: 0 (start), 10, 100 (exceeds timeout)
            if call_count[0] == 1:
                return 0
            elif call_count[0] == 2:
                return 10
            else:
                return 100  # Always return 100 to exceed timeout
        mock_time.side_effect = time_side_effect

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "installation failed"

        with pytest.raises(RuntimeError, match="timed out"):
            upgrader._wait_for_software_install("11.2.4", 60)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_install_timeout(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 100, 200]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.return_value = "running"

        with pytest.raises(RuntimeError, match="timed out"):
            upgrader._wait_for_software_install("11.2.4", 10)

    @patch('src.panos_upgrade.time.sleep')
    @patch('src.panos_upgrade.time.time')
    def test_wait_for_software_install_exception(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 10, 20, 30, 40]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        upgrader.client = Mock()
        upgrader.client.send_command.side_effect = [
            Exception("Error"),
            "installed 11.2.4",
        ]

        upgrader._wait_for_software_install("11.2.4", 60)

    def test_reboot(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        mock_client = Mock()
        upgrader.client = mock_client

        upgrader.reboot()

        mock_client.send_command_timing.assert_called()
        assert upgrader.client is None  # Should disconnect

    def test_reboot_exception(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        mock_client = Mock()
        mock_client.send_command_timing.side_effect = Exception("Connection lost")
        upgrader.client = mock_client

        upgrader.reboot()  # Should not raise
        assert upgrader.client is None

    def test_reboot_not_connected(self):
        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")

        with pytest.raises(RuntimeError, match="Not connected"):
            upgrader.reboot()

    @patch('src.panos_upgrade.wait_for_ssh')
    @patch('src.panos_upgrade.time.sleep')
    def test_wait_for_reboot_success(self, mock_sleep, mock_wait_ssh):
        mock_wait_ssh.return_value = True

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.wait_for_reboot(timeout=120)

        assert result is True

    @patch('src.panos_upgrade.wait_for_ssh')
    @patch('src.panos_upgrade.time.sleep')
    def test_wait_for_reboot_timeout(self, mock_sleep, mock_wait_ssh):
        mock_wait_ssh.return_value = False

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.wait_for_reboot(timeout=120)

        assert result is False

    @patch.object(PANOSUpgrader, 'connect')
    @patch.object(PANOSUpgrader, 'disconnect')
    @patch.object(PANOSUpgrader, 'get_current_version')
    def test_upgrade_to_version_no_upgrade_needed(self, mock_version, mock_disconnect, mock_connect):
        mock_version.return_value = "11.2.4"

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.upgrade_to_version("11.2.4")

        assert result is True

    @patch('src.panos_upgrade.get_upgrade_path')
    @patch.object(PANOSUpgrader, 'connect')
    @patch.object(PANOSUpgrader, 'disconnect')
    @patch.object(PANOSUpgrader, 'get_current_version')
    @patch.object(PANOSUpgrader, 'check_available_versions')
    @patch.object(PANOSUpgrader, 'download_software')
    @patch.object(PANOSUpgrader, 'install_software')
    @patch.object(PANOSUpgrader, 'reboot')
    @patch.object(PANOSUpgrader, 'wait_for_reboot')
    def test_upgrade_to_version_success(self, mock_wait, mock_reboot, mock_install,
                                         mock_download, mock_check, mock_version,
                                         mock_disconnect, mock_connect, mock_get_path):
        # Initial version, then version after each step (2 steps in path)
        mock_version.side_effect = ["11.0.0", "11.1.0", "11.2.4"]
        mock_wait.return_value = True
        mock_get_path.return_value = ["11.1.0", "11.2.4"]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.upgrade_to_version("11.2.4")

        assert result is True

    @patch('src.panos_upgrade.get_upgrade_path')
    @patch.object(PANOSUpgrader, 'connect')
    @patch.object(PANOSUpgrader, 'disconnect')
    @patch.object(PANOSUpgrader, 'get_current_version')
    @patch.object(PANOSUpgrader, 'check_available_versions')
    @patch.object(PANOSUpgrader, 'download_software')
    @patch.object(PANOSUpgrader, 'install_software')
    @patch.object(PANOSUpgrader, 'reboot')
    @patch.object(PANOSUpgrader, 'wait_for_reboot')
    def test_upgrade_to_version_reboot_timeout(self, mock_wait, mock_reboot, mock_install,
                                                mock_download, mock_check, mock_version,
                                                mock_disconnect, mock_connect, mock_get_path):
        """Test when firewall doesn't come back after reboot."""
        mock_version.return_value = "11.0.0"
        mock_wait.return_value = False  # Reboot timeout
        mock_get_path.return_value = ["11.1.0"]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.upgrade_to_version("11.1.0")

        assert result is False

    @patch('src.panos_upgrade.get_upgrade_path')
    @patch.object(PANOSUpgrader, 'connect')
    @patch.object(PANOSUpgrader, 'disconnect')
    @patch.object(PANOSUpgrader, 'get_current_version')
    @patch.object(PANOSUpgrader, 'check_available_versions')
    @patch.object(PANOSUpgrader, 'download_software')
    @patch.object(PANOSUpgrader, 'install_software')
    @patch.object(PANOSUpgrader, 'reboot')
    @patch.object(PANOSUpgrader, 'wait_for_reboot')
    def test_upgrade_to_version_version_mismatch(self, mock_wait, mock_reboot, mock_install,
                                                  mock_download, mock_check, mock_version,
                                                  mock_disconnect, mock_connect, mock_get_path):
        """Test when version after upgrade doesn't match expected."""
        # Returns 11.0.0 initially, then 11.0.5 after upgrade (expected 11.1.x)
        mock_version.side_effect = ["11.0.0", "11.0.5"]
        mock_wait.return_value = True
        mock_get_path.return_value = ["11.1.0"]

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.upgrade_to_version("11.1.0")

        # Should still return True but log a warning
        assert result is True

    @patch.object(PANOSUpgrader, 'connect')
    @patch.object(PANOSUpgrader, 'disconnect')
    def test_upgrade_to_version_exception(self, mock_disconnect, mock_connect):
        mock_connect.side_effect = Exception("Connection failed")

        upgrader = PANOSUpgrader("10.0.0.1", "admin", "password")
        result = upgrader.upgrade_to_version("11.2.4")

        assert result is False
        mock_disconnect.assert_called()


class TestUpgradeFirewall:
    """Tests for upgrade_firewall function."""

    @patch('src.panos_upgrade.PANOSUpgrader')
    def test_upgrade_firewall_success(self, mock_upgrader_class):
        mock_upgrader = Mock()
        mock_upgrader.upgrade_to_version.return_value = True
        mock_upgrader_class.return_value = mock_upgrader

        result = upgrade_firewall("10.0.0.1", "admin", "password", "11.2.4")

        assert result is True

    @patch('src.panos_upgrade.PANOSUpgrader')
    def test_upgrade_firewall_with_callback(self, mock_upgrader_class):
        mock_upgrader = Mock()
        mock_upgrader.upgrade_to_version.return_value = True
        mock_upgrader_class.return_value = mock_upgrader

        callback = Mock()
        result = upgrade_firewall("10.0.0.1", "admin", "password", "11.2.4",
                                   progress_callback=callback)

        assert result is True
        mock_upgrader_class.assert_called_with("10.0.0.1", "admin", "password", callback)
