"""Tests for src/ssh_client.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import socket

from src.ssh_client import PANOSSSHClient, wait_for_ssh


class TestPANOSSSHClient:
    """Tests for PANOSSSHClient class."""

    def test_init(self):
        client = PANOSSSHClient("192.168.1.1", "admin", "password", port=22, timeout=60)
        assert client.host == "192.168.1.1"
        assert client.username == "admin"
        assert client.password == "password"
        assert client.port == 22
        assert client.timeout == 60
        assert client.connection is None

    def test_init_defaults(self):
        client = PANOSSSHClient("10.0.0.1")
        assert client.host == "10.0.0.1"
        assert client.username == "admin"
        assert client.password == "admin"
        assert client.port == 22

    @patch('src.ssh_client.ConnectHandler')
    def test_connect_success(self, mock_connect_handler):
        mock_connection = Mock()
        mock_connect_handler.return_value = mock_connection

        client = PANOSSSHClient("192.168.1.1", "admin", "admin")
        client.connect()

        mock_connect_handler.assert_called_once()
        assert client.connection == mock_connection

    @patch('src.ssh_client.ConnectHandler')
    def test_connect_authentication_failure(self, mock_connect_handler):
        from netmiko.exceptions import NetmikoAuthenticationException
        mock_connect_handler.side_effect = NetmikoAuthenticationException("Auth failed")

        client = PANOSSSHClient("192.168.1.1", "admin", "wrong")
        with pytest.raises(NetmikoAuthenticationException):
            client.connect()

    @patch('src.ssh_client.ConnectHandler')
    def test_connect_timeout(self, mock_connect_handler):
        from netmiko.exceptions import NetmikoTimeoutException
        mock_connect_handler.side_effect = NetmikoTimeoutException("Timeout")

        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(NetmikoTimeoutException):
            client.connect()

    @patch('src.ssh_client.ConnectHandler')
    def test_connect_generic_exception(self, mock_connect_handler):
        mock_connect_handler.side_effect = Exception("Connection error")

        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(Exception):
            client.connect()

    def test_disconnect_when_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        mock_conn = Mock()
        client.connection = mock_conn

        client.disconnect()

        mock_conn.disconnect.assert_called_once()
        assert client.connection is None

    def test_disconnect_when_not_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        client.disconnect()  # Should not raise

    def test_disconnect_with_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.disconnect.side_effect = Exception("Error")

        client.disconnect()  # Should not raise
        assert client.connection is None

    def test_is_connected_true(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.is_alive.return_value = True

        assert client.is_connected() is True

    def test_is_connected_false_no_connection(self):
        client = PANOSSSHClient("192.168.1.1")
        assert client.is_connected() is False

    def test_is_connected_false_dead_connection(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.is_alive.return_value = False

        assert client.is_connected() is False

    def test_is_connected_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.is_alive.side_effect = Exception("Error")

        assert client.is_connected() is False

    def test_send_command_not_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(RuntimeError, match="Not connected"):
            client.send_command("show system info")

    def test_send_command_success(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.return_value = "output"

        result = client.send_command("show clock")
        assert result == "output"

    def test_send_command_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.side_effect = Exception("Command failed")

        with pytest.raises(Exception):
            client.send_command("show clock")

    def test_send_command_timing_not_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(RuntimeError, match="Not connected"):
            client.send_command_timing("configure")

    def test_send_command_timing_success(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.return_value = "output"

        result = client.send_command_timing("configure")
        assert result == "output"

    def test_send_command_timing_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.side_effect = Exception("Error")

        with pytest.raises(Exception):
            client.send_command_timing("configure")

    def test_send_config_command(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.return_value = "OK"

        result = client.send_config_command("set deviceconfig system ip-address 10.0.0.1")

        assert client.connection.send_command_timing.call_count == 3  # configure, command, exit

    def test_send_config_command_not_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(RuntimeError, match="Not connected"):
            client.send_config_command("set something")

    def test_send_config_command_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.side_effect = Exception("Error")

        with pytest.raises(Exception):
            client.send_config_command("set something")

    def test_send_config_set(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_config_set.return_value = "OK"

        result = client.send_config_set(["cmd1", "cmd2"])
        assert result == "OK"

    def test_send_config_set_not_connected(self):
        client = PANOSSSHClient("192.168.1.1")
        with pytest.raises(RuntimeError, match="Not connected"):
            client.send_config_set(["cmd1"])

    def test_send_config_set_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_config_set.side_effect = Exception("Error")

        with pytest.raises(Exception):
            client.send_config_set(["cmd1"])

    def test_enter_configure_mode(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.return_value = "Entering configuration mode"

        result = client.enter_configure_mode()
        client.connection.send_command_timing.assert_called_with("configure", delay_factor=2.0)

    def test_exit_configure_mode(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command_timing.return_value = "Exiting configuration mode"

        result = client.exit_configure_mode()
        client.connection.send_command_timing.assert_called_with("exit", delay_factor=2.0)

    def test_commit_success(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.return_value = "Configuration committed successfully"

        result = client.commit()
        assert "successfully" in result.lower()

    def test_commit_failure(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.return_value = "Commit failed: validation error"

        with pytest.raises(RuntimeError, match="Commit failed"):
            client.commit()

    def test_commit_exception(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.side_effect = Exception("Error")

        with pytest.raises(Exception):
            client.commit()

    def test_get_system_info(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.return_value = """hostname: firewall1
