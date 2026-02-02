"""Tests for src/firewall_config.py"""

import pytest
from unittest.mock import Mock, patch

from src.firewall_config import FirewallConfigurator, configure_firewall


class TestFirewallConfigurator:
    """Tests for FirewallConfigurator class."""

    def test_init(self):
        mock_client = Mock()
        configurator = FirewallConfigurator(mock_client)
        assert configurator.client == mock_client
        assert configurator.progress_callback is None

    def test_init_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        configurator = FirewallConfigurator(mock_client, progress_callback=callback)
        assert configurator.progress_callback == callback

    def test_update_progress_with_callback(self):
        mock_client = Mock()
        callback = Mock()
        configurator = FirewallConfigurator(mock_client, progress_callback=callback)

        configurator._update_progress("Test message")
        callback.assert_called_with("Test message")

    def test_update_progress_without_callback(self):
        mock_client = Mock()
        configurator = FirewallConfigurator(mock_client)
        configurator._update_progress("Test message")  # Should not raise

    def test_set_management_ip(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        mock_client.enter_configure_mode.return_value = "Entering config mode"
        mock_client.exit_configure_mode.return_value = "Exiting config mode"
        configurator = FirewallConfigurator(mock_client)

        configurator.set_management_ip("10.0.0.1", "255.255.255.0", "10.0.0.254")

        # Should enter config, set 3 commands, exit
        mock_client.enter_configure_mode.assert_called()
        mock_client.exit_configure_mode.assert_called()

    def test_set_management_ip_error(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "error: invalid syntax"
        configurator = FirewallConfigurator(mock_client)

        with pytest.raises(RuntimeError):
            configurator.set_management_ip("invalid", "255.255.255.0", "10.0.0.254")

    def test_set_dns_servers_primary_only(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        configurator = FirewallConfigurator(mock_client)

        configurator.set_dns_servers("8.8.8.8")

        mock_client.enter_configure_mode.assert_called()
        mock_client.exit_configure_mode.assert_called()

    def test_set_dns_servers_primary_and_secondary(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        configurator = FirewallConfigurator(mock_client)

        configurator.set_dns_servers("8.8.8.8", "8.8.4.4")

        assert mock_client.send_command_timing.call_count >= 2

    def test_set_dns_servers_error(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "error: failed"
        configurator = FirewallConfigurator(mock_client)

        with pytest.raises(RuntimeError):
            configurator.set_dns_servers("invalid")

    def test_set_dns_servers_secondary_error(self):
        mock_client = Mock()
        mock_client.enter_configure_mode.return_value = "Entering config mode"
        mock_client.exit_configure_mode.return_value = "Exiting config mode"
        # First call succeeds (primary DNS), second fails (secondary DNS)
        mock_client.send_command_timing.side_effect = [
            "OK",  # primary DNS
            "error: invalid secondary",  # secondary DNS
        ]
        configurator = FirewallConfigurator(mock_client)

        with pytest.raises(RuntimeError, match="secondary DNS"):
            configurator.set_dns_servers("8.8.8.8", "invalid")

    def test_change_admin_password(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        configurator = FirewallConfigurator(mock_client)

        configurator.change_admin_password("NewPassword123")

        mock_client.enter_configure_mode.assert_called()
        mock_client.exit_configure_mode.assert_called()

    def test_change_admin_password_error(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "error: password invalid"
        configurator = FirewallConfigurator(mock_client)

        with pytest.raises(RuntimeError):
            configurator.change_admin_password("bad")

    def test_commit_configuration_success(self):
        mock_client = Mock()
        mock_client.commit.return_value = "Configuration committed successfully"
        configurator = FirewallConfigurator(mock_client)

        configurator.commit_configuration()

        mock_client.commit.assert_called_once()

    def test_commit_configuration_other_message(self):
        mock_client = Mock()
        mock_client.commit.return_value = "Commit completed"
        configurator = FirewallConfigurator(mock_client)

        configurator.commit_configuration()  # Should not raise

    def test_perform_initial_setup(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        mock_client.commit.return_value = "Configuration committed successfully"
        configurator = FirewallConfigurator(mock_client)

        configurator.perform_initial_setup(
            new_ip="10.0.0.1",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8", "8.8.4.4"],
            new_password="NewPassword123"
        )

        mock_client.commit.assert_called()

    def test_perform_initial_setup_single_dns(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        mock_client.commit.return_value = "success"
        configurator = FirewallConfigurator(mock_client)

        configurator.perform_initial_setup(
            new_ip="10.0.0.1",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8"],
            new_password="NewPassword123"
        )

    def test_perform_initial_setup_no_dns(self):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        mock_client.commit.return_value = "success"
        configurator = FirewallConfigurator(mock_client)

        configurator.perform_initial_setup(
            new_ip="10.0.0.1",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=[],
            new_password="NewPassword123"
        )


class TestConfigureFirewall:
    """Tests for configure_firewall function."""

    @patch('src.firewall_config.PANOSSSHClient')
    @patch('src.firewall_config.FirewallConfigurator')
    def test_configure_firewall_success(self, mock_configurator_class, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_configurator = Mock()
        mock_configurator_class.return_value = mock_configurator

        result = configure_firewall(
            host="192.168.1.1",
            new_ip="10.0.0.1",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8"],
            new_password="Password123"
        )

        assert result is True
        mock_client.connect.assert_called()
        mock_client.disconnect.assert_called()

    @patch('src.firewall_config.PANOSSSHClient')
    def test_configure_firewall_with_callback(self, mock_client_class):
        mock_client = Mock()
        mock_client.send_command_timing.return_value = "OK"
        mock_client.commit.return_value = "success"
        mock_client_class.return_value = mock_client

        callback = Mock()
        result = configure_firewall(
            host="192.168.1.1",
            new_ip="10.0.0.1",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8"],
            new_password="Password123",
            progress_callback=callback
        )

        assert result is True
        callback.assert_called()

    @patch('src.firewall_config.PANOSSSHClient')
    def test_configure_firewall_disconnect_on_exception(self, mock_client_class):
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        with pytest.raises(Exception):
            configure_firewall(
                host="192.168.1.1",
                new_ip="10.0.0.1",
                subnet_mask="255.255.255.0",
                gateway="10.0.0.254",
                dns_servers=["8.8.8.8"],
                new_password="Password123"
            )

        mock_client.disconnect.assert_called()
