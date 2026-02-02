"""PAN-OS upgrade operations and version management."""

import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, Optional
from src.ssh_client import PANOSSSHClient, wait_for_ssh

logger = logging.getLogger("PA-SSH-prep")


# PAN-OS upgrade paths - maps source major.minor version to next base version in upgrade path
# Each major version jump requires installing the base release first
# Note: Base version is typically X.Y.0, but 12.1 base is 12.1.2
# Format: {source_major.minor: next_base_version}
UPGRADE_PATHS = {
    "9.0": "9.1.0",
    "9.1": "10.0.0",
    "10.0": "10.1.0",
    "10.1": "10.2.0",
    "10.2": "11.0.0",
    "11.0": "11.1.0",
    "11.1": "11.2.0",
    "11.2": "12.1.2",  # 12.1 base version is 12.1.2, not 12.1.0
}


@dataclass
class Version:
    """PAN-OS version representation."""
    major: int
    minor: int
    patch: int
    original: str

    @classmethod
    def parse(cls, version_str: str) -> 'Version':
        """Parse a version string like '10.2.4' or '10.2.4-h1'."""
        # Remove any hotfix suffix
        clean_version = re.sub(r'-h\d+$', '', version_str.strip())

        match = re.match(r'^(\d+)\.(\d+)\.(\d+)', clean_version)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")

        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            original=version_str.strip()
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def major_minor(self) -> str:
        """Return major.minor version string."""
        return f"{self.major}.{self.minor}"

    def base_version(self) -> str:
        """Return base version (X.Y.0)."""
        return f"{self.major}.{self.minor}.0"

    def __lt__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __ge__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)


def get_upgrade_path(current_version: str, target_version: str) -> list[str]:
    """
    Determine the upgrade path from current to target version.

    Args:
        current_version: Current PAN-OS version
        target_version: Target PAN-OS version

    Returns:
        List of versions to upgrade through (including target)
    """
    current = Version.parse(current_version)
    target = Version.parse(target_version)

    if current >= target:
        return []  # Already at or past target

    path = []
    working_version = current

    while working_version < target:
        current_major_minor = working_version.major_minor()

        # Check if we need to jump to next major version
        if current_major_minor in UPGRADE_PATHS:
            next_base = UPGRADE_PATHS[current_major_minor]
            next_version = Version.parse(next_base)

            # If target is in same major.minor as next step, go directly to target
            if next_version.major_minor() == target.major_minor():
                path.append(str(target))
                break
            elif next_version <= target:
                path.append(next_base)
                working_version = next_version
            else:
                # Target is in current major.minor
                path.append(str(target))
                break
        else:
            # Same major.minor, just upgrade to target
            path.append(str(target))
            break

    return path


class PANOSUpgrader:
    """Handles PAN-OS upgrade operations."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        self.host = host
        self.username = username
        self.password = password
        self.progress_callback = progress_callback
        self.client: Optional[PANOSSSHClient] = None

    def _update_progress(self, message: str) -> None:
        """Update progress via callback."""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def connect(self) -> None:
        """Establish SSH connection."""
        self._update_progress(f"Connecting to {self.host}...")
        self.client = PANOSSSHClient(self.host, self.username, self.password)
        self.client.connect()

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.disconnect()
            self.client = None

    def get_current_version(self) -> str:
        """Get current PAN-OS version."""
        if not self.client:
            raise RuntimeError("Not connected")

        version = self.client.get_panos_version()
        self._update_progress(f"Current PAN-OS version: {version}")
        return version

    def check_available_versions(self) -> str:
        """Check available software versions."""
        if not self.client:
            raise RuntimeError("Not connected")

        self._update_progress("Checking available software versions...")
        output = self.client.send_command(
            "request system software check",
            read_timeout=120
        )
        return output

    def download_software(self, version: str, timeout: int = 1800) -> None:
        """
        Download a specific PAN-OS version.

        Args:
            version: Version to download (e.g., "10.2.0")
            timeout: Maximum time to wait for download
        """
        if not self.client:
            raise RuntimeError("Not connected")

        self._update_progress(f"Downloading PAN-OS {version}...")

        # Check if base version needs to be downloaded first
        ver = Version.parse(version)
        if ver.patch != 0:
            # Need to download base first
            base = ver.base_version()
            self._download_version(base, timeout // 2)

        # Download the target version
        self._download_version(version, timeout)

    def _download_version(self, version: str, timeout: int) -> None:
        """Download a specific version."""
        if not self.client:
            raise RuntimeError("Not connected")

        self._update_progress(f"Downloading version {version}...")

        output = self.client.send_command(
            f"request system software download version {version}",
            read_timeout=60
        )

        if "already downloaded" in output.lower():
            self._update_progress(f"Version {version} already downloaded")
            return

        if "download job enqueued" in output.lower() or "started" in output.lower():
            self._wait_for_software_download(version, timeout)
        elif "successfully" in output.lower():
            self._update_progress(f"Version {version} downloaded")
        elif "failed" in output.lower() or "error" in output.lower():
            raise RuntimeError(f"Failed to download {version}: {output}")

    def _wait_for_software_download(self, version: str, timeout: int) -> None:
        """Wait for software download to complete."""
        if not self.client:
            raise RuntimeError("Not connected")

        start_time = time.time()
        poll_interval = 30

        while (time.time() - start_time) < timeout:
            time.sleep(poll_interval)

            status = self.client.send_command("request system software info")

            # Check if download is complete
            if version in status:
                # Look for downloaded indicator
                lines = status.split('\n')
                for line in lines:
                    if version in line and ('yes' in line.lower() or 'downloaded' in line.lower()):
                        self._update_progress(f"Version {version} download complete")
                        return

            # Check for progress
            if "downloading" in status.lower():
                match = re.search(r'(\d+)%', status)
                if match:
                    self._update_progress(f"Downloading {version}: {match.group(1)}%")

            if "failed" in status.lower():
                raise RuntimeError(f"Download of {version} failed")

        raise RuntimeError(f"Download of {version} timed out")

    def install_software(self, version: str, timeout: int = 1200) -> None:
        """
        Install a specific PAN-OS version.

        Args:
            version: Version to install
            timeout: Maximum time to wait for installation
        """
        if not self.client:
            raise RuntimeError("Not connected")

        self._update_progress(f"Installing PAN-OS {version}...")

        output = self.client.send_command(
            f"request system software install version {version}",
            read_timeout=60
        )

        if "install job enqueued" in output.lower() or "started" in output.lower():
            self._wait_for_software_install(version, timeout)
        elif "successfully" in output.lower() or "installed" in output.lower():
            self._update_progress(f"Version {version} installed")
        elif "failed" in output.lower() or "error" in output.lower():
            raise RuntimeError(f"Failed to install {version}: {output}")

    def _wait_for_software_install(self, version: str, timeout: int) -> None:
        """Wait for software installation to complete."""
        if not self.client:
            raise RuntimeError("Not connected")

        start_time = time.time()
        poll_interval = 30

        while (time.time() - start_time) < timeout:
            time.sleep(poll_interval)

            try:
                status = self.client.send_command("show jobs all")

                # Check for completion
                if "installed" in status.lower() and version in status:
                    self._update_progress(f"Version {version} installation complete")
                    return

                # Check for in-progress
                if "running" in status.lower() or "pending" in status.lower():
                    self._update_progress(f"Installing {version}...")
                    continue

                if "failed" in status.lower():
                    raise RuntimeError(f"Installation of {version} failed")

            except Exception as e:
                logger.warning(f"Error checking install status: {e}")
                continue

        raise RuntimeError(f"Installation of {version} timed out")

    def reboot(self) -> None:
        """Reboot the firewall."""
        if not self.client:
            raise RuntimeError("Not connected")

        self._update_progress("Rebooting firewall...")

        try:
            self.client.send_command_timing("request restart system")
            # Confirm if prompted
            self.client.send_command_timing("y")
        except Exception:
            # Connection will likely drop during reboot
            pass

        self.disconnect()

    def wait_for_reboot(self, timeout: int = 600) -> bool:
        """
        Wait for firewall to come back online after reboot.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if firewall is back online
        """
        self._update_progress("Waiting for firewall to reboot...")

        # Give initial time for shutdown
        time.sleep(60)

        success = wait_for_ssh(
            self.host,
            username=self.username,
            password=self.password,
            timeout=timeout - 60,
            poll_interval=30,
            progress_callback=self.progress_callback
        )

        if success:
            self._update_progress("Firewall is back online")
        else:
            self._update_progress("Timeout waiting for firewall to come back online")

        return success

    def upgrade_to_version(self, target_version: str) -> bool:
        """
        Perform complete upgrade to target version.

        This handles the full upgrade path, including:
        - Determining required intermediate versions
        - Downloading and installing each version
        - Rebooting between versions

        Args:
            target_version: Target PAN-OS version

        Returns:
            True if upgrade successful
        """
        try:
            self.connect()
            current = self.get_current_version()

            # Get upgrade path
            path = get_upgrade_path(current, target_version)

            if not path:
                self._update_progress(f"Already at version {current}, no upgrade needed")
                return True

            self._update_progress(f"Upgrade path: {current} -> {' -> '.join(path)}")

            for version in path:
                self._update_progress(f"Upgrading to {version}...")

                # Check software availability
                self.check_available_versions()

                # Download
                self.download_software(version)

                # Install
                self.install_software(version)

                # Reboot
                self.reboot()

                # Wait for reboot
                if not self.wait_for_reboot():
                    raise RuntimeError(f"Firewall did not come back after upgrading to {version}")

                # Reconnect
                self.connect()

                # Verify version
                new_version = self.get_current_version()
                if not new_version.startswith(version.rsplit('.', 1)[0]):
                    logger.warning(f"Expected version {version}, got {new_version}")

            self._update_progress(f"Upgrade to {target_version} complete!")
            return True

        except Exception as e:
            logger.error(f"Upgrade failed: {e}")
            return False

        finally:
            self.disconnect()


def upgrade_firewall(
    host: str,
    username: str,
    password: str,
    target_version: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    High-level function to upgrade a firewall to target version.

    Args:
        host: Firewall IP address
        username: SSH username
        password: SSH password
        target_version: Target PAN-OS version
        progress_callback: Optional callback for progress updates

    Returns:
        True if upgrade successful
    """
    upgrader = PANOSUpgrader(host, username, password, progress_callback)
    return upgrader.upgrade_to_version(target_version)
