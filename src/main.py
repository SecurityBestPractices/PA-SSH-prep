"""PA-SSH-prep - Main entry point for Palo Alto Firewall Initial Setup Tool."""

import logging
import threading
import sys
from typing import Optional

from src.gui import PASSHPrepGUI, SetupConfig
from src.utils import setup_logging, beep_error, beep_success, get_error_suggestion
from src.ssh_client import PANOSSSHClient, wait_for_ssh
from src.firewall_config import FirewallConfigurator
from src.licensing import LicenseManager
from src.content_update import ContentUpdater
from src.panos_upgrade import PANOSUpgrader, get_upgrade_path

# Default firewall IP (factory default)
DEFAULT_FIREWALL_IP = "192.168.1.1"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

logger = logging.getLogger("PA-SSH-prep")


class FirewallSetupOrchestrator:
    """Orchestrates the complete firewall setup process."""

    def __init__(self, gui: PASSHPrepGUI, config: SetupConfig):
        self.gui = gui
        self.config = config
        self.current_phase = 0
        self.total_phases = 4  # Initial config, licensing, content, upgrade

    def _update_progress(self, message: str, phase_progress: float = 0) -> None:
        """Update GUI with progress information."""
        # Calculate overall progress
        phase_weight = 100 / self.total_phases
        overall = (self.current_phase * phase_weight) + (phase_progress * phase_weight / 100)

        self.gui.update_status(message)
        self.gui.update_progress(overall)
        logger.info(message)

    def _check_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self.gui.is_cancelled()

    def run(self) -> bool:
        """
        Execute the complete setup process.

        Returns:
            True if successful
        """
        try:
            # Phase 1: Initial Configuration
            self.current_phase = 0
            if not self._phase1_initial_config():
                return False

            if self._check_cancelled():
                return False

            # Phase 2: Licensing
            self.current_phase = 1
            if not self._phase2_licensing():
                return False

            if self._check_cancelled():
                return False

            # Phase 3: Content Update
            self.current_phase = 2
            if not self._phase3_content_update():
                return False

            if self._check_cancelled():
                return False

            # Phase 4: PAN-OS Upgrade
            self.current_phase = 3
            if not self._phase4_upgrade():
                return False

            self._update_progress("Setup complete!", 100)
            return True

        except Exception as e:
            logger.exception("Setup failed")
            beep_error()
            self.gui.show_error(
                "Setup Failed",
                f"An error occurred: {e}\n\nSuggestion: {get_error_suggestion(e)}"
            )
            return False

    def _phase1_initial_config(self) -> bool:
        """
        Phase 1: Connect to factory default firewall and configure.

        Returns:
            True if successful
        """
        self._update_progress("Phase 1: Initial Configuration", 0)

        client = None
        try:
            # Connect to default IP
            self._update_progress("Connecting to firewall at 192.168.1.1...", 10)
            client = PANOSSSHClient(
                DEFAULT_FIREWALL_IP,
                DEFAULT_USERNAME,
                DEFAULT_PASSWORD
            )
            client.connect()

            # Configure the firewall
            configurator = FirewallConfigurator(
                client,
                progress_callback=lambda msg: self._update_progress(msg, 50)
            )

            # Set management IP
            self._update_progress("Configuring management IP...", 30)
            configurator.set_management_ip(
                self.config.new_ip,
                self.config.subnet_mask,
                self.config.gateway
            )

            # Set DNS
            self._update_progress("Configuring DNS servers...", 50)
            primary_dns = self.config.dns_servers[0] if self.config.dns_servers else "8.8.8.8"
            secondary_dns = self.config.dns_servers[1] if len(self.config.dns_servers) > 1 else None
            configurator.set_dns_servers(primary_dns, secondary_dns)

            # Change password
            self._update_progress("Changing admin password...", 70)
            configurator.change_admin_password(self.config.new_password)

            # Commit
            self._update_progress("Committing configuration...", 85)
            configurator.commit_configuration()

            self._update_progress("Initial configuration complete", 100)
            return True

        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            beep_error()
            self.gui.show_error(
                "Initial Configuration Failed",
                f"Failed to configure firewall: {e}\n\nSuggestion: {get_error_suggestion(e)}"
            )
            return False

        finally:
            if client:
                client.disconnect()

    def _phase2_licensing(self) -> bool:
        """
        Phase 2: Connect to new IP and fetch licenses.

        Returns:
            True if successful
        """
        self._update_progress("Phase 2: Licensing", 0)

        # Wait for firewall to be reachable on new IP
        self._update_progress("Waiting for firewall at new IP...", 10)

        if not wait_for_ssh(
            self.config.new_ip,
            username=DEFAULT_USERNAME,
            password=self.config.new_password,
            timeout=180,
            poll_interval=15,
            progress_callback=lambda msg: self._update_progress(msg, 20)
        ):
            beep_error()
            self.gui.show_error(
                "Connection Failed",
                f"Cannot connect to firewall at {self.config.new_ip}\n\n"
                "The firewall may still be committing or restarting services."
            )
            return False

        client = None
        try:
            # Connect to new IP with new password
            self._update_progress("Connecting to firewall...", 30)
            client = PANOSSSHClient(
                self.config.new_ip,
                DEFAULT_USERNAME,
                self.config.new_password
            )
            client.connect()

            # Fetch licenses
            self._update_progress("Fetching licenses...", 50)
            license_mgr = LicenseManager(
                client,
                progress_callback=lambda msg: self._update_progress(msg, 70)
            )
            license_mgr.fetch_licenses()

            self._update_progress("Licensing complete", 100)
            return True

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            beep_error()
            self.gui.show_error(
                "Licensing Failed",
                f"Failed to fetch licenses: {e}\n\nSuggestion: {get_error_suggestion(e)}"
            )
            return False

        finally:
            if client:
                client.disconnect()

    def _phase3_content_update(self) -> bool:
        """
        Phase 3: Download and install content updates.

        Returns:
            True if successful
        """
        self._update_progress("Phase 3: Content Update", 0)

        client = None
        try:
            # Connect
            self._update_progress("Connecting to firewall...", 10)
            client = PANOSSSHClient(
                self.config.new_ip,
                DEFAULT_USERNAME,
                self.config.new_password
            )
            client.connect()

            # Update content
            content_updater = ContentUpdater(
                client,
                progress_callback=lambda msg: self._update_progress(msg, 50)
            )

            self._update_progress("Downloading content update...", 30)
            content_updater.download_latest_content()

            self._update_progress("Installing content update...", 70)
            content_updater.install_latest_content()

            self._update_progress("Content update complete", 100)
            return True

        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            beep_error()
            self.gui.show_error(
                "Content Update Failed",
                f"Failed to update content: {e}\n\nSuggestion: {get_error_suggestion(e)}"
            )
            return False

        finally:
            if client:
                client.disconnect()

    def _phase4_upgrade(self) -> bool:
        """
        Phase 4: Upgrade PAN-OS to target version.

        Returns:
            True if successful
        """
        self._update_progress("Phase 4: PAN-OS Upgrade", 0)

        try:
            upgrader = PANOSUpgrader(
                self.config.new_ip,
                DEFAULT_USERNAME,
                self.config.new_password,
                progress_callback=lambda msg: self._update_progress(msg, 50)
            )

            # Connect and check current version
            upgrader.connect()
            current_version = upgrader.get_current_version()

            # Get upgrade path
            path = get_upgrade_path(current_version, self.config.target_version)

            if not path:
                self._update_progress(
                    f"Already at or past target version ({current_version})", 100
                )
                upgrader.disconnect()
                return True

            self._update_progress(
                f"Upgrade path: {current_version} -> {' -> '.join(path)}", 10
            )

            total_steps = len(path)
            for i, version in enumerate(path):
                step_progress = (i / total_steps) * 100

                if self._check_cancelled():
                    upgrader.disconnect()
                    return False

                self._update_progress(f"Upgrading to {version}...", step_progress)

                # Check for available software
                upgrader.check_available_versions()

                # Download
                self._update_progress(f"Downloading PAN-OS {version}...", step_progress + 10)
                upgrader.download_software(version)

                # Install
                self._update_progress(f"Installing PAN-OS {version}...", step_progress + 40)
                upgrader.install_software(version)

                # Reboot
                self._update_progress(f"Rebooting after {version} install...", step_progress + 60)
                upgrader.reboot()

                # Wait for reboot
                self._update_progress("Waiting for firewall to come back online...", step_progress + 70)
                if not upgrader.wait_for_reboot(timeout=600):
                    raise RuntimeError(f"Firewall did not come back after upgrading to {version}")

                # Reconnect
                upgrader.connect()

            # Verify final version
            final_version = upgrader.get_current_version()
            self._update_progress(f"Upgrade complete. Final version: {final_version}", 100)

            upgrader.disconnect()
            return True

        except Exception as e:
            logger.error(f"Phase 4 failed: {e}")
            beep_error()
            self.gui.show_error(
                "PAN-OS Upgrade Failed",
                f"Failed to upgrade PAN-OS: {e}\n\nSuggestion: {get_error_suggestion(e)}"
            )
            return False


def run_setup(gui: PASSHPrepGUI, config: SetupConfig) -> None:
    """Run the setup process in a background thread."""
    def worker():
        try:
            orchestrator = FirewallSetupOrchestrator(gui, config)
            success = orchestrator.run()

            if success:
                beep_success()
                gui.show_info(
                    "Setup Complete",
                    f"Firewall setup completed successfully!\n\n"
                    f"Management IP: {config.new_ip}\n"
                    f"PAN-OS Version: {config.target_version}"
                )
            gui.complete(success)

        except Exception as e:
            logger.exception("Unexpected error in setup worker")
            beep_error()
            gui.show_error("Error", f"Unexpected error: {e}")
            gui.complete(False)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def main() -> None:
    """Main entry point."""
    # Set up logging
    setup_logging()
    logger.info("PA-SSH-prep starting")

    # Create and run GUI
    gui = PASSHPrepGUI()

    def on_start(config: SetupConfig) -> None:
        run_setup(gui, config)

    gui.on_start = on_start
    gui.create_window()
    gui.run()

    logger.info("PA-SSH-prep exiting")


if __name__ == "__main__":
    main()
