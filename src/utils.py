"""Utility functions for logging, alerts, and error handling."""

import logging
import sys
from datetime import datetime
from typing import Optional

# Try to import winsound for Windows, provide fallback for other platforms
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger("PA-SSH-prep")
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def beep_error() -> None:
    """Play an error beep sound on Windows."""
    if HAS_WINSOUND:
        winsound.Beep(1000, 500)  # 1000Hz for 500ms


def beep_success() -> None:
    """Play a success beep sound on Windows."""
    if HAS_WINSOUND:
        winsound.Beep(800, 200)  # 800Hz for 200ms
        winsound.Beep(1000, 200)  # 1000Hz for 200ms


def get_error_suggestion(error: Exception) -> str:
    """Get a helpful suggestion based on the error type."""
    error_str = str(error).lower()

    if "authentication" in error_str or "password" in error_str:
        return "Check the username and password. The default is admin/admin."
    elif "timeout" in error_str or "timed out" in error_str:
        return "The firewall may be unreachable. Check network connectivity and IP address."
    elif "connection refused" in error_str:
        return "SSH may not be enabled or the firewall is not ready. Wait and try again."
    elif "host key" in error_str:
        return "SSH host key verification failed. This may be a new or reset firewall."
    elif "no route" in error_str or "network is unreachable" in error_str:
        return "Cannot reach the firewall. Check that you're on the correct network."
    elif "license" in error_str:
        return "License operation failed. Ensure the firewall has internet access."
    elif "commit" in error_str:
        return "Configuration commit failed. Check for conflicting settings."
    else:
        return "Check the logs for more details and try again."


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def validate_ip_address(ip: str) -> bool:
    """Validate an IPv4 address format."""
    parts = ip.strip().split('.')
    if len(parts) != 4:
        return False
    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def validate_subnet_mask(mask: str) -> bool:
    """Validate a subnet mask format."""
    if not validate_ip_address(mask):
        return False

    # Convert to binary and check it's a valid mask (all 1s followed by all 0s)
    parts = [int(p) for p in mask.split('.')]
    binary = ''.join(format(p, '08b') for p in parts)

    # Valid masks have all 1s before all 0s
    seen_zero = False
    for bit in binary:
        if bit == '0':
            seen_zero = True
        elif seen_zero:
            return False
    return True


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets PAN-OS requirements.
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 31:
        return False, "Password must be 31 characters or less"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""
