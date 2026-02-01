"""Netmiko-based SSH client for PAN-OS devices."""

import time
import logging
from typing import Optional, Callable
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

logger = logging.getLogger("PA-SSH-prep")


class PANOSSSHClient:
    """SSH client wrapper for PAN-OS firewalls using Netmiko."""

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "admin",
        port: int = 22,
        timeout: int = 60
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.connection: Optional[ConnectHandler] = None

    def connect(self) -> None:
        """Establish SSH connection to the firewall."""
        logger.info(f"Connecting to {self.host}:{self.port} as {self.username}")

        device = {
            'device_type': 'paloalto_panos',
            'host': self.host,
            'username': self.username,
            'password': self.password,
            'port': self.port,
            'timeout': self.timeout,
            'session_timeout': 120,
            'auth_timeout': 60,
            'banner_timeout': 60,
        }

        try:
            self.connection = ConnectHandler(**device)
            logger.info(f"Successfully connected to {self.host}")
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timed out: {e}")
            raise
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    def disconnect(self) -> None:
        """Close the SSH connection."""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connection = None

    def is_connected(self) -> bool:
        """Check if connection is active."""
        if not self.connection:
            return False
        try:
            return self.connection.is_alive()
        except Exception:
            return False

    def send_command(
        self,
        command: str,
        expect_string: Optional[str] = None,
        read_timeout: int = 120,
        strip_prompt: bool = True,
        strip_command: bool = True
    ) -> str:
        """
        Send a command and return the output.

        Args:
            command: The command to execute
            expect_string: Optional string to wait for in output
            read_timeout: Timeout for reading response
            strip_prompt: Remove prompt from output
            strip_command: Remove echoed command from output

        Returns:
            Command output as string
        """
        if not self.connection:
            raise RuntimeError("Not connected to firewall")

        logger.debug(f"Sending command: {command}")

        try:
            output = self.connection.send_command(
                command,
                expect_string=expect_string,
                read_timeout=read_timeout,
                strip_prompt=strip_prompt,
                strip_command=strip_command
            )
            logger.debug(f"Command output: {output[:200]}..." if len(output) > 200 else f"Command output: {output}")
            return output
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    def send_command_timing(self, command: str, delay_factor: float = 2.0) -> str:
        """
        Send a command using timing-based approach (for commands without clear ending).

        Args:
            command: The command to execute
            delay_factor: Multiplier for delays

        Returns:
            Command output as string
        """
        if not self.connection:
            raise RuntimeError("Not connected to firewall")

        logger.debug(f"Sending command (timing): {command}")

        try:
            output = self.connection.send_command_timing(command, delay_factor=delay_factor)
            return output
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise

    def send_config_command(self, command: str) -> str:
        """Send a configuration mode command."""
        if not self.connection:
            raise RuntimeError("Not connected to firewall")

        logger.debug(f"Sending config command: {command}")

        try:
            # Enter configure mode
            self.connection.send_command_timing("configure")
            # Send the actual command
            output = self.connection.send_command_timing(command)
            # Exit configure mode
            self.connection.send_command_timing("exit")
            return output
        except Exception as e:
            logger.error(f"Config command failed: {e}")
            raise

    def send_config_set(self, commands: list[str]) -> str:
        """Send multiple configuration commands."""
        if not self.connection:
            raise RuntimeError("Not connected to firewall")

        logger.debug(f"Sending config set: {commands}")

        try:
            output = self.connection.send_config_set(commands)
            return output
        except Exception as e:
            logger.error(f"Config set failed: {e}")
            raise

    def enter_configure_mode(self) -> str:
        """Enter configuration mode."""
        return self.send_command_timing("configure")

    def exit_configure_mode(self) -> str:
        """Exit configuration mode."""
        return self.send_command_timing("exit")

    def commit(self, timeout: int = 300) -> str:
        """
        Commit the current configuration.

        Args:
            timeout: Maximum time to wait for commit

        Returns:
            Commit output
        """
        logger.info("Committing configuration...")

        try:
            output = self.send_command(
                "commit",
                expect_string=r"(Configuration committed successfully|Commit failed)",
                read_timeout=timeout
            )

            if "failed" in output.lower():
                raise RuntimeError(f"Commit failed: {output}")

            logger.info("Configuration committed successfully")
            return output
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            raise

    def get_system_info(self) -> dict:
        """Get system information including PAN-OS version."""
        output = self.send_command("show system info")

        info = {}
        for line in output.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                info[key.strip().lower()] = value.strip()

        return info

    def get_panos_version(self) -> str:
        """Get the current PAN-OS version."""
        info = self.get_system_info()
        return info.get('sw-version', '')


def wait_for_ssh(
    host: str,
    port: int = 22,
    username: str = "admin",
    password: str = "admin",
    timeout: int = 600,
    poll_interval: int = 30,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Wait for SSH to become available on a host.

    Args:
        host: Target host IP
        port: SSH port
        username: SSH username
        password: SSH password
        timeout: Maximum time to wait in seconds
        poll_interval: Time between connection attempts
        progress_callback: Optional callback for progress updates

    Returns:
        True if connection successful, False if timeout
    """
    import socket

    start_time = time.time()
    attempt = 0

    while (time.time() - start_time) < timeout:
        attempt += 1
        elapsed = int(time.time() - start_time)

        if progress_callback:
            progress_callback(f"Waiting for SSH... Attempt {attempt} ({elapsed}s elapsed)")

        logger.info(f"SSH connection attempt {attempt} to {host}:{port}")

        # First check if port is open
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                logger.debug(f"Port {port} not open yet")
                time.sleep(poll_interval)
                continue
        except Exception as e:
            logger.debug(f"Socket check failed: {e}")
            time.sleep(poll_interval)
            continue

        # Port is open, try SSH connection
        try:
            client = PANOSSSHClient(host, username, password, port)
            client.connect()
            # Verify we can run a command
            client.send_command_timing("show clock")
            client.disconnect()
            logger.info(f"SSH connection successful to {host}")
            return True
        except Exception as e:
            logger.debug(f"SSH connection attempt failed: {e}")

        time.sleep(poll_interval)

    logger.error(f"Timeout waiting for SSH on {host}")
    return False
