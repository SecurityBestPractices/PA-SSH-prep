"""Tests for src/main.py"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.main import FirewallSetupOrchestrator, run_setup, main
from src.gui import SetupConfig


@pytest.fixture
def mock_gui():
    """Create a mock GUI object."""
    gui = Mock()
    gui.is_cancelled.return_value = False
    return gui


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return SetupConfig(
        new_ip="10.0.0.1",
        new_password="Password123",
        target_version="11.2.4",
        subnet_mask="255.255.255.0",
        gateway="10.0.0.254",
        dns_servers=["8.8.8.8", "8.8.4.4"]
    )


class TestFirewallSetupOrchestrator:
    """Tests for FirewallSetupOrchestrator class."""

    def test_init(self, mock_gui, sample_config):
        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        assert orchestrator.gui == mock_gui
        assert orchestrator.config == sample_config
        assert orchestrator.current_phase == 0
        assert orchestrator.total_phases == 4

    def test_update_progress(self, mock_gui, sample_config):
        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        orchestrator._update_progress("Test message", 50)

        mock_gui.update_status.assert_called_with("Test message")
        mock_gui.update_progress.assert_called()

    def test_check_cancelled(self, mock_gui, sample_config):
        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)

        mock_gui.is_cancelled.return_value = False
        assert orchestrator._check_cancelled() is False

        mock_gui.is_cancelled.return_value = True
        assert orchestrator._check_cancelled() is True

    @patch('src.main.PANOSSSHClient')
    @patch('src.main.FirewallConfigurator')
    def test_phase1_initial_config_success(self, mock_configurator_class, mock_client_class, mock_gui, sample_config):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_configurator = Mock()
        mock_configurator_class.return_value = mock_configurator

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase1_initial_config()

        assert result is True
        mock_client.connect.assert_called()
        mock_client.disconnect.assert_called()

    @patch('src.main.PANOSSSHClient')
    def test_phase1_initial_config_failure(self, mock_client_class, mock_gui, sample_config):
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase1_initial_config()

        assert result is False
        mock_gui.show_error.assert_called()

    @patch('src.main.wait_for_ssh')
    @patch('src.main.PANOSSSHClient')
    @patch('src.main.LicenseManager')
    def test_phase2_licensing_success(self, mock_license_class, mock_client_class, mock_wait_ssh, mock_gui, sample_config):
        mock_wait_ssh.return_value = True

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_license_mgr = Mock()
        mock_license_class.return_value = mock_license_mgr

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase2_licensing()

        assert result is True

    @patch('src.main.wait_for_ssh')
    def test_phase2_licensing_ssh_timeout(self, mock_wait_ssh, mock_gui, sample_config):
        mock_wait_ssh.return_value = False

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase2_licensing()

        assert result is False
        mock_gui.show_error.assert_called()

    @patch('src.main.wait_for_ssh')
    @patch('src.main.PANOSSSHClient')
    def test_phase2_licensing_failure(self, mock_client_class, mock_wait_ssh, mock_gui, sample_config):
        mock_wait_ssh.return_value = True

        mock_client = Mock()
        mock_client.connect.side_effect = Exception("License error")
        mock_client_class.return_value = mock_client

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase2_licensing()

        assert result is False

    @patch('src.main.PANOSSSHClient')
    @patch('src.main.ContentUpdater')
    def test_phase3_content_update_success(self, mock_updater_class, mock_client_class, mock_gui, sample_config):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_updater = Mock()
        mock_updater_class.return_value = mock_updater

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase3_content_update()

        assert result is True

    @patch('src.main.PANOSSSHClient')
    def test_phase3_content_update_failure(self, mock_client_class, mock_gui, sample_config):
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Content error")
        mock_client_class.return_value = mock_client

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase3_content_update()

        assert result is False

    @patch('src.main.PANOSUpgrader')
    @patch('src.main.get_upgrade_path')
    def test_phase4_upgrade_no_upgrade_needed(self, mock_get_path, mock_upgrader_class, mock_gui, sample_config):
        mock_get_path.return_value = []

        mock_upgrader = Mock()
        mock_upgrader.get_current_version.return_value = "11.2.4"
        mock_upgrader_class.return_value = mock_upgrader

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase4_upgrade()

        assert result is True

    @patch('src.main.PANOSUpgrader')
    @patch('src.main.get_upgrade_path')
    def test_phase4_upgrade_success(self, mock_get_path, mock_upgrader_class, mock_gui, sample_config):
        mock_get_path.return_value = ["11.1.0", "11.2.0"]

        mock_upgrader = Mock()
        mock_upgrader.get_current_version.return_value = "11.0.0"
        mock_upgrader.wait_for_reboot.return_value = True
        mock_upgrader_class.return_value = mock_upgrader

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase4_upgrade()

        assert result is True

    @patch('src.main.PANOSUpgrader')
    @patch('src.main.get_upgrade_path')
    def test_phase4_upgrade_cancelled(self, mock_get_path, mock_upgrader_class, mock_gui, sample_config):
        mock_get_path.return_value = ["11.1.0"]
        mock_gui.is_cancelled.return_value = True

        mock_upgrader = Mock()
        mock_upgrader.get_current_version.return_value = "11.0.0"
        mock_upgrader_class.return_value = mock_upgrader

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase4_upgrade()

        assert result is False

    @patch('src.main.PANOSUpgrader')
    @patch('src.main.get_upgrade_path')
    def test_phase4_upgrade_reboot_timeout(self, mock_get_path, mock_upgrader_class, mock_gui, sample_config):
        mock_get_path.return_value = ["11.1.0"]

        mock_upgrader = Mock()
        mock_upgrader.get_current_version.return_value = "11.0.0"
        mock_upgrader.wait_for_reboot.return_value = False
        mock_upgrader_class.return_value = mock_upgrader

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase4_upgrade()

        assert result is False

    @patch('src.main.PANOSUpgrader')
    def test_phase4_upgrade_exception(self, mock_upgrader_class, mock_gui, sample_config):
        mock_upgrader = Mock()
        mock_upgrader.connect.side_effect = Exception("Upgrade error")
        mock_upgrader_class.return_value = mock_upgrader

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator._phase4_upgrade()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    @patch.object(FirewallSetupOrchestrator, '_phase3_content_update')
    @patch.object(FirewallSetupOrchestrator, '_phase4_upgrade')
    def test_run_success(self, mock_p4, mock_p3, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = True
        mock_p3.return_value = True
        mock_p4.return_value = True

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is True

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    def test_run_phase1_failure(self, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = False

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    def test_run_cancelled_after_phase1(self, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_gui.is_cancelled.return_value = True

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    def test_run_phase2_failure(self, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = False
        mock_gui.is_cancelled.return_value = False

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    def test_run_cancelled_after_phase2(self, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = True
        # Return False first (for after phase1), then True (for after phase2)
        mock_gui.is_cancelled.side_effect = [False, True]

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    @patch.object(FirewallSetupOrchestrator, '_phase3_content_update')
    def test_run_phase3_failure(self, mock_p3, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = True
        mock_p3.return_value = False
        mock_gui.is_cancelled.return_value = False

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    @patch.object(FirewallSetupOrchestrator, '_phase3_content_update')
    def test_run_cancelled_after_phase3(self, mock_p3, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = True
        mock_p3.return_value = True
        mock_gui.is_cancelled.side_effect = [False, False, True]

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    @patch.object(FirewallSetupOrchestrator, '_phase2_licensing')
    @patch.object(FirewallSetupOrchestrator, '_phase3_content_update')
    @patch.object(FirewallSetupOrchestrator, '_phase4_upgrade')
    def test_run_phase4_failure(self, mock_p4, mock_p3, mock_p2, mock_p1, mock_gui, sample_config):
        mock_p1.return_value = True
        mock_p2.return_value = True
        mock_p3.return_value = True
        mock_p4.return_value = False
        mock_gui.is_cancelled.return_value = False

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False

    @patch.object(FirewallSetupOrchestrator, '_phase1_initial_config')
    def test_run_exception(self, mock_p1, mock_gui, sample_config):
        mock_p1.side_effect = Exception("Unexpected error")

        orchestrator = FirewallSetupOrchestrator(mock_gui, sample_config)
        result = orchestrator.run()

        assert result is False
        mock_gui.show_error.assert_called()


class TestRunSetup:
    """Tests for run_setup function."""

    @patch('src.main.threading.Thread')
    def test_run_setup_starts_thread(self, mock_thread_class, mock_gui, sample_config):
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        run_setup(mock_gui, sample_config)

        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    @patch('src.main.beep_success')
    @patch('src.main.FirewallSetupOrchestrator')
    def test_run_setup_worker_success(self, mock_orchestrator_class, mock_beep, mock_gui, sample_config):
        mock_orchestrator = Mock()
        mock_orchestrator.run.return_value = True
        mock_orchestrator_class.return_value = mock_orchestrator

        # Capture the worker function
        import threading
        original_thread = threading.Thread

        captured_worker = [None]

        def mock_thread_init(target=None, daemon=None):
            captured_worker[0] = target
            mock_instance = Mock()
            mock_instance.start = Mock()
            return mock_instance

        with patch('src.main.threading.Thread', side_effect=mock_thread_init):
            run_setup(mock_gui, sample_config)

        # Run the captured worker
        captured_worker[0]()

        mock_beep.assert_called_once()
        mock_gui.show_info.assert_called()
        mock_gui.complete.assert_called_with(True)

    @patch('src.main.beep_error')
    @patch('src.main.FirewallSetupOrchestrator')
    def test_run_setup_worker_failure(self, mock_orchestrator_class, mock_beep, mock_gui, sample_config):
        mock_orchestrator = Mock()
        mock_orchestrator.run.return_value = False
        mock_orchestrator_class.return_value = mock_orchestrator

        captured_worker = [None]

        def mock_thread_init(target=None, daemon=None):
            captured_worker[0] = target
            mock_instance = Mock()
            mock_instance.start = Mock()
            return mock_instance

        with patch('src.main.threading.Thread', side_effect=mock_thread_init):
            run_setup(mock_gui, sample_config)

        captured_worker[0]()

        mock_gui.complete.assert_called_with(False)

    @patch('src.main.beep_error')
    @patch('src.main.FirewallSetupOrchestrator')
    def test_run_setup_worker_exception(self, mock_orchestrator_class, mock_beep, mock_gui, sample_config):
        mock_orchestrator = Mock()
        mock_orchestrator.run.side_effect = Exception("Unexpected error")
        mock_orchestrator_class.return_value = mock_orchestrator

        captured_worker = [None]

        def mock_thread_init(target=None, daemon=None):
            captured_worker[0] = target
            mock_instance = Mock()
            mock_instance.start = Mock()
            return mock_instance

        with patch('src.main.threading.Thread', side_effect=mock_thread_init):
            run_setup(mock_gui, sample_config)

        captured_worker[0]()

        mock_beep.assert_called_once()
        mock_gui.show_error.assert_called()
        mock_gui.complete.assert_called_with(False)


class TestMain:
    """Tests for main function."""

    @patch('src.main.PASSHPrepGUI')
    @patch('src.main.setup_logging')
    def test_main(self, mock_setup_logging, mock_gui_class):
        mock_gui = Mock()
        mock_gui_class.return_value = mock_gui

        main()

        mock_setup_logging.assert_called()
        mock_gui.create_window.assert_called()
        mock_gui.run.assert_called()
