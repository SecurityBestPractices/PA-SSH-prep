"""Tests for src/network_detect.py"""

import pytest
from src.network_detect import (
    parse_ipconfig_output,
    is_same_subnet,
    get_default_gateway_for_ip,
    NetworkSettings,
)


class TestParseIpconfigOutput:
    """Tests for parse_ipconfig_output function."""

    def test_parse_basic_adapter(self):
        output = """
Windows IP Configuration

Ethernet adapter Ethernet:

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 192.168.1.100
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
"""
        adapters = parse_ipconfig_output(output)
        assert len(adapters) >= 1

        # Find the Ethernet adapter
        eth_adapter = None
        for adapter in adapters:
            if 'Ethernet' in adapter.get('name', ''):
                eth_adapter = adapter
                break

        assert eth_adapter is not None
        assert '192.168.1.100' in eth_adapter.get('ips', [])
        assert eth_adapter.get('subnet_mask') == '255.255.255.0'
        assert eth_adapter.get('gateway') == '192.168.1.1'

    def test_parse_adapter_with_dns(self):
        output = """
Ethernet adapter Ethernet:

   IPv4 Address. . . . . . . . . . . : 10.0.0.50
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 10.0.0.1
   DNS Servers . . . . . . . . . . . : 8.8.8.8
                                       8.8.4.4
"""
        adapters = parse_ipconfig_output(output)
        eth_adapter = [a for a in adapters if 'Ethernet' in a.get('name', '')][0]

        assert '8.8.8.8' in eth_adapter.get('dns', [])
        assert '8.8.4.4' in eth_adapter.get('dns', [])

    def test_parse_multiple_adapters(self):
        output = """
Ethernet adapter Ethernet:

   IPv4 Address. . . . . . . . . . . : 192.168.1.100
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1

Wireless LAN adapter Wi-Fi:

   IPv4 Address. . . . . . . . . . . : 192.168.2.50
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.2.1
"""
        adapters = parse_ipconfig_output(output)
        # Should have at least 2 adapters
        adapter_names = [a.get('name', '') for a in adapters]
        assert any('Ethernet' in name for name in adapter_names)
        assert any('Wi-Fi' in name for name in adapter_names)

    def test_parse_empty_output(self):
        output = ""
        adapters = parse_ipconfig_output(output)
        assert adapters == []


class TestIsSameSubnet:
    """Tests for is_same_subnet function."""

    def test_same_subnet_24(self):
        assert is_same_subnet("192.168.1.1", "192.168.1.100", "255.255.255.0") is True
        assert is_same_subnet("192.168.1.1", "192.168.1.254", "255.255.255.0") is True

    def test_different_subnet_24(self):
        assert is_same_subnet("192.168.1.1", "192.168.2.1", "255.255.255.0") is False
        assert is_same_subnet("10.0.0.1", "192.168.1.1", "255.255.255.0") is False

    def test_same_subnet_16(self):
        assert is_same_subnet("172.16.0.1", "172.16.255.254", "255.255.0.0") is True

    def test_different_subnet_16(self):
        assert is_same_subnet("172.16.0.1", "172.17.0.1", "255.255.0.0") is False

    def test_same_subnet_8(self):
        assert is_same_subnet("10.0.0.1", "10.255.255.254", "255.0.0.0") is True

    def test_invalid_input(self):
        # Should return False for invalid input rather than raising
        assert is_same_subnet("invalid", "192.168.1.1", "255.255.255.0") is False
        assert is_same_subnet("192.168.1.1", "invalid", "255.255.255.0") is False


class TestGetDefaultGatewayForIP:
    """Tests for get_default_gateway_for_ip function."""

    def test_standard_ip(self):
        assert get_default_gateway_for_ip("192.168.1.100") == "192.168.1.254"
        assert get_default_gateway_for_ip("10.0.0.50") == "10.0.0.254"
        assert get_default_gateway_for_ip("172.16.5.10") == "172.16.5.254"

    def test_gateway_ip(self):
        # Even if given a .1 or .254, should still return .254
        assert get_default_gateway_for_ip("192.168.1.1") == "192.168.1.254"
        assert get_default_gateway_for_ip("192.168.1.254") == "192.168.1.254"

    def test_invalid_ip(self):
        # Should return default for invalid input
        result = get_default_gateway_for_ip("invalid")
        assert result == "192.168.1.254"


class TestNetworkSettings:
    """Tests for NetworkSettings dataclass."""

    def test_create_network_settings(self):
        settings = NetworkSettings(
            subnet_mask="255.255.255.0",
            gateway="192.168.1.1",
            dns_servers=["8.8.8.8", "8.8.4.4"],
            local_ip="192.168.1.100",
            adapter_name="Ethernet"
        )

        assert settings.subnet_mask == "255.255.255.0"
        assert settings.gateway == "192.168.1.1"
        assert settings.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert settings.local_ip == "192.168.1.100"
        assert settings.adapter_name == "Ethernet"

    def test_network_settings_with_single_dns(self):
        settings = NetworkSettings(
            subnet_mask="255.255.255.0",
            gateway="10.0.0.1",
            dns_servers=["8.8.8.8"],
            local_ip="10.0.0.50",
            adapter_name="Wi-Fi"
        )

        assert len(settings.dns_servers) == 1
        assert settings.dns_servers[0] == "8.8.8.8"
