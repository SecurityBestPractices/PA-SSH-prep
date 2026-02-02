"""Tests for src/content_update.py"""

import pytest
from unittest.mock import Mock, patch

from src.content_update import ContentUpdater, update_firewall_content


class TestContentUpdater:
    """Tests for ContentUpdater class."""

    def test_init(self):
        mock_client = Mock()
        updater = ContentUpdater(mock_client)
        assert updater.client == mock_client
        assert updater.progress_callback is None

    def test_init_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        updater = ContentUpdater(mock_client, progress_callback=callback)
        assert updater.progress_callback == callback

    def test_update_progress_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        updater = ContentUpdater(mock_client, progress_callback=callback)

        updater._update_progress("Downloading...")
        callback.assert_called_with("Downloading...")

    def test_update_progress_without_callback(self):
        mock_client = Mock()
        updater = ContentUpdater(mock_client)
        updater._update_progress("Test")  # Should not raise

    def test_check_content_version(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Content version: 1234-5678"
        updater = ContentUpdater(mock_client)

        result = updater.check_content_version()
        assert "1234-5678" in result

    def test_download_latest_content_job_enqueued(self):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "download job enqueued",
            "download complete",
        ]
        updater = ContentUpdater(mock_client)

        with patch.object(updater, '_wait_for_download_completion', return_value="done"):
            result = updater.download_latest_content()

    def test_download_latest_content_already_downloaded(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Content already downloaded"
        updater = ContentUpdater(mock_client)

        result = updater.download_latest_content()
        assert "already downloaded" in result.lower()

    def test_download_latest_content_success(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Download succeeded"
        updater = ContentUpdater(mock_client)

        result = updater.download_latest_content()

    def test_download_latest_content_failed(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Download failed: error"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="failed"):
            updater.download_latest_content()

    def test_download_latest_content_exception(self):
        mock_client = Mock()
        mock_client.send_command.side_effect = Exception("Network error")
        updater = ContentUpdater(mock_client)

        with pytest.raises(Exception):
            updater.download_latest_content()

    def test_download_latest_content_unknown_response(self):
        """Test when response doesn't match any known pattern - returns raw output."""
        mock_client = Mock()
        mock_client.send_command.return_value = "some unexpected response"
        updater = ContentUpdater(mock_client)

        result = updater.download_latest_content()
        assert result == "some unexpected response"

    @patch('src.content_update.time.sleep')
    def test_wait_for_download_completion_success(self, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "currently downloading 50%",
            "download complete",
        ]
        updater = ContentUpdater(mock_client)

        result = updater._wait_for_download_completion(timeout=60)

    @patch('src.content_update.time.sleep')
    def test_wait_for_download_completion_with_percentage(self, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "currently downloading 25%",
            "currently downloading 75%",
            "download complete",
        ]
        updater = ContentUpdater(mock_client)
        callback = Mock()
        updater.progress_callback = callback

        updater._wait_for_download_completion(timeout=120)
        assert callback.call_count >= 2

    @patch('src.content_update.time.sleep')
    def test_wait_for_download_completion_failed(self, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.return_value = "download failed"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="failed"):
            updater._wait_for_download_completion(timeout=30)

    @patch('src.content_update.time.sleep')
    @patch('src.content_update.time.time')
    def test_wait_for_download_completion_timeout(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 100, 200]  # Exceed timeout
        mock_client = Mock()
        mock_client.send_command.return_value = "currently downloading"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="timed out"):
            updater._wait_for_download_completion(timeout=10)

    @patch('src.content_update.time.sleep')
    @patch('src.content_update.time.time')
    def test_wait_for_download_version_ready(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 5, 10]
        mock_client = Mock()
        mock_client.send_command.return_value = "8901-1234  yes"
        updater = ContentUpdater(mock_client)

        result = updater._wait_for_download_completion(timeout=60)

    def test_get_downloadable_version(self):
        mock_client = Mock()
        updater = ContentUpdater(mock_client)

        result = updater._get_downloadable_version("8901-1234  yes downloaded")
        assert result == "8901-1234"

    def test_get_downloadable_version_none(self):
        mock_client = Mock()
        updater = ContentUpdater(mock_client)

        result = updater._get_downloadable_version("no versions available")
        assert result is None

    def test_install_latest_content_job_enqueued(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "install job enqueued"
        updater = ContentUpdater(mock_client)

        with patch.object(updater, '_wait_for_install_completion', return_value="done"):
            updater.install_latest_content()

    def test_install_latest_content_success(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Content installed successfully"
        updater = ContentUpdater(mock_client)

        result = updater.install_latest_content()

    def test_install_latest_content_already_installed(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Content already installed"
        updater = ContentUpdater(mock_client)

        result = updater.install_latest_content()

    def test_install_latest_content_failed(self):
        mock_client = Mock()
        mock_client.send_command.return_value = "Installation failed"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="failed"):
            updater.install_latest_content()

    def test_install_latest_content_exception(self):
        mock_client = Mock()
        mock_client.send_command.side_effect = Exception("Error")
        updater = ContentUpdater(mock_client)

        with pytest.raises(Exception):
            updater.install_latest_content()

    @patch('src.content_update.time.sleep')
    def test_wait_for_install_completion_success(self, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "currently installing",
            "install complete",
        ]
        updater = ContentUpdater(mock_client)

        updater._wait_for_install_completion(timeout=60)

    @patch('src.content_update.time.sleep')
    def test_wait_for_install_completion_failed(self, mock_sleep):
        mock_client = Mock()
        mock_client.send_command.return_value = "installation failed"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="failed"):
            updater._wait_for_install_completion(timeout=30)

    @patch('src.content_update.time.sleep')
    @patch('src.content_update.time.time')
    def test_wait_for_install_completion_timeout(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 100, 200]
        mock_client = Mock()
        mock_client.send_command.return_value = "installing"
        updater = ContentUpdater(mock_client)

        with pytest.raises(RuntimeError, match="timed out"):
            updater._wait_for_install_completion(timeout=10)

    @patch('src.content_update.time.sleep')
    @patch('src.content_update.time.time')
    def test_wait_for_install_completion_version_current(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 5]
        mock_client = Mock()
        mock_client.send_command.return_value = "version 1234 current"
        updater = ContentUpdater(mock_client)

        updater._wait_for_install_completion(timeout=60)

    def test_update_content(self):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "download succeeded",
            "install succeeded",
        ]
        updater = ContentUpdater(mock_client)

        updater.update_content()


class TestUpdateFirewallContent:
    """Tests for update_firewall_content function."""

    @patch('src.content_update.PANOSSSHClient')
    def test_update_firewall_content_success(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "download succeeded",
            "install succeeded",
        ]
        mock_client_class.return_value = mock_client

        result = update_firewall_content("10.0.0.1", "admin", "password")

        assert result is True
        mock_client.connect.assert_called()
        mock_client.disconnect.assert_called()

    @patch('src.content_update.PANOSSSHClient')
    def test_update_firewall_content_with_callback(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command.side_effect = [
            "download succeeded",
            "install succeeded",
        ]
        mock_client_class.return_value = mock_client

        callback = Mock()
        result = update_firewall_content(
            "10.0.0.1", "admin", "password",
            progress_callback=callback
        )

        assert result is True
        callback.assert_called()

    @patch('src.content_update.PANOSSSHClient')
    def test_update_firewall_content_disconnect_on_exception(self, mock_client_class):
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        with pytest.raises(Exception):
            update_firewall_content("10.0.0.1", "admin", "password")

        mock_client.disconnect.assert_called()
