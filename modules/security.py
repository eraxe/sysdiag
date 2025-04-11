#!/usr/bin/env python3
"""
Security related diagnostic modules.
"""

import os
import re
from typing import Dict

from .base import DiagnosticModule


class SecurityInfoModule(DiagnosticModule):
    """Module for security information diagnostics."""

    def __init__(self):
        super().__init__(
            "security_info",
            "Security Information"
        )
        self.subsections = {
            "firewall_status": True,
            "selinux_apparmor": True,
            "security_updates": True,
            "auth_logs": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["firewall_status"]:
            # Check various firewall implementations

            # iptables
            iptables = self.safe_run_command(["sudo", "iptables", "-L", "-n", "-v"])

            # firewalld (if available)
            firewalld = self.safe_run_command(["sudo", "firewall-cmd", "--list-all"])

            # ufw (if available)
            ufw = self.safe_run_command(["sudo", "ufw", "status", "verbose"])

            # nftables (if available)
            nftables = self.safe_run_command(["sudo", "nft", "list", "ruleset"])

            # Determine which firewall is active
            active_firewall = "Unknown/None"
            if "Error" not in iptables and iptables.strip() and not all(chain in iptables for chain in
                                                                        ["Chain INPUT (policy ACCEPT)",
                                                                         "Chain FORWARD (policy ACCEPT)",
                                                                         "Chain OUTPUT (policy ACCEPT)"]):
                active_firewall = "iptables"
            elif "Error" not in firewalld and "not running" not in firewalld:
                active_firewall = "firewalld"
            elif "Error" not in ufw and "Status: active" in ufw:
                active_firewall = "ufw"
            elif "Error" not in nftables and nftables.strip():
                active_firewall = "nftables"

            results[
                "firewall_status"] = f"Active Firewall: {active_firewall}\n\niptables Rules:\n{iptables}\n\nfirewalld Configuration:\n{firewalld}\n\nUFW Status:\n{ufw}\n\nnftables Ruleset:\n{nftables}"

        if self.subsections["selinux_apparmor"]:
            # Check SELinux status
            selinux_status = self.safe_run_command(["getenforce"])
            if "Error" in selinux_status:
                selinux_status = self.safe_read_file("/sys/fs/selinux/enforce")
                if "Error" in selinux_status:
                    selinux_status = "SELinux not installed/enabled"

            # Check for SELinux denials
            selinux_denials = "N/A"
            if "SELinux not installed/enabled" not in selinux_status:
                selinux_denials = self.safe_run_command(["sudo", "ausearch", "-m", "avc", "-ts", "today"],
                                                        trim_lines=20)
                if "Error" in selinux_denials:
                    selinux_denials = self.safe_run_command(["sudo", "grep", "denied", "/var/log/audit/audit.log"],
                                                            trim_lines=20)

            # Check AppArmor status
            apparmor_status = self.safe_run_command(["aa-status"])
            if "Error" in apparmor_status:
                apparmor_status = self.safe_read_file("/sys/kernel/security/apparmor/profiles")
                if "Error" in apparmor_status:
                    apparmor_status = "AppArmor not installed/enabled"

            # Check for AppArmor denials
            apparmor_denials = "N/A"
            if "AppArmor not installed/enabled" not in apparmor_status:
                apparmor_denials = self.safe_run_command(["sudo", "grep", "apparmor=\"DENIED\"", "/var/log/syslog"],
                                                         trim_lines=20)
                if "Error" in apparmor_denials or not apparmor_denials.strip():
                    apparmor_denials = self.safe_run_command(
                        ["sudo", "grep", "apparmor=\"DENIED\"", "/var/log/kern.log"],
                        trim_lines=20)

            results[
                "selinux_apparmor"] = f"SELinux Status:\n{selinux_status}\n\nSELinux Denials:\n{selinux_denials}\n\nAppArmor Status:\n{apparmor_status}\n\nAppArmor Denials:\n{apparmor_denials}"

        if self.subsections["security_updates"]:
            # Check for different package managers

            # For Debian/Ubuntu systems
            apt_updates = self.safe_run_command(["apt", "list", "--upgradable"],
                                                filter_func=lambda line: "security" in line.lower())

            # For Red Hat/CentOS/Fedora systems
            yum_updates = self.safe_run_command(["yum", "list", "updates", "--security"])

            # Check when was the last update
            last_update = "Unknown"

            # For Debian/Ubuntu
            if os.path.exists("/var/log/apt/history.log"):
                apt_history = self.safe_read_file("/var/log/apt/history.log",
                                                  filter_func=lambda line: "Start-Date:" in line or "Upgrade:" in line)
                if apt_history:
                    last_update = "Debian/Ubuntu: Last APT actions:\n" + apt_history

            # For Red Hat/CentOS
            elif os.path.exists("/var/log/yum.log"):
                yum_history = self.safe_read_file("/var/log/yum.log", trim_lines=20)
                if yum_history:
                    last_update = "Red Hat/CentOS: Last YUM actions:\n" + yum_history

            results[
                "security_updates"] = f"Available Security Updates (APT):\n{apt_updates}\n\nAvailable Security Updates (YUM):\n{yum_updates}\n\nLast Update Information:\n{last_update}"

        if self.subsections["auth_logs"]:
            # Extract failed login attempts
            auth_log_paths = [
                "/var/log/auth.log",
                "/var/log/secure"
            ]

            failed_logins = "No auth logs found"
            for path in auth_log_paths:
                if os.path.exists(path):
                    failed_login_content = self.safe_read_file(path,
                                                               filter_func=lambda line: "Failed password" in line or
                                                                                        "authentication failure" in line or
                                                                                        "Invalid user" in line,
                                                               trim_lines=20)
                    if failed_login_content:
                        failed_logins = failed_login_content
                        break

            # Show sudo usage patterns
            sudo_usage = "No sudo logs found"
            for path in auth_log_paths:
                if os.path.exists(path):
                    sudo_content = self.safe_read_file(path,
                                                       filter_func=lambda line: "sudo:" in line,
                                                       trim_lines=20)
                    if sudo_content:
                        sudo_usage = sudo_content
                        break

            # Check for unusual access patterns
            unusual_access = "No unusual access patterns found"
            for path in auth_log_paths:
                if os.path.exists(path):
                    unusual_content = self.safe_read_file(path,
                                                          filter_func=lambda line: ("unrecognized" in line.lower() or
                                                                                    "invalid" in line.lower() or
                                                                                    "unauthorized" in line.lower() or
                                                                                    "not allowed" in line.lower()) and
                                                                                   not "Failed password" in line and
                                                                                   not "authentication failure" in line,
                                                          trim_lines=20)
                    if unusual_content:
                        unusual_access = unusual_content
                        break

            results[
                "auth_logs"] = f"Failed Login Attempts:\n{failed_logins}\n\nSudo Usage:\n{sudo_usage}\n\nUnusual Access Patterns:\n{unusual_access}"

        return results


class UserAccountModule(DiagnosticModule):
    """Module for user account information diagnostics."""

    def __init__(self):
        super().__init__(
            "user_account",
            "User Account Information"
        )
        self.subsections = {
            "user_listing": True,
            "login_history": True,
            "privilege_config": True,
            "resource_limits": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["user_listing"]:
            # Display users and their details
            passwd_entries = self.safe_read_file("/etc/passwd",
                                                 filter_func=lambda line: not line.startswith("#") and
                                                                          not "/nologin" in line and
                                                                          not "/false" in line)

            # Show groups
            group_entries = self.safe_read_file("/etc/group",
                                                filter_func=lambda line: not line.startswith("#"))

            # Extract root and sudo groups
            sudo_groups = self.safe_read_file("/etc/group",
                                              filter_func=lambda
                                                  line: "sudo" in line or "wheel" in line or "admin" in line)

            # Check password aging policies
            aging_policies = self.safe_run_command(["grep", "^PASS_", "/etc/login.defs"],
                                                   filter_func=lambda line: not line.startswith("#"))

            results[
                "user_listing"] = f"User Accounts:\n{passwd_entries}\n\nGroup Memberships:\n{group_entries}\n\nAdministrative Groups:\n{sudo_groups}\n\nPassword Aging Policies:\n{aging_policies}"

        if self.subsections["login_history"]:
            # Display recent logins
            last_output = self.safe_run_command(["last", "-n", "20"])

            # Check failed login attempts
            failed_logins = self.safe_run_command(["lastb", "-n", "20"])
            if "Error" in failed_logins:
                # lastb might not be available, try to use auth.log
                failed_logins = self.safe_run_command(["grep", "Failed password", "/var/log/auth.log"],
                                                      trim_lines=20)
                if "Error" in failed_logins:
                    failed_logins = self.safe_run_command(["grep", "Failed password", "/var/log/secure"],
                                                          trim_lines=20)

            # Show currently logged-in users
            current_users = self.safe_run_command(["who"])

            results[
                "login_history"] = f"Recent Logins:\n{last_output}\n\nFailed Login Attempts:\n{failed_logins}\n\nCurrently Logged In Users:\n{current_users}"

        if self.subsections["privilege_config"]:
            # Examine sudo configuration
            sudo_config = self.safe_run_command(["sudo", "cat", "/etc/sudoers"],
                                                filter_func=lambda line: not line.startswith("#") and line.strip())
            if "Error" in sudo_config:
                sudo_config = "Unable to view sudoers file directly"

                # Check sudoers.d directory
                if os.path.exists("/etc/sudoers.d"):
                    sudo_d_files = self.safe_run_command(["sudo", "ls", "-la", "/etc/sudoers.d"])
                    sudo_config += f"\n\nSudoers.d directory contents:\n{sudo_d_files}"

            # Check for SUID/SGID binaries
            suid_binaries = self.safe_run_command(
                ["sudo", "find", "/", "-path", "/proc", "-prune", "-o", "-type", "f", "-perm", "-4000", "-ls"],
                trim_lines=20)

            sgid_binaries = self.safe_run_command(
                ["sudo", "find", "/", "-path", "/proc", "-prune", "-o", "-type", "f", "-perm", "-2000", "-ls"],
                trim_lines=20)

            # Verify PAM configuration
            pam_config = self.safe_read_file("/etc/pam.d/common-auth",
                                             filter_func=lambda line: not line.startswith("#") and line.strip())
            if "Error" in pam_config:
                pam_config = self.safe_read_file("/etc/pam.d/system-auth",
                                                 filter_func=lambda line: not line.startswith("#") and line.strip())

            results[
                "privilege_config"] = f"Sudo Configuration:\n{sudo_config}\n\nSUID Binaries (first 20):\n{suid_binaries}\n\nSGID Binaries (first 20):\n{sgid_binaries}\n\nPAM Authentication Configuration:\n{pam_config}"

        if self.subsections["resource_limits"]:
            # Display ulimit settings for the current process
            ulimit_output = self.safe_run_command(["ulimit", "-a"])

            # Check systemd user slice configurations
            systemd_user_slice = self.safe_run_command(["systemctl", "show", "user.slice"])

            # Show resource usage by user
            resource_usage = self.safe_run_command(
                ["ps", "-e", "-o", "user,pcpu,pmem,vsz,time,comm", "--sort", "-pcpu"],
                trim_lines=20)

            results[
                "resource_limits"] = f"Ulimit Settings:\n{ulimit_output}\n\nSystemd User Slice Configuration:\n{systemd_user_slice}\n\nResource Usage by Process/User:\n{resource_usage}"

        return results