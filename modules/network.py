#!/usr/bin/env python3
"""
Network related diagnostic modules.
"""

import os
import re
from typing import Dict

from .base import DiagnosticModule


class NetworkConfigModule(DiagnosticModule):
    """Module for network configuration diagnostics."""

    def __init__(self):
        super().__init__(
            "network_config",
            "Network Configuration"
        )
        self.subsections = {
            "interface_status": True,
            "routing_info": True,
            "dns_config": True,
            "network_services": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["interface_status"]:
            # List all network interfaces
            ip_addr = self.safe_run_command(["ip", "addr"])

            # Show interface statistics
            ip_stats = self.safe_run_command(["ip", "-s", "link"])

            # Check link status and speed
            ethtool_results = []

            # Extract interface names from ip addr output
            interface_pattern = re.compile(r'^\d+:\s+([^:@]+)')
            interfaces = []

            for line in ip_addr.splitlines():
                match = interface_pattern.match(line)
                if match and not match.group(1) == 'lo':
                    interfaces.append(match.group(1))

            # Get ethtool info for each interface
            for iface in interfaces:
                ethtool_output = self.safe_run_command(["ethtool", iface])
                if not "Error" in ethtool_output:
                    ethtool_results.append(f"=== Interface {iface} ===\n{ethtool_output}")

            results[
                "interface_status"] = f"Network Interfaces:\n{ip_addr}\n\nInterface Statistics:\n{ip_stats}\n\nLink Status and Speed:\n" + "\n".join(
                ethtool_results)

        if self.subsections["routing_info"]:
            # Display routing tables
            ip_route = self.safe_run_command(["ip", "route"])

            # Check default gateway
            default_gateway = self.safe_run_command(["ip", "route", "show", "default"])

            # Check for routing conflicts
            ip_route_all = self.safe_run_command(["ip", "route", "show", "table", "all"])

            results[
                "routing_info"] = f"Routing Table:\n{ip_route}\n\nDefault Gateway:\n{default_gateway}\n\nAll Routing Tables:\n{ip_route_all}"

        if self.subsections["dns_config"]:
            # Analyze resolv.conf
            resolv_conf = self.safe_read_file("/etc/resolv.conf")

            # Check systemd-resolved settings if available
            systemd_resolved = self.safe_run_command(["systemd-resolve", "--status"])

            # Test DNS resolution functionality
            dns_test = self.safe_run_command(["dig", "google.com", "+short"])
            if "Error" in dns_test:
                dns_test = self.safe_run_command(["nslookup", "google.com"])

            # Check hosts file
            hosts_file = self.safe_read_file("/etc/hosts")

            results[
                "dns_config"] = f"Resolver Configuration:\n{resolv_conf}\n\nSystemd-resolved Status:\n{systemd_resolved}\n\nDNS Resolution Test:\n{dns_test}\n\nHosts File:\n{hosts_file}"

        if self.subsections["network_services"]:
            # Check listening ports
            ss_output = self.safe_run_command(["ss", "-tuln"])

            # Check network service status
            network_services = self.safe_run_command(["systemctl", "list-units", "--type=service", "--state=active"],
                                                     filter_func=lambda line: any(
                                                         term in line.lower() for term in
                                                         ["network", "firewall", "ssh", "http", "ftp", "dns", "dhcp",
                                                          "proxy"]
                                                     ))

            # Display active connections
            active_connections = self.safe_run_command(["ss", "-tu", "state", "established"])

            results[
                "network_services"] = f"Listening Ports:\n{ss_output}\n\nActive Network Services:\n{network_services}\n\nActive Connections:\n{active_connections}"

        return results