"""Firewall initial configuration operations."""

import logging
from typing import Callable, Optional
from src.ssh_client import PANOSSSHClient

logger = logging.getLogger("PA-SSH-prep")


class FirewallConfigurator:
    """Handles initial firewall configuration via SSH."""

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

    def set_management_ip(
        self,
        ip_address: str,
        subnet_mask: str,
        gateway: str
    ) -> None:
        """
        Configure the management interface IP settings.

        Args:
            ip_address: New management IP address
            subnet_mask: Subnet mask
            gateway: Default gateway
        """
        self._update_progress(f"Setting management IP to {ip_address}...")

        # Enter configuration mode
        self.client.enter_configure_mode()

        try:
            # Set management IP configuration
            commands = [
                f"set deviceconfig system ip-address {ip_address}",
                f"set deviceconfig system netmask {subnet_mask}",
                f"set deviceconfig system default-gateway {gateway}",
            ]

            for cmd in commands:
                logger.debug(f"Executing: {cmd}")
                output = self.client.send_command_timing(cmd)
                if "error" in output.lower() or "invalid" in output.lower():
                    raise RuntimeError(f"Command failed: {cmd}\nOutput: {output}")

            self._update_progress("Management IP configured")

        finally:
            self.client.exit_configure_mode()

    def set_dns_servers(self, primary_dns: str, secondary_dns: Optional[str] = None) -> None:
        """
        Configure DNS servers.

        Args:
            primary_dns: Primary DNS server IP
            secondary_dns: Secondary DNS server IP (optional)
        """
        self._update_progress(f"Setting DNS servers...")

        self.client.enter_configure_mode()

        try:
            # Set primary DNS
            cmd = f"set deviceconfig system dns-setting servers primary {primary_dns}"
            logger.debug(f"Executing: {cmd}")
            output = self.client.send_command_timing(cmd)
            if "error" in output.lower() or "invalid" in output.lower():
                raise RuntimeError(f"Failed to set primary DNS: {output}")

            # Set secondary DNS if provided
            if secondary_dns:
                cmd = f"set deviceconfig system dns-setting servers secondary {secondary_dns}"
                logger.debug(f"Executing: {cmd}")
                output = self.client.send_command_timing(cmd)
                if "error" in output.lower() or "invalid" in output.lower():
                    raise RuntimeError(f"Failed to set secondary DNS: {output}")

            self._update_progress("DNS servers configured")

        finally:
            self.client.exit_configure_mode()

    def change_admin_password(self, new_password: str) -> None:
        """
        Change the admin user password.

        Args:
            new_password: New admin password
        """
        self._update_progress("Changing admin password...")

        self.client.enter_configure_mode()

        try:
            # Use phash format for password
            cmd = f'set mgt-config users admin password'
            logger.debug("Executing password change command")

            # Send the command
            self.client.send_command_timing(cmd)
            # Send the password when prompted
            self.client.send_command_timing(new_password)
            # Confirm the password
            output = self.client.send_command_timing(new_password)

            if "error" in output.lower():
                raise RuntimeError(f"Password change failed: {output}")

            self._update_progress("Admin password changed")

        finally:
            self.client.exit_configure_mode()

    def commit_configuration(self, timeout: int = 300) -> None:
        """
        Commit the current configuration.

        Args:
            timeout: Maximum time to wait for commit
        """
        self._update_progress("Committing configuration...")

        output = self.client.commit(timeout=timeout)

        if "success" in output.lower():
            self._update_progress("Configuration committed successfully")
        else:
            self._update_progress("Configuration commit completed")

    def perform_initial_setup(
        self,
        new_ip: str,
        subnet_mask: str,
        gateway: str,
        dns_servers: list[str],
        new_password: str
    ) -> None:
        """
        Perform complete initial setup of the firewall.

        This includes:
        1. Setting management IP
        2. Setting DNS servers
        3. Changing admin password
        4. Committing configuration

        Args:
            new_ip: New management IP address
            subnet_mask: Subnet mask
            gateway: Default gateway
            dns_servers: List of DNS server IPs (1-2)
            new_password: New admin password
        """
        self._update_progress("Starting initial configuration...")

        # Configure management IP
        self.set_management_ip(new_ip, subnet_mask, gateway)

        # Configure DNS
        primary_dns = dns_servers[0] if dns_servers else "8.8.8.8"
        secondary_dns = dns_servers[1] if len(dns_servers) > 1 else None
        self.set_dns_servers(primary_dns, secondary_dns)

        # Change password
        self.change_admin_password(new_password)

        # Commit all changes
        self.commit_configuration()

        self._update_progress("Initial configuration complete")


def configure_firewall(
    host: str,
    new_ip: str,
    subnet_mask: str,
    gateway: str,
    dns_servers: list[str],
    new_password: str,
    username: str = "admin",
    current_password: str = "admin",
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    High-level function to configure a firewall with new settings.

    Args:
        host: Current firewall IP (e.g., 192.168.1.1)
        new_ip: New management IP address
        subnet_mask: Subnet mask
        gateway: Default gateway
        dns_servers: List of DNS server IPs
        new_password: New admin password
        username: SSH username
        current_password: Current SSH password
        progress_callback: Optional callback for progress updates

    Returns:
        True if successful
    """
    client = None

    try:
        # Connect to firewall
        if progress_callback:
            progress_callback(f"Connecting to {host}...")

        client = PANOSSSHClient(host, username, current_password)
        client.connect()

        # Perform configuration
        configurator = FirewallConfigurator(client, progress_callback)
        configurator.perform_initial_setup(
            new_ip=new_ip,
            subnet_mask=subnet_mask,
            gateway=gateway,
            dns_servers=dns_servers,
            new_password=new_password
        )

        return True

    finally:
        if client:
            client.disconnect()
