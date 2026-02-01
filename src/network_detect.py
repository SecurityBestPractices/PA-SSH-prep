"""Windows network settings detection for firewall configuration."""

import subprocess
import re
import socket
from dataclasses import dataclass
from typing import Optional


@dataclass
class NetworkSettings:
    """Detected network settings from Windows adapter."""
    subnet_mask: str
    gateway: str
    dns_servers: list[str]
    local_ip: str
    adapter_name: str


def run_ipconfig() -> str:
    """Run ipconfig /all and return output."""
    try:
        result = subprocess.run(
            ['ipconfig', '/all'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        raise RuntimeError(f"Failed to run ipconfig: {e}")


def parse_ipconfig_output(output: str) -> list[dict]:
    """Parse ipconfig /all output into adapter dictionaries."""
    adapters = []
    current_adapter = None

    for line in output.split('\n'):
        line = line.rstrip()

        # New adapter section (not indented, ends with colon)
        if line and not line.startswith(' ') and ':' in line:
            if current_adapter:
                adapters.append(current_adapter)
            current_adapter = {'name': line.rstrip(':'), 'ips': [], 'dns': []}
        elif current_adapter and line.startswith('   '):
            # Property line
            line = line.strip()

            # IPv4 Address
            if 'IPv4 Address' in line or 'IP Address' in line:
                match = re.search(r':\s*(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    current_adapter['ips'].append(ip)

            # Subnet Mask
            elif 'Subnet Mask' in line:
                match = re.search(r':\s*(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    current_adapter['subnet_mask'] = match.group(1)

            # Default Gateway
            elif 'Default Gateway' in line:
                match = re.search(r':\s*(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    current_adapter['gateway'] = match.group(1)

            # DNS Servers
            elif 'DNS Servers' in line:
                match = re.search(r':\s*(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    current_adapter['dns'].append(match.group(1))

            # Additional DNS servers (continuation lines)
            elif re.match(r'^\d+\.\d+\.\d+\.\d+$', line):
                current_adapter['dns'].append(line)

    if current_adapter:
        adapters.append(current_adapter)

    return adapters


def can_reach_host(host: str, port: int = 22, timeout: float = 2.0) -> bool:
    """Check if a host is reachable on a specific port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def is_same_subnet(ip1: str, ip2: str, mask: str) -> bool:
    """Check if two IPs are in the same subnet."""
    try:
        ip1_parts = [int(p) for p in ip1.split('.')]
        ip2_parts = [int(p) for p in ip2.split('.')]
        mask_parts = [int(p) for p in mask.split('.')]

        for i in range(4):
            if (ip1_parts[i] & mask_parts[i]) != (ip2_parts[i] & mask_parts[i]):
                return False
        return True
    except Exception:
        return False


def detect_network_settings(target_ip: str = "192.168.1.1") -> Optional[NetworkSettings]:
    """
    Detect network settings from the adapter that can reach the target IP.

    Args:
        target_ip: The IP address of the firewall (default factory IP)

    Returns:
        NetworkSettings object or None if no suitable adapter found
    """
    try:
        output = run_ipconfig()
        adapters = parse_ipconfig_output(output)

        # First, try to find an adapter in the same subnet as target
        target_prefix = '.'.join(target_ip.split('.')[:3])

        for adapter in adapters:
            if not adapter.get('ips'):
                continue

            for ip in adapter['ips']:
                # Check if this IP is in a similar range to the target
                ip_prefix = '.'.join(ip.split('.')[:3])
                if ip_prefix == target_prefix:
                    subnet_mask = adapter.get('subnet_mask', '255.255.255.0')
                    gateway = adapter.get('gateway', f'{target_prefix}.254')
                    dns_servers = adapter.get('dns', ['8.8.8.8', '8.8.4.4'])

                    # Filter out empty or invalid DNS entries
                    dns_servers = [d for d in dns_servers if d and re.match(r'^\d+\.\d+\.\d+\.\d+$', d)]
                    if not dns_servers:
                        dns_servers = ['8.8.8.8', '8.8.4.4']

                    return NetworkSettings(
                        subnet_mask=subnet_mask,
                        gateway=gateway,
                        dns_servers=dns_servers[:2],  # Limit to 2 DNS servers
                        local_ip=ip,
                        adapter_name=adapter['name']
                    )

        # If no adapter in same subnet, return defaults
        return NetworkSettings(
            subnet_mask='255.255.255.0',
            gateway=f'{target_prefix}.254',
            dns_servers=['8.8.8.8', '8.8.4.4'],
            local_ip='',
            adapter_name='(Not detected)'
        )

    except Exception as e:
        # Return sensible defaults on error
        return NetworkSettings(
            subnet_mask='255.255.255.0',
            gateway='192.168.1.254',
            dns_servers=['8.8.8.8', '8.8.4.4'],
            local_ip='',
            adapter_name=f'(Detection failed: {e})'
        )


def get_default_gateway_for_ip(ip: str) -> str:
    """Generate a default gateway IP based on the target IP (assumes .254)."""
    parts = ip.split('.')
    if len(parts) == 4:
        parts[3] = '254'
        return '.'.join(parts)
    return '192.168.1.254'
