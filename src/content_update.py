"""Content update operations for PAN-OS firewalls."""

import logging
import re
import time
from typing import Callable, Optional
from src.ssh_client import PANOSSSHClient

logger = logging.getLogger("PA-SSH-prep")


class ContentUpdater:
    """Handles content update operations on PAN-OS firewalls."""

    def __init__(
        self,
        client: PANOSSSHClient,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        self.client = client
        self.progress_callback = progress_callback

    def _update_progress(self, message: str) -> None:
        """Update progress via callback."""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def check_content_version(self) -> str:
        """
        Check current content version.

        Returns:
            Current content version string
        """
        output = self.client.send_command("request content upgrade check")
        return output

    def download_latest_content(self, timeout: int = 600) -> str:
        """
        Download the latest content update.

        Args:
            timeout: Maximum time to wait for download

        Returns:
            Output from download command

        Raises:
            RuntimeError: If download fails
        """
        self._update_progress("Downloading latest content update...")

        try:
            output = self.client.send_command(
                "request content upgrade download latest",
                read_timeout=timeout
            )

            logger.debug(f"Content download output: {output}")

            # Check for various status indicators
            if "download job enqueued" in output.lower():
                self._update_progress("Content download job started, waiting for completion...")
                return self._wait_for_download_completion(timeout)

            if "already downloaded" in output.lower():
                self._update_progress("Latest content already downloaded")
                return output

            if "download succeeded" in output.lower() or "successfully" in output.lower():
                self._update_progress("Content download completed")
                return output

            if "failed" in output.lower():
                raise RuntimeError(f"Content download failed: {output}")

            return output

        except Exception as e:
            logger.error(f"Content download error: {e}")
            raise

    def _wait_for_download_completion(self, timeout: int = 600) -> str:
        """Wait for a content download to complete."""
        start_time = time.time()
        poll_interval = 10

        while (time.time() - start_time) < timeout:
            time.sleep(poll_interval)

            # Check download status
            status = self.client.send_command("request content upgrade info")

            if "currently downloading" in status.lower():
                # Extract percentage if available
                match = re.search(r'(\d+)%', status)
                if match:
                    self._update_progress(f"Downloading content: {match.group(1)}%")
                continue

            if "download" in status.lower() and "complete" in status.lower():
                self._update_progress("Content download completed")
                return status

            if "failed" in status.lower():
                raise RuntimeError(f"Content download failed: {status}")

            # Check if any version is ready for install
            if self._get_downloadable_version(status):
                return status

        raise RuntimeError("Content download timed out")

    def _get_downloadable_version(self, status_output: str) -> Optional[str]:
        """Extract a downloaded version from status output."""
        # Look for version patterns
        match = re.search(r'(\d+-\d+)\s+yes', status_output.lower())
        if match:
            return match.group(1)
        return None

    def install_latest_content(self, timeout: int = 300) -> str:
        """
        Install the latest downloaded content.

        Args:
            timeout: Maximum time to wait for installation

        Returns:
            Output from install command

        Raises:
            RuntimeError: If installation fails
        """
        self._update_progress("Installing content update...")

        try:
            output = self.client.send_command(
                "request content upgrade install version latest",
                read_timeout=timeout
            )

            logger.debug(f"Content install output: {output}")

            if "install job enqueued" in output.lower():
                self._update_progress("Content install job started, waiting for completion...")
                return self._wait_for_install_completion(timeout)

            if "successfully" in output.lower() or "installed" in output.lower():
                self._update_progress("Content installed successfully")
                return output

            if "failed" in output.lower():
                raise RuntimeError(f"Content installation failed: {output}")

            if "already installed" in output.lower():
                self._update_progress("Latest content already installed")
                return output

            return output

        except Exception as e:
            logger.error(f"Content install error: {e}")
            raise

    def _wait_for_install_completion(self, timeout: int = 300) -> str:
        """Wait for content installation to complete."""
        start_time = time.time()
        poll_interval = 10

        while (time.time() - start_time) < timeout:
            time.sleep(poll_interval)

            status = self.client.send_command("request content upgrade info")

            if "currently installing" in status.lower():
                self._update_progress("Installing content...")
                continue

            if "install" in status.lower() and "complete" in status.lower():
                self._update_progress("Content installation completed")
                return status

            if "failed" in status.lower():
                raise RuntimeError(f"Content installation failed: {status}")

            # Check for successful install indicators
            if "version" in status.lower() and "current" in status.lower():
                return status

        raise RuntimeError("Content installation timed out")

    def update_content(self) -> None:
        """
        Perform full content update (download and install).
        """
        self._update_progress("Starting content update...")

        # Download latest content
        self.download_latest_content()

        # Install content
        self.install_latest_content()

        self._update_progress("Content update complete")


def update_firewall_content(
    host: str,
    username: str,
    password: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Connect to firewall and update content.

    Args:
        host: Firewall IP address
        username: SSH username
        password: SSH password
        progress_callback: Optional callback for progress updates

    Returns:
        True if content update successful
    """
    client = None

    def update(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        update(f"Connecting to {host} for content update...")

        client = PANOSSSHClient(host, username, password)
        client.connect()

        content_updater = ContentUpdater(client, progress_callback)
        content_updater.update_content()

        return True

    finally:
        if client:
            client.disconnect()
