"""License fetch operations for PAN-OS firewalls."""

import logging
import time
from typing import Callable, Optional
from src.ssh_client import PANOSSSHClient

logger = logging.getLogger("PA-SSH-prep")


class LicenseManager:
    """Handles license operations on PAN-OS firewalls."""

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

    def fetch_licenses(self, timeout: int = 120) -> str:
        """
        Fetch licenses from Palo Alto license server.

        Args:
            timeout: Maximum time to wait for license fetch

        Returns:
            Output from license fetch command

        Raises:
            RuntimeError: If license fetch fails
        """
        self._update_progress("Fetching licenses from license server...")

        try:
            output = self.client.send_command(
                "request license fetch",
                read_timeout=timeout
            )

            logger.debug(f"License fetch output: {output}")

            # Check for success indicators
            if "successfully" in output.lower():
                self._update_progress("Licenses fetched successfully")
                return output

            # Check for common errors
            if "failed" in output.lower():
                raise RuntimeError(f"License fetch failed: {output}")

            if "unable to connect" in output.lower():
                raise RuntimeError("Unable to connect to license server. Check internet connectivity.")

            if "invalid auth code" in output.lower():
                raise RuntimeError("Invalid auth code. Check firewall registration.")

            # If no clear success/failure, log warning but continue
            self._update_progress("License fetch completed")
            return output

        except Exception as e:
            logger.error(f"License fetch error: {e}")
            raise

    def get_license_info(self) -> str:
        """
        Get current license information.

        Returns:
            Output from show license command
        """
        self._update_progress("Checking license status...")

        output = self.client.send_command("request license info")
        return output

    def verify_licenses_active(self) -> bool:
        """
        Verify that licenses are active.

        Returns:
            True if licenses appear to be active
        """
        output = self.get_license_info()

        # Check for indicators of active licenses
        has_licenses = (
            "threat prevention" in output.lower() or
            "pandb url filtering" in output.lower() or
            "wildfire" in output.lower() or
            "globalprotect" in output.lower() or
            "valid" in output.lower()
        )

        return has_licenses


def fetch_and_verify_licenses(
    host: str,
    username: str,
    password: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    max_retries: int = 3,
    retry_delay: int = 30
) -> bool:
    """
    Connect to firewall and fetch licenses with retry logic.

    Args:
        host: Firewall IP address
        username: SSH username
        password: SSH password
        progress_callback: Optional callback for progress updates
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if licenses fetched successfully
    """
    client = None

    def update(msg: str) -> None:
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    try:
        update(f"Connecting to {host} for licensing...")

        client = PANOSSSHClient(host, username, password)
        client.connect()

        license_manager = LicenseManager(client, progress_callback)

        # Try to fetch licenses with retries
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                update(f"License fetch attempt {attempt}/{max_retries}...")
                license_manager.fetch_licenses()

                # Verify licenses are active
                if license_manager.verify_licenses_active():
                    update("Licenses verified as active")
                    return True
                else:
                    update("Warning: Could not verify license activation")
                    return True  # Still return True as fetch succeeded

            except Exception as e:
                last_error = e
                logger.warning(f"License fetch attempt {attempt} failed: {e}")

                if attempt < max_retries:
                    update(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        # All retries exhausted
        raise RuntimeError(f"License fetch failed after {max_retries} attempts: {last_error}")

    finally:
        if client:
            client.disconnect()