sw-version: 11.2.4
model: PA-440"""

        info = client.get_system_info()
        assert info['hostname'] == 'firewall1'
        assert info['sw-version'] == '11.2.4'
        assert info['model'] == 'PA-440'

    def test_get_panos_version(self):
        client = PANOSSSHClient("192.168.1.1")
        client.connection = Mock()
        client.connection.send_command.return_value = "sw-version: 11.2.4"

        version = client.get_panos_version()
        assert version == "11.2.4"


class TestWaitForSSH:
    """Tests for wait_for_ssh function."""

    @patch('src.ssh_client.PANOSSSHClient')
    @patch('socket.socket')
    @patch('time.sleep')
    def test_wait_for_ssh_success_immediate(self, mock_sleep, mock_socket, mock_client_class):
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = wait_for_ssh("192.168.1.1", timeout=60, poll_interval=5)

        assert result is True

    @patch('src.ssh_client.PANOSSSHClient')
    @patch('socket.socket')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_ssh_timeout(self, mock_time, mock_sleep, mock_socket, mock_client_class):
        # Simulate timeout
        mock_time.side_effect = [0, 0, 100, 200, 300]  # Exceed timeout

        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # Port not open
        mock_socket.return_value = mock_sock

        result = wait_for_ssh("192.168.1.1", timeout=10, poll_interval=5)

        assert result is False

    @patch('src.ssh_client.PANOSSSHClient')
    @patch('socket.socket')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_ssh_with_callback(self, mock_time, mock_sleep, mock_socket, mock_client_class):
        mock_time.side_effect = [0, 5, 10]

        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        callback = Mock()
        result = wait_for_ssh("192.168.1.1", timeout=60, progress_callback=callback)

        assert result is True
        callback.assert_called()

    @patch('socket.socket')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_ssh_socket_exception(self, mock_time, mock_sleep, mock_socket):
        # Use iterator function to provide values - logging also uses time.time()
        call_count = [0]
        def time_side_effect():
            call_count[0] += 1
            if call_count[0] <= 4:
                return 0  # Start time and first few checks
            return 100  # Eventually exceed timeout
        mock_time.side_effect = time_side_effect

        mock_sock = Mock()
        mock_sock.connect_ex.side_effect = Exception("Network error")
        mock_socket.return_value = mock_sock

        result = wait_for_ssh("192.168.1.1", timeout=10, poll_interval=5)

        assert result is False

    @patch('src.ssh_client.PANOSSSHClient')
    @patch('socket.socket')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_ssh_connection_fails_then_succeeds(self, mock_time, mock_sleep, mock_socket, mock_client_class):
        # Provide enough values for all time.time() calls
        mock_time.side_effect = [0, 0, 5, 5, 10, 10, 15]

        mock_sock = Mock()
        # First call port not open, second call port open
        mock_sock.connect_ex.side_effect = [1, 0]
        mock_socket.return_value = mock_sock

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = wait_for_ssh("192.168.1.1", timeout=60, poll_interval=5)

        assert result is True

    @patch('src.ssh_client.PANOSSSHClient')
    @patch('socket.socket')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_ssh_port_open_but_ssh_fails(self, mock_time, mock_sleep, mock_socket, mock_client_class):
        """Test when port is open but SSH connection fails."""
        # Use function that returns incrementing time values
        call_count = [0]
        def time_side_effect():
            call_count[0] += 1
            if call_count[0] <= 4:
                return 0
            return 100  # Exceed timeout
        mock_time.side_effect = time_side_effect

        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Port is open
        mock_socket.return_value = mock_sock

        mock_client = Mock()
        mock_client.connect.side_effect = Exception("SSH authentication failed")
        mock_client_class.return_value = mock_client

        result = wait_for_ssh("192.168.1.1", timeout=10, poll_interval=5)

        assert result is False
