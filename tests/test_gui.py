"""Tests for src/gui.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk

from src.gui import PASSHPrepGUI, SetupConfig


class TestSetupConfig:
    """Tests for SetupConfig dataclass."""

    def test_create_config(self):
        config = SetupConfig(
            new_ip="10.0.0.1",
            new_password="Password123",
            target_version="11.2.4",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8", "8.8.4.4"]
        )

        assert config.new_ip == "10.0.0.1"
        assert config.new_password == "Password123"
        assert config.target_version == "11.2.4"
        assert config.subnet_mask == "255.255.255.0"
        assert config.gateway == "10.0.0.254"
        assert config.dns_servers == ["8.8.8.8", "8.8.4.4"]

    def test_config_with_single_dns(self):
        config = SetupConfig(
            new_ip="10.0.0.1",
            new_password="Password123",
            target_version="11.2.4",
            subnet_mask="255.255.255.0",
            gateway="10.0.0.254",
            dns_servers=["8.8.8.8"]
        )

        assert len(config.dns_servers) == 1


class TestPASSHPrepGUI:
    """Tests for PASSHPrepGUI class."""

    def test_init(self):
        gui = PASSHPrepGUI()
        assert gui.on_start is None
        assert gui.root is None
        assert gui.running is False
        assert gui.cancelled is False

    def test_init_with_callback(self):
        callback = Mock()
        gui = PASSHPrepGUI(on_start=callback)
        assert gui.on_start == callback

    @patch('src.gui.tk.DoubleVar')
    @patch('src.gui.tk.StringVar')
    @patch('src.gui.ttk')
    @patch('src.gui.tk.Tk')
    @patch('src.gui.detect_network_settings')
    def test_create_window(self, mock_detect, mock_tk, mock_ttk, mock_stringvar, mock_doublevar):
        mock_root = MagicMock()
        mock_root.winfo_width.return_value = 450
        mock_root.winfo_height.return_value = 400
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tk.return_value = mock_root

        # Mock StringVar to return mock objects with get/set methods
        def make_stringvar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = ""
            return var
        mock_stringvar.side_effect = make_stringvar

        def make_doublevar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = 0.0
            return var
        mock_doublevar.side_effect = make_doublevar

        mock_detect.return_value = Mock(
            subnet_mask="255.255.255.0",
            gateway="192.168.1.254",
            dns_servers=["8.8.8.8", "8.8.4.4"]
        )

        gui = PASSHPrepGUI()
        result = gui.create_window()

        assert result == mock_root
        mock_root.title.assert_called()

    @patch('src.gui.tk.DoubleVar')
    @patch('src.gui.tk.StringVar')
    @patch('src.gui.ttk')
    @patch('src.gui.tk.Tk')
    @patch('src.gui.detect_network_settings')
    def test_detect_network_populates_fields(self, mock_detect, mock_tk, mock_ttk, mock_stringvar, mock_doublevar):
        mock_root = MagicMock()
        mock_root.winfo_width.return_value = 450
        mock_root.winfo_height.return_value = 400
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tk.return_value = mock_root

        # Track what values were set
        stored_values = {}
        def make_stringvar(*args, **kwargs):
            var = MagicMock()
            var._value = ""
            def setter(val):
                var._value = val
            def getter():
                return var._value
            var.set.side_effect = setter
            var.get.side_effect = getter
            return var
        mock_stringvar.side_effect = make_stringvar

        def make_doublevar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = 0.0
            return var
        mock_doublevar.side_effect = make_doublevar

        mock_detect.return_value = Mock(
            subnet_mask="255.255.0.0",
            gateway="10.0.0.1",
            dns_servers=["1.1.1.1", "1.0.0.1"]
        )

        gui = PASSHPrepGUI()
        gui.create_window()

        # Check that the values were set via the mock
        gui.subnet_var.set.assert_called()
        gui.gateway_var.set.assert_called()
        gui.dns1_var.set.assert_called()
        gui.dns2_var.set.assert_called()

    @patch('src.gui.tk.DoubleVar')
    @patch('src.gui.tk.StringVar')
    @patch('src.gui.ttk')
    @patch('src.gui.tk.Tk')
    @patch('src.gui.detect_network_settings')
    def test_detect_network_single_dns(self, mock_detect, mock_tk, mock_ttk, mock_stringvar, mock_doublevar):
        mock_root = MagicMock()
        mock_root.winfo_width.return_value = 450
        mock_root.winfo_height.return_value = 400
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tk.return_value = mock_root

        def make_stringvar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = ""
            return var
        mock_stringvar.side_effect = make_stringvar

        def make_doublevar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = 0.0
            return var
        mock_doublevar.side_effect = make_doublevar

        mock_detect.return_value = Mock(
            subnet_mask="255.255.255.0",
            gateway="192.168.1.1",
            dns_servers=["8.8.8.8"]
        )

        gui = PASSHPrepGUI()
        gui.create_window()

        gui.dns1_var.set.assert_called()

    @patch('src.gui.tk.DoubleVar')
    @patch('src.gui.tk.StringVar')
    @patch('src.gui.ttk')
    @patch('src.gui.tk.Tk')
    @patch('src.gui.detect_network_settings')
    def test_detect_network_no_dns(self, mock_detect, mock_tk, mock_ttk, mock_stringvar, mock_doublevar):
        mock_root = MagicMock()
        mock_root.winfo_width.return_value = 450
        mock_root.winfo_height.return_value = 400
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tk.return_value = mock_root

        def make_stringvar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = ""
            return var
        mock_stringvar.side_effect = make_stringvar

        def make_doublevar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = 0.0
            return var
        mock_doublevar.side_effect = make_doublevar

        mock_detect.return_value = Mock(
            subnet_mask="255.255.255.0",
            gateway="192.168.1.1",
            dns_servers=[]
        )

        gui = PASSHPrepGUI()
        gui.create_window()
        # Should use defaults - no error raised

    @patch('src.gui.tk.DoubleVar')
    @patch('src.gui.tk.StringVar')
    @patch('src.gui.ttk')
    @patch('src.gui.tk.Tk')
    @patch('src.gui.detect_network_settings')
    def test_detect_network_returns_none(self, mock_detect, mock_tk, mock_ttk, mock_stringvar, mock_doublevar):
        mock_root = MagicMock()
        mock_root.winfo_width.return_value = 450
        mock_root.winfo_height.return_value = 400
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tk.return_value = mock_root
        mock_detect.return_value = None

        def make_stringvar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = ""
            return var
        mock_stringvar.side_effect = make_stringvar

        def make_doublevar(*args, **kwargs):
            var = MagicMock()
            var.get.return_value = 0.0
            return var
        mock_doublevar.side_effect = make_doublevar

        gui = PASSHPrepGUI()
        gui.create_window()  # Should not raise

    def test_validate_inputs_missing_ip(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = ""

        error = gui._validate_inputs()
        assert "IP is required" in error

    def test_validate_inputs_invalid_ip(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "invalid"

        error = gui._validate_inputs()
        assert "Invalid IP" in error

    def test_validate_inputs_missing_password(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = ""

        error = gui._validate_inputs()
        assert "password is required" in error

    def test_validate_inputs_invalid_password(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "weak"

        error = gui._validate_inputs()
        assert error is not None

    def test_validate_inputs_missing_version(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = ""

        error = gui._validate_inputs()
        assert "version is required" in error

    def test_validate_inputs_invalid_version(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "invalid"

        error = gui._validate_inputs()
        assert "version format" in error.lower() or error is not None

    def test_validate_inputs_invalid_subnet(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "invalid"

        error = gui._validate_inputs()
        assert "subnet" in error.lower()

    def test_validate_inputs_invalid_gateway(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "invalid"

        error = gui._validate_inputs()
        assert "gateway" in error.lower()

    def test_validate_inputs_invalid_dns1(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = "invalid"
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = ""

        error = gui._validate_inputs()
        assert "DNS 1" in error

    def test_validate_inputs_invalid_dns2(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = "8.8.8.8"
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = "invalid"

        error = gui._validate_inputs()
        assert "DNS 2" in error

    def test_validate_inputs_success(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = "8.8.8.8"
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = "8.8.4.4"

        error = gui._validate_inputs()
        assert error is None

    def test_validate_inputs_empty_dns_ok(self):
        gui = PASSHPrepGUI()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = ""
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = ""

        error = gui._validate_inputs()
        assert error is None

    def test_update_status(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()
        gui.status_var = Mock()

        gui.update_status("Test status")
        gui.root.after.assert_called()

    def test_update_status_no_root(self):
        gui = PASSHPrepGUI()
        gui.update_status("Test")  # Should not raise

    def test_update_progress(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()
        gui.progress_var = Mock()

        gui.update_progress(50)
        gui.root.after.assert_called()

    def test_update_progress_no_root(self):
        gui = PASSHPrepGUI()
        gui.update_progress(50)  # Should not raise

    def test_show_error(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()

        gui.show_error("Error", "Message")
        gui.root.after.assert_called()

    def test_show_error_no_root(self):
        gui = PASSHPrepGUI()
        gui.show_error("Error", "Message")  # Should not raise

    def test_show_info(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()

        gui.show_info("Info", "Message")
        gui.root.after.assert_called()

    def test_show_info_no_root(self):
        gui = PASSHPrepGUI()
        gui.show_info("Info", "Message")  # Should not raise

    def test_complete_success(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()
        gui.status_var = Mock()
        gui.progress_var = Mock()

        gui.complete(success=True)

        assert gui.running is False
        gui.root.after.assert_called()

    def test_complete_failure(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()
        gui.status_var = Mock()
        gui.progress_var = Mock()

        gui.complete(success=False)

        assert gui.running is False

    def test_is_cancelled(self):
        gui = PASSHPrepGUI()
        gui.cancelled = False
        assert gui.is_cancelled() is False

        gui.cancelled = True
        assert gui.is_cancelled() is True

    def test_run(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()

        gui.run()
        gui.root.mainloop.assert_called()

    def test_run_no_root(self):
        gui = PASSHPrepGUI()
        gui.run()  # Should not raise

    def test_quit(self):
        gui = PASSHPrepGUI()
        gui.root = Mock()

        gui.quit()
        gui.root.quit.assert_called()
        gui.root.destroy.assert_called()

    def test_quit_no_root(self):
        gui = PASSHPrepGUI()
        gui.quit()  # Should not raise

    @patch('src.gui.messagebox')
    def test_on_ok_when_running(self, mock_msgbox):
        gui = PASSHPrepGUI()
        gui.running = True

        gui._on_ok()
        mock_msgbox.showerror.assert_not_called()

    @patch('src.gui.messagebox')
    def test_on_ok_validation_error(self, mock_msgbox):
        gui = PASSHPrepGUI()
        gui.running = False
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = ""

        gui._on_ok()
        mock_msgbox.showerror.assert_called()

    @patch('src.gui.messagebox')
    def test_on_ok_user_cancels_confirm(self, mock_msgbox):
        mock_msgbox.askyesno.return_value = False

        gui = PASSHPrepGUI()
        gui.running = False
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = "8.8.8.8"
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = ""

        gui._on_ok()

        assert gui.running is False

    @patch('src.gui.messagebox')
    def test_on_ok_success(self, mock_msgbox):
        mock_msgbox.askyesno.return_value = True

        callback = Mock()
        gui = PASSHPrepGUI(on_start=callback)
        gui.running = False
        gui.root = MagicMock()
        gui.root.winfo_children.return_value = []
        gui.cancel_button = Mock()
        gui.new_ip_var = Mock()
        gui.new_ip_var.get.return_value = "10.0.0.1"
        gui.password_var = Mock()
        gui.password_var.get.return_value = "Password123"
        gui.version_var = Mock()
        gui.version_var.get.return_value = "11.2.4"
        gui.subnet_var = Mock()
        gui.subnet_var.get.return_value = "255.255.255.0"
        gui.gateway_var = Mock()
        gui.gateway_var.get.return_value = "10.0.0.254"
        gui.dns1_var = Mock()
        gui.dns1_var.get.return_value = "8.8.8.8"
        gui.dns2_var = Mock()
        gui.dns2_var.get.return_value = "8.8.4.4"

        gui._on_ok()

        assert gui.running is True
        callback.assert_called()

    @patch('src.gui.messagebox')
    def test_on_cancel_not_running(self, mock_msgbox):
        gui = PASSHPrepGUI()
        gui.running = False
        gui.root = Mock()

        gui._on_cancel()
        gui.root.quit.assert_called()

    @patch('src.gui.messagebox')
    def test_on_cancel_running_user_confirms(self, mock_msgbox):
        mock_msgbox.askyesno.return_value = True

        gui = PASSHPrepGUI()
        gui.running = True
        gui.root = Mock()
        gui.status_var = Mock()

        gui._on_cancel()

        assert gui.cancelled is True

    @patch('src.gui.messagebox')
    def test_on_cancel_running_user_declines(self, mock_msgbox):
        mock_msgbox.askyesno.return_value = False

        gui = PASSHPrepGUI()
        gui.running = True
        gui.root = Mock()

        gui._on_cancel()

        assert gui.cancelled is False
