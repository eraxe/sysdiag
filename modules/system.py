#!/usr/bin/env python3
"""
System related diagnostic modules.
"""

import os
import re
from typing import Dict

from .base import DiagnosticModule


class KernelLogsModule(DiagnosticModule):
    """Module for kernel boot and system logs."""

    def __init__(self):
        super().__init__(
            "kernel_logs",
            "Kernel Boot & System Logs"
        )
        self.subsections = {
            "dmesg": True,
            "journalctl": True,
            "boot_log": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["dmesg"]:
            # Get dmesg with errors and warnings only
            dmesg_errors = self.safe_run_command(
                ["dmesg", "--level=err,warn,emerg,alert,crit"],
                trim_lines=20
            )
            results["dmesg"] = dmesg_errors

        if self.subsections["journalctl"]:
            # Get boot logs with errors only
            journal_boot = self.safe_run_command(
                ["journalctl", "-b", "-p", "err..emerg"],
                trim_lines=20
            )
            results["journalctl"] = journal_boot

        if self.subsections["boot_log"]:
            # Try different log files that might contain boot information
            boot_log_paths = [
                "/var/log/boot.log",
                "/var/log/dmesg",
                "/var/log/syslog"
            ]

            for path in boot_log_paths:
                if os.path.exists(path):
                    log_content = self.safe_read_file(path, trim_lines=20,
                                                      filter_func=lambda line: any(
                                                          level in line.lower() for level in
                                                          ["error", "warning", "fail", "critical"]
                                                      ))
                    results[f"boot_log_{os.path.basename(path)}"] = log_content

            if not any(key.startswith("boot_log_") for key in results.keys()):
                results["boot_log"] = "No boot log files found"

        return results


class HardwareInfoModule(DiagnosticModule):
    """Module for hardware and driver information."""

    def __init__(self):
        super().__init__(
            "hardware_info",
            "Hardware & Driver Information"
        )
        self.subsections = {
            "lspci": True,
            "lsusb": True,
            "drivers": True,
            "cpu_info": True,
            "memory_diagnostics": True,
            "cpu_status": True,
            "pci_usb_issues": True,
            "peripheral_status": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["lspci"]:
            # Get PCI devices with kernel drivers
            results["lspci"] = self.safe_run_command(["lspci", "-k"])

        if self.subsections["lsusb"]:
            # Get USB devices
            results["lsusb"] = self.safe_run_command(["lsusb"])

        if self.subsections["drivers"]:
            # Get loaded kernel modules
            loaded_modules = self.safe_run_command(["lsmod"],
                                                   filter_func=lambda line: not line.startswith(
                                                       "Module") and line.strip())

            # Get any driver errors from dmesg
            driver_errors = self.safe_run_command(
                ["dmesg"],
                filter_func=lambda line: any(
                    error in line.lower() for error in
                    ["driver", "firmware", "module"] +
                    ["error", "fail", "warn"]
                ),
                trim_lines=20
            )

            results["drivers"] = f"Loaded Modules:\n{loaded_modules}\n\nDriver Messages:\n{driver_errors}"

        if self.subsections["cpu_info"]:
            # Get CPU information
            cpu_info = self.safe_read_file("/proc/cpuinfo",
                                           filter_func=lambda line: line.startswith("model name") or
                                                                    line.startswith("cpu MHz") or
                                                                    line.startswith("processor"))
            results["cpu_info"] = cpu_info

        # Additional subsections
        if self.subsections["memory_diagnostics"]:
            # Check for memory errors in logs
            memory_errors = self.safe_run_command(
                ["dmesg"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["memory", "ram", "mem", "oom", "out of memory"]
                ) and any(
                    level in line.lower() for level in
                    ["error", "fail", "warn", "crit", "alert"]
                ),
                trim_lines=20
            )

            # Get memory usage statistics
            mem_info = self.safe_read_file("/proc/meminfo")
            swap_info = self.safe_run_command(["swapon", "--show"])
            vmstat = self.safe_run_command(["vmstat"])

            results[
                "memory_diagnostics"] = f"Memory Error Messages:\n{memory_errors}\n\nMemory Info:\n{mem_info}\n\nSwap Info:\n{swap_info}\n\nVMStat:\n{vmstat}"

        if self.subsections["cpu_status"]:
            # Check CPU frequency scaling and throttling
            cpu_freq = self.safe_run_command(["cat", "/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"],
                                             filter_func=lambda line: line.strip())

            # Check thermal status
            thermal = self.safe_run_command(["cat", "/sys/class/thermal/thermal_zone*/temp"],
                                            filter_func=lambda line: line.strip())

            # Get CPU load average
            loadavg = self.safe_read_file("/proc/loadavg")

            # Get CPU info from top
            top_cpu = self.safe_run_command(["top", "-bn1"],
                                            filter_func=lambda line: "Cpu(s)" in line or "top -" in line)

            results[
                "cpu_status"] = f"CPU Frequency:\n{cpu_freq}\n\nThermal Status:\n{thermal}\n\nLoad Average:\n{loadavg}\n\nCPU Utilization:\n{top_cpu}"

        if self.subsections["pci_usb_issues"]:
            # Check for hardware conflicts
            pci_conflicts = self.safe_run_command(["dmesg"],
                                                  filter_func=lambda line: (
                                                                                   "pci" in line.lower() or "usb" in line.lower()) and
                                                                           any(term in line.lower() for term in
                                                                               ["conflict", "error", "fail", "warn"]),
                                                  trim_lines=20)

            # Check for IRQ sharing
            interrupts = self.safe_read_file("/proc/interrupts")

            # Check for missing firmware
            missing_firmware = self.safe_run_command(["dmesg"],
                                                     filter_func=lambda line: "firmware" in line.lower() and
                                                                              any(term in line.lower() for term in
                                                                                  ["missing", "not found", "fail",
                                                                                   "error"]),
                                                     trim_lines=10)

            results[
                "pci_usb_issues"] = f"PCI/USB Conflicts:\n{pci_conflicts}\n\nInterrupts:\n{interrupts}\n\nMissing Firmware:\n{missing_firmware}"

        if self.subsections["peripheral_status"]:
            # Check input devices
            input_devices = self.safe_run_command(["ls", "-la", "/dev/input"])

            # Check SMART status if available
            smart_status = self.safe_run_command(["sudo", "smartctl", "--scan"])
            if "Error" not in smart_status:
                # If smartctl is available, try to get SMART data for the first drive
                smart_data = self.safe_run_command(["sudo", "smartctl", "-a", "/dev/sda"])
                smart_status += f"\n\nSMART Data for /dev/sda:\n{smart_data}"

            # Check hardware sensors if available
            sensors = self.safe_run_command(["sensors"])

            results[
                "peripheral_status"] = f"Input Devices:\n{input_devices}\n\nStorage SMART Status:\n{smart_status}\n\nHardware Sensors:\n{sensors}"

        return results


class CustomScriptsModule(DiagnosticModule):
    """Module for custom scripts and environment variables."""

    def __init__(self):
        super().__init__(
            "custom_scripts",
            "Custom Scripts & Environmental Variables"
        )
        self.subsections = {
            "rc_scripts": True,
            "env_vars": True,
            "crontabs": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["rc_scripts"]:
            # Check for custom scripts in various locations
            rc_locations = [
                "/etc/rc.local",
                "/etc/rc.d/",
                "/etc/init.d/",
                "/etc/systemd/system/"
            ]

            script_findings = []

            for location in rc_locations:
                if os.path.exists(location):
                    if os.path.isdir(location):
                        # List non-standard service files
                        try:
                            files = os.listdir(location)
                            custom_files = [
                                f for f in files
                                if not f.startswith("README") and
                                   not f.startswith(".") and
                                   not f in ["multi-user.target", "default.target", "sysinit.target"]
                            ]

                            if custom_files:
                                script_findings.append(f"Custom files in {location}:\n" + "\n".join(custom_files))

                                # Sample content from first 5 custom files
                                for i, file in enumerate(custom_files[:5]):
                                    path = os.path.join(location, file)
                                    if os.path.isfile(path):
                                        content = self.safe_read_file(path, trim_lines=10)
                                        script_findings.append(f"Sample from {path}:\n{content}\n")
                        except Exception as e:
                            script_findings.append(f"Error listing {location}: {str(e)}")
                    else:
                        # Read content of specific files
                        content = self.safe_read_file(location, trim_lines=20)
                        script_findings.append(f"Content of {location}:\n{content}")

            if script_findings:
                results["rc_scripts"] = "\n\n".join(script_findings)
            else:
                results["rc_scripts"] = "No custom startup scripts found"

        if self.subsections["env_vars"]:
            # Get system-wide environment settings
            env_files = [
                "/etc/environment",
                "/etc/profile",
                "/etc/profile.d/"
            ]

            env_findings = []

            for location in env_files:
                if os.path.exists(location):
                    if os.path.isdir(location):
                        try:
                            files = os.listdir(location)
                            env_contents = []

                            for file in files:
                                if file.endswith(".sh"):
                                    path = os.path.join(location, file)
                                    content = self.safe_read_file(path,
                                                                  filter_func=lambda line: not line.strip().startswith(
                                                                      "#") and "=" in line)
                                    if content.strip():
                                        env_contents.append(f"=== {file} ===\n{content}")

                            if env_contents:
                                env_findings.append(f"Environment files in {location}:\n" + "\n".join(env_contents))
                        except Exception as e:
                            env_findings.append(f"Error reading {location}: {str(e)}")
                    else:
                        content = self.safe_read_file(location,
                                                      filter_func=lambda line: not line.strip().startswith(
                                                          "#") and "=" in line)
                        if content.strip():
                            env_findings.append(f"Environment settings in {location}:\n{content}")

            # Also include current user's environment variables
            env_vars = self.safe_run_command(["env"],
                                             filter_func=lambda line: any(
                                                 var in line for var in
                                                 ["PATH", "LD_LIBRARY", "HOME", "USER", "SHELL", "TERM"]
                                             ))

            env_findings.append(f"Current environment variables:\n{env_vars}")

            if env_findings:
                results["env_vars"] = "\n\n".join(env_findings)
            else:
                results["env_vars"] = "No significant environment variables found"

        if self.subsections["crontabs"]:
            # Check system crontabs
            system_crontab = self.safe_run_command(["sudo", "cat", "/etc/crontab"])

            # Check for user crontabs
            user_crontabs = self.safe_run_command(["sudo", "ls", "-la", "/var/spool/cron/"])

            results["crontabs"] = f"System Crontab:\n{system_crontab}\n\nUser Crontabs:\n{user_crontabs}"

        return results


class RecoveryDiagnosticsModule(DiagnosticModule):
    """Module for recovery and emergency diagnostics."""

    def __init__(self):
        super().__init__(
            "recovery_diagnostics",
            "Recovery & Emergency Diagnostics"
        )
        self.subsections = {
            "rescue_log": True,
            "emergency_status": True,
            "systemd_errors": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["rescue_log"]:
            # Check for emergency or rescue mode logs
            rescue_logs = self.safe_run_command(
                ["journalctl", "-b", "-o", "short", "-u", "emergency.service", "-u", "rescue.service"],
                trim_lines=20
            )

            if "No entries" in rescue_logs:
                results["rescue_log"] = "No emergency or rescue mode logs found"
            else:
                results["rescue_log"] = rescue_logs

        if self.subsections["emergency_status"]:
            # Check systemd for failed units
            failed_units = self.safe_run_command(["systemctl", "--failed"])
            results["emergency_status"] = f"Failed Units:\n{failed_units}"

        if self.subsections["systemd_errors"]:
            # Get critical systemd errors
            systemd_errors = self.safe_run_command(
                ["journalctl", "-p", "err..emerg", "-u", "systemd"],
                trim_lines=20
            )
            results["systemd_errors"] = systemd_errors

        return results


class SystemServiceStatusModule(DiagnosticModule):
    """Module for system service status diagnostics."""

    def __init__(self):
        super().__init__(
            "system_service_status",
            "System Service Status"
        )
        self.subsections = {
            "systemd_unit_status": True,
            "service_logs": True,
            "system_targets": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["systemd_unit_status"]:
            # Check for failed systemd units
            failed_units = self.safe_run_command(["systemctl", "--failed"])

            # Analyze problematic services
            if "0 loaded units listed" not in failed_units:
                # Get detailed status for failed services
                failed_services = []
                for line in failed_units.splitlines():
                    if "UNIT" not in line and "LOAD" not in line and "●" not in line and line.strip():
                        service_name = line.split()[0]
                        status = self.safe_run_command(["systemctl", "status", service_name])
                        failed_services.append(f"=== {service_name} ===\n{status}")

                problematic_services = "\n\n".join(failed_services)
            else:
                problematic_services = "No failed services found"

            # Check service dependencies
            service_deps = self.safe_run_command(["systemctl", "list-dependencies", "multi-user.target"],
                                                 filter_func=lambda line: "●" in line)

            results[
                "systemd_unit_status"] = f"Failed Units:\n{failed_units}\n\nProblematic Services:\n{problematic_services}\n\nService Dependencies:\n{service_deps}"

        if self.subsections["service_logs"]:
            # Extract critical errors from service logs
            service_critical_errors = self.safe_run_command(
                ["journalctl", "-p", "err..emerg", "--since", "today"],
                trim_lines=30
            )

            # Check service startup sequences
            startup_logs = self.safe_run_command(
                ["journalctl", "-b", "-p", "info..err", "-u", "systemd"],
                filter_func=lambda line: "Starting" in line or "Started" in line or "Failed" in line,
                trim_lines=20
            )

            # Monitor resource usage by services
            resource_usage = self.safe_run_command(
                ["systemd-cgtop", "-n", "1"],
                trim_lines=20
            )

            results[
                "service_logs"] = f"Critical Service Errors:\n{service_critical_errors}\n\nService Startup Sequences:\n{startup_logs}\n\nService Resource Usage:\n{resource_usage}"

        if self.subsections["system_targets"]:
            # Verify active systemd targets
            active_targets = self.safe_run_command(["systemctl", "list-units", "--type=target"])

            # Check default target
            default_target = self.safe_run_command(["systemctl", "get-default"])

            # Analyze dependencies between targets
            target_deps = self.safe_run_command(["systemctl", "list-dependencies", "default.target"])

            results[
                "system_targets"] = f"Active Targets:\n{active_targets}\n\nDefault Target:\n{default_target}\n\nTarget Dependencies:\n{target_deps}"

        return results


class VirtualizationContainerModule(DiagnosticModule):
    """Module for virtualization and container status diagnostics."""

    def __init__(self):
        super().__init__(
            "virtualization_container",
            "Virtualization & Container Status"
        )
        self.subsections = {
            "vm_status": True,
            "container_status": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["vm_status"]:
            # Check if this is a VM or a host running VMs
            virt_type = self.safe_run_command(["systemd-detect-virt"])
            if "none" in virt_type:
                # This might be a host, check for hypervisors
                kvm_modules = self.safe_run_command(["lsmod"],
                                                    filter_func=lambda line: "kvm" in line)

                virsh_list = self.safe_run_command(["virsh", "list", "--all"])

                vm_info = f"This appears to be a physical host.\n\nKVM Modules:\n{kvm_modules}\n\nLibvirt VMs:\n{virsh_list}"
            else:
                # This is a VM, get guest info
                vm_info = f"This is a virtual machine. Virtualization type: {virt_type}"

                # Check for guest agents
                qemu_agent = self.safe_run_command(["pgrep", "qemu-ga"])
                vmware_tools = self.safe_run_command(["pgrep", "vmtoolsd"])

                vm_info += f"\n\nGuest Agents:\nQEMU Guest Agent: {'Running' if qemu_agent and 'Error' not in qemu_agent else 'Not running'}\nVMware Tools: {'Running' if vmware_tools and 'Error' not in vmware_tools else 'Not running'}"

            # Check VM resource allocation and utilization
            vm_resources = self.safe_run_command(["free", "-h"])
            vm_resources += "\n\n" + self.safe_run_command(["lscpu"])

            # Check VM networking
            vm_network = self.safe_run_command(["ip", "addr"])

            results[
                "vm_status"] = f"VM Status:\n{vm_info}\n\nVM Resources:\n{vm_resources}\n\nVM Networking:\n{vm_network}"

        if self.subsections["container_status"]:
            # Check Docker status
            docker_status = self.safe_run_command(["docker", "info"])

            # If docker not found, try podman
            if "Error" in docker_status or "command not found" in docker_status:
                docker_status = self.safe_run_command(["podman", "info"])
                if "Error" in docker_status or "command not found" in docker_status:
                    # Try LXC
                    docker_status = self.safe_run_command(["lxc-ls", "--fancy"])
                    container_type = "LXC" if not "Error" in docker_status and not "command not found" in docker_status else "None detected"
                else:
                    container_type = "Podman"
            else:
                container_type = "Docker"

            # Check container list
            if container_type == "Docker":
                container_list = self.safe_run_command(["docker", "ps", "-a"])
                container_errors = self.safe_run_command(["journalctl"],
                                                         filter_func=lambda line: "docker" in line.lower() and
                                                                                  any(error in line.lower() for error in
                                                                                      ["error", "fail", "exit"]),
                                                         trim_lines=20)
                container_resources = self.safe_run_command(["docker", "stats", "--no-stream", "--all"])

            elif container_type == "Podman":
                container_list = self.safe_run_command(["podman", "ps", "-a"])
                container_errors = self.safe_run_command(["journalctl"],
                                                         filter_func=lambda line: "podman" in line.lower() and
                                                                                  any(error in line.lower() for error in
                                                                                      ["error", "fail", "exit"]),
                                                         trim_lines=20)
                container_resources = self.safe_run_command(["podman", "stats", "--no-stream", "--all"])

            elif container_type == "LXC":
                container_list = self.safe_run_command(["lxc-ls", "--fancy"])
                container_errors = self.safe_run_command(["journalctl"],
                                                         filter_func=lambda line: "lxc" in line.lower() and
                                                                                  any(error in line.lower() for error in
                                                                                      ["error", "fail", "exit"]),
                                                         trim_lines=20)
                container_resources = "Resource statistics not available for LXC containers through standard commands"

            else:
                container_list = "No container system detected"
                container_errors = "N/A"
                container_resources = "N/A"

            results[
                "container_status"] = f"Container System: {container_type}\n\nContainer List:\n{container_list}\n\nContainer Errors:\n{container_errors}\n\nContainer Resources:\n{container_resources}"

        return results


class LogAnalysisModule(DiagnosticModule):
    """Module for log analysis and monitoring."""

    def __init__(self):
        super().__init__(
            "log_analysis",
            "Log Analysis & Monitoring"
        )
        self.subsections = {
            "consolidated_errors": True,
            "log_rotation": True,
            "system_monitoring": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["consolidated_errors"]:
            # Get all critical errors across logs
            critical_errors = self.safe_run_command(
                ["journalctl", "-p", "err..emerg", "--since", "yesterday"],
                trim_lines=30
            )

            # Extract common error patterns
            error_patterns = {}
            for line in critical_errors.splitlines():
                # Extract error message part
                error_match = re.search(r'error:?\s*([^:]+)', line, re.IGNORECASE)
                if error_match:
                    error_type = error_match.group(1).strip()
                    if error_type in error_patterns:
                        error_patterns[error_type] += 1
                    else:
                        error_patterns[error_type] = 1

            # Format the error patterns
            error_pattern_summary = "Common Error Patterns:\n"
            for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                error_pattern_summary += f"{error}: {count} occurrences\n"

            # Check for correlated errors
            # (This is a simplified approach - full correlation would require more complex analysis)
            correlated_events = self.safe_run_command(
                ["journalctl", "-p", "notice..emerg", "--since", "yesterday"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["start", "stop", "restart", "reload", "shutdown", "boot"]
                ) and any(
                    svc in line.lower() for svc in
                    ["network", "firewall", "service", "daemon", "system"]
                ),
                trim_lines=20
            )

            results[
                "consolidated_errors"] = f"Critical Errors (last 24h):\n{critical_errors}\n\n{error_pattern_summary}\n\nPotentially Correlated Events:\n{correlated_events}"

        if self.subsections["log_rotation"]:
            # Verify log rotation settings
            logrotate_config = "Log Rotation Configuration:\n"

            # Check main config
            main_config = self.safe_read_file("/etc/logrotate.conf",
                                              filter_func=lambda line: not line.startswith("#") and line.strip())

            logrotate_config += f"\n/etc/logrotate.conf:\n{main_config}\n"

            # Check logrotate.d
            if os.path.exists("/etc/logrotate.d"):
                for file in os.listdir("/etc/logrotate.d")[:5]:  # Get first 5 files only
                    file_path = os.path.join("/etc/logrotate.d", file)
                    if os.path.isfile(file_path):
                        content = self.safe_read_file(file_path,
                                                      filter_func=lambda line: not line.startswith(
                                                          "#") and line.strip())
                        logrotate_config += f"\n/etc/logrotate.d/{file}:\n{content}"

            # Check for oversized logs
            big_logs = self.safe_run_command(
                ["find", "/var/log", "-type", "f", "-size", "+100M", "-exec", "ls", "-lh", "{}", ";"]
            )

            # Check log volume and growth
            log_space = self.safe_run_command(["du", "-sh", "/var/log"])

            # Check journal size
            journal_size = self.safe_run_command(["journalctl", "--disk-usage"])

            results[
                "log_rotation"] = f"{logrotate_config}\n\nOversized Logs (>100MB):\n{big_logs}\n\nLog Directory Size:\n{log_space}\n\nJournal Size:\n{journal_size}"

        if self.subsections["system_monitoring"]:
            # Display system uptime
            uptime = self.safe_run_command(["uptime"])

            # Check for system reboots
            reboot_history = self.safe_run_command(["last", "reboot"], trim_lines=10)

            # Check for recurring issues
            recurring_issues = self.safe_run_command(
                ["journalctl", "--since", "1 week ago"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["error", "fail", "critical"]
                ) and any(
                    svc in line.lower() for svc in
                    ["crash", "killed", "terminated", "core dumped", "segfault"]
                ),
                trim_lines=20
            )

            # Check for resource exhaustion
            resource_exhaustion = self.safe_run_command(
                ["journalctl", "--since", "1 week ago"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["out of memory", "no space", "disk full", "cannot allocate", "too many open files"]
                ),
                trim_lines=20
            )

            results[
                "system_monitoring"] = f"System Uptime:\n{uptime}\n\nReboot History:\n{reboot_history}\n\nRecurring Critical Issues:\n{recurring_issues}\n\nResource Exhaustion Events:\n{resource_exhaustion}"

        return results


class PackageManagementModule(DiagnosticModule):
    """Module for package management diagnostics."""

    def __init__(self):
        super().__init__(
            "package_management",
            "Package Management"
        )
        self.subsections = {
            "package_status": True,
            "package_dependencies": True,
            "package_history": True,
            "repository_health": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        # Determine package manager type
        if os.path.exists("/usr/bin/dpkg") or os.path.exists("/bin/dpkg"):
            package_manager = "apt"
        elif os.path.exists("/usr/bin/rpm") or os.path.exists("/bin/rpm"):
            if os.path.exists("/usr/bin/dnf") or os.path.exists("/bin/dnf"):
                package_manager = "dnf"
            else:
                package_manager = "yum"
        elif os.path.exists("/usr/bin/pacman") or os.path.exists("/bin/pacman"):
            package_manager = "pacman"
        else:
            package_manager = "unknown"

        if self.subsections["package_status"]:
            # List installed packages
            if package_manager == "apt":
                # Debian/Ubuntu
                installed_packages = self.safe_run_command(
                    ["dpkg-query", "-W", "-f='${Status} ${Package} ${Version}\\n'"],
                    filter_func=lambda line: "install ok installed" in line,
                    trim_lines=20)

                pending_updates = self.safe_run_command(["apt", "list", "--upgradable"],
                                                        trim_lines=20)

                repo_config = self.safe_read_file("/etc/apt/sources.list",
                                                  filter_func=lambda line: not line.startswith("#") and line.strip())

                # Also check sources.list.d
                if os.path.exists("/etc/apt/sources.list.d"):
                    repo_config += "\n\n/etc/apt/sources.list.d contents:\n"
                    for file in os.listdir("/etc/apt/sources.list.d"):
                        if file.endswith(".list"):
                            content = self.safe_read_file(f"/etc/apt/sources.list.d/{file}",
                                                          filter_func=lambda line: not line.startswith(
                                                              "#") and line.strip())
                            repo_config += f"\n--- {file} ---\n{content}"

            elif package_manager in ["yum", "dnf"]:
                # Red Hat/CentOS/Fedora
                installed_packages = self.safe_run_command([package_manager, "list", "installed"],
                                                           trim_lines=20)

                pending_updates = self.safe_run_command([package_manager, "check-update"],
                                                        trim_lines=20)

                repo_config = self.safe_run_command([package_manager, "repolist", "-v"])

                # Check for repo files
                if os.path.exists("/etc/yum.repos.d"):
                    repo_config += "\n\n/etc/yum.repos.d contents:\n"
                    for file in os.listdir("/etc/yum.repos.d"):
                        if file.endswith(".repo"):
                            content = self.safe_read_file(f"/etc/yum.repos.d/{file}",
                                                          filter_func=lambda line: not line.startswith(
                                                              "#") and line.strip())
                            repo_config += f"\n--- {file} ---\n{content}"

            elif package_manager == "pacman":
                # Arch Linux
                installed_packages = self.safe_run_command(["pacman", "-Q"],
                                                           trim_lines=20)

                pending_updates = self.safe_run_command(["pacman", "-Qu"],
                                                        trim_lines=20)

                repo_config = self.safe_read_file("/etc/pacman.conf",
                                                  filter_func=lambda line: not line.startswith("#") and line.strip())

                # Check for pacman.d
                if os.path.exists("/etc/pacman.d"):
                    repo_config += "\n\n/etc/pacman.d contents:\n"
                    for file in os.listdir("/etc/pacman.d"):
                        content = self.safe_read_file(f"/etc/pacman.d/{file}",
                                                      filter_func=lambda line: not line.startswith(
                                                          "#") and line.strip())
                        repo_config += f"\n--- {file} ---\n{content}"

            else:
                installed_packages = "Unable to determine package manager type"
                pending_updates = "Unable to determine package manager type"
                repo_config = "Unable to determine package manager type"

            results[
                "package_status"] = f"Package Manager: {package_manager}\n\nInstalled Packages (sample):\n{installed_packages}\n\nPending Updates:\n{pending_updates}\n\nRepository Configuration:\n{repo_config}"

        if self.subsections["package_dependencies"]:
            # Check for broken dependencies
            if package_manager == "apt":
                # Debian/Ubuntu
                dependency_check = self.safe_run_command(["apt", "check"],
                                                         filter_func=lambda line: line.strip())
                if not dependency_check.strip():
                    dependency_check = "No broken dependencies found"

                # Check package integrity
                integrity_check = self.safe_run_command(["debsums", "-s"],
                                                        filter_func=lambda line: line.strip())
                if not integrity_check.strip():
                    integrity_check = "No package integrity issues found"
                elif "command not found" in integrity_check:
                    integrity_check = "debsums not installed"

                # Check for orphaned packages
                orphaned_packages = self.safe_run_command(["apt-get", "autoremove", "--dry-run"],
                                                          filter_func=lambda line: "would be removed" in line or
                                                                                   "The following packages will be REMOVED" in line)
                if not orphaned_packages.strip():
                    orphaned_packages = "No orphaned packages found"

            elif package_manager in ["yum", "dnf"]:
                # Red Hat/CentOS/Fedora
                dependency_check = self.safe_run_command([package_manager, "check"],
                                                         filter_func=lambda line: line.strip())
                if not dependency_check.strip():
                    dependency_check = "No broken dependencies found"

                # Check package integrity
                integrity_check = self.safe_run_command([package_manager, "verify"],
                                                        filter_func=lambda line: line.strip(),
                                                        trim_lines=20)
                if not integrity_check.strip():
                    integrity_check = "No package integrity issues found"

                # Check for orphaned packages
                orphaned_packages = self.safe_run_command([package_manager, "autoremove", "--dry-run"],
                                                          filter_func=lambda line: "will be removed" in line or
                                                                                   "Removing:" in line)
                if not orphaned_packages.strip():
                    orphaned_packages = "No orphaned packages found"

            elif package_manager == "pacman":
                # Arch Linux
                dependency_check = self.safe_run_command(["pacman", "-Dk"],
                                                         filter_func=lambda line: line.strip())
                if not dependency_check.strip():
                    dependency_check = "No broken dependencies found"

                # Check package integrity
                integrity_check = self.safe_run_command(["pacman", "-Qk"],
                                                        filter_func=lambda
                                                            line: "0 missing" not in line and line.strip(),
                                                        trim_lines=20)
                if not integrity_check.strip():
                    integrity_check = "No package integrity issues found"

                # Check for orphaned packages
                orphaned_packages = self.safe_run_command(["pacman", "-Qtd"],
                                                          filter_func=lambda line: line.strip(),
                                                          trim_lines=20)
                if not orphaned_packages.strip():
                    orphaned_packages = "No orphaned packages found"

            else:
                dependency_check = "Unable to determine package manager type"
                integrity_check = "Unable to determine package manager type"
                orphaned_packages = "Unable to determine package manager type"

            results[
                "package_dependencies"] = f"Dependency Check:\n{dependency_check}\n\nPackage Integrity:\n{integrity_check}\n\nOrphaned Packages:\n{orphaned_packages}"

        if self.subsections["package_history"]:
            # Show recently installed packages
            if package_manager == "apt":
                # Debian/Ubuntu
                if os.path.exists("/var/log/apt/history.log"):
                    recent_installs = self.safe_read_file("/var/log/apt/history.log",
                                                          filter_func=lambda line: "Install:" in line,
                                                          trim_lines=20)
                else:
                    recent_installs = "APT history log not found"

                # Display upgrade history
                if os.path.exists("/var/log/apt/history.log"):
                    upgrade_history = self.safe_read_file("/var/log/apt/history.log",
                                                          filter_func=lambda line: "Upgrade:" in line,
                                                          trim_lines=20)
                else:
                    upgrade_history = "APT history log not found"

                # Check for failed installations
                if os.path.exists("/var/log/apt/term.log"):
                    failed_installs = self.safe_read_file("/var/log/apt/term.log",
                                                          filter_func=lambda
                                                              line: "Error" in line or "error" in line.lower(),
                                                          trim_lines=20)
                else:
                    failed_installs = "APT term log not found"

            elif package_manager in ["yum", "dnf"]:
                # Red Hat/CentOS/Fedora
                if os.path.exists("/var/log/yum.log"):
                    recent_installs = self.safe_read_file("/var/log/yum.log",
                                                          filter_func=lambda line: "Installed" in line,
                                                          trim_lines=20)
                elif os.path.exists("/var/log/dnf.log"):
                    recent_installs = self.safe_read_file("/var/log/dnf.log",
                                                          filter_func=lambda line: "Installed" in line,
                                                          trim_lines=20)
                else:
                    recent_installs = f"{package_manager} log not found"

                # Display upgrade history
                if os.path.exists("/var/log/yum.log"):
                    upgrade_history = self.safe_read_file("/var/log/yum.log",
                                                          filter_func=lambda line: "Upgraded" in line,
                                                          trim_lines=20)
                elif os.path.exists("/var/log/dnf.log"):
                    upgrade_history = self.safe_read_file("/var/log/dnf.log",
                                                          filter_func=lambda line: "Upgraded" in line,
                                                          trim_lines=20)
                else:
                    upgrade_history = f"{package_manager} log not found"

                # Check for failed installations
                if os.path.exists("/var/log/yum.log"):
                    failed_installs = self.safe_read_file("/var/log/yum.log",
                                                          filter_func=lambda
                                                              line: "Error" in line or "error" in line.lower(),
                                                          trim_lines=20)
                elif os.path.exists("/var/log/dnf.log"):
                    failed_installs = self.safe_read_file("/var/log/dnf.log",
                                                          filter_func=lambda
                                                              line: "Error" in line or "error" in line.lower(),
                                                          trim_lines=20)
                else:
                    failed_installs = f"{package_manager} log not found"

            elif package_manager == "pacman":
                # Arch Linux
                if os.path.exists("/var/log/pacman.log"):
                    recent_installs = self.safe_read_file("/var/log/pacman.log",
                                                          filter_func=lambda line: "installed" in line,
                                                          trim_lines=20)

                    upgrade_history = self.safe_read_file("/var/log/pacman.log",
                                                          filter_func=lambda line: "upgraded" in line,
                                                          trim_lines=20)

                    failed_installs = self.safe_read_file("/var/log/pacman.log",
                                                          filter_func=lambda
                                                              line: "error" in line.lower() or "failed" in line.lower(),
                                                          trim_lines=20)
                else:
                    recent_installs = "Pacman log not found"
                    upgrade_history = "Pacman log not found"
                    failed_installs = "Pacman log not found"

            else:
                recent_installs = "Unable to determine package manager type"
                upgrade_history = "Unable to determine package manager type"
                failed_installs = "Unable to determine package manager type"

            results[
                "package_history"] = f"Recently Installed Packages:\n{recent_installs}\n\nUpgrade History:\n{upgrade_history}\n\nFailed Installations:\n{failed_installs}"

        if self.subsections["repository_health"]:
            # Verify repository access
            if package_manager == "apt":
                # Debian/Ubuntu
                repo_access = self.safe_run_command(["apt-get", "update", "--dry-run"],
                                                    filter_func=lambda
                                                        line: "Ign:" in line or "Hit:" in line or "Err:" in line)

                # Check repository signing keys
                repo_keys = self.safe_run_command(["apt-key", "list"],
                                                  filter_func=lambda
                                                      line: "/" in line or "pub" in line or "uid" in line)

                # Test package manager functionality
                package_test = self.safe_run_command(["apt-cache", "policy", "apt"])

            elif package_manager in ["yum", "dnf"]:
                # Red Hat/CentOS/Fedora
                repo_access = self.safe_run_command([package_manager, "repolist"])

                # Check repository signing keys
                repo_keys = self.safe_run_command(["rpm", "-qa", "gpg-pubkey*"])

                # Test package manager functionality
                package_test = self.safe_run_command([package_manager, "info", package_manager])

            elif package_manager == "pacman":
                # Arch Linux
                repo_access = self.safe_run_command(["pacman", "-Sy", "--dry-run"])

                # Check repository signing keys
                repo_keys = self.safe_run_command(["pacman-key", "--list-keys"])

                # Test package manager functionality
                package_test = self.safe_run_command(["pacman", "-Si", "pacman"])

            else:
                repo_access = "Unable to determine package manager type"
                repo_keys = "Unable to determine package manager type"
                package_test = "Unable to determine package manager type"

            results[
                "repository_health"] = f"Repository Access Check:\n{repo_access}\n\nRepository Signing Keys:\n{repo_keys}\n\nPackage Manager Functionality Test:\n{package_test}"

        return results