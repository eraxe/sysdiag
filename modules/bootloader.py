#!/usr/bin/env python3
"""
Boot related diagnostic modules.
"""

import os
import re
from typing import Dict

from .base import DiagnosticModule


class BootLoaderModule(DiagnosticModule):
    """Module for boot and bootloader information."""

    def __init__(self):
        super().__init__(
            "bootloader",
            "/boot & Boot Loader Configurations"
        )
        self.subsections = {
            "boot_contents": True,
            "grub_config": True,
            "grub_defaults": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["boot_contents"]:
            # List only the kernel images and config files
            results["boot_contents"] = self.safe_run_command(["ls", "-la", "/boot"],
                                                             filter_func=lambda
                                                                 line: "vmlinuz" in line or "config" in line or "initramfs" in line or "initrd" in line)

        if self.subsections["grub_defaults"]:
            grub_default_path = "/etc/default/grub"
            if os.path.exists(grub_default_path):
                results["grub_defaults"] = self.safe_read_file(grub_default_path)
            else:
                results["grub_defaults"] = "GRUB defaults file not found at /etc/default/grub"

                # Try to find alternative grub config files
                alt_paths = [
                    "/etc/grub.d/",
                    "/etc/grub2/grub.cfg",
                    "/boot/grub2/grub.cfg"
                ]

                for path in alt_paths:
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            results["grub_alternatives"] = f"Found GRUB config directory: {path}"
                        else:
                            results["grub_alternatives"] = f"Found alternative GRUB config: {path}"
                        break

        if self.subsections["grub_config"]:
            # Try multiple paths for grub.cfg
            grub_paths = [
                "/boot/grub/grub.cfg",
                "/boot/grub2/grub.cfg",
                "/boot/efi/EFI/grub/grub.cfg"
            ]

            for path in grub_paths:
                if os.path.exists(path):
                    # Extract only the menuentry sections
                    content = self.safe_read_file(path)

                    # Simple extraction of menuentry blocks
                    menu_entries = []
                    in_menu_entry = False
                    current_entry = []
                    open_braces = 0

                    for line in content.splitlines():
                        if line.strip().startswith("menuentry "):
                            in_menu_entry = True
                            open_braces = line.count("{") - line.count("}")
                            current_entry = [line]
                        elif in_menu_entry:
                            current_entry.append(line)
                            open_braces += line.count("{") - line.count("}")

                            if open_braces <= 0:
                                in_menu_entry = False
                                menu_entries.append("\n".join(current_entry))
                                current_entry = []

                    if menu_entries:
                        results["grub_config"] = "\n\n".join(menu_entries)
                    else:
                        results["grub_config"] = f"Failed to extract menu entries from {path}"
                    break
            else:
                results["grub_config"] = "GRUB configuration file not found"

        return results


class InitramfsModule(DiagnosticModule):
    """Module for initramfs and dracut information."""

    def __init__(self):
        super().__init__(
            "initramfs",
            "initramfs & Dracut Configuration"
        )
        self.subsections = {
            "dracut_conf": True,
            "dracut_confdir": True,
            "initramfs_info": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["dracut_conf"]:
            dracut_conf_path = "/etc/dracut.conf"
            if os.path.exists(dracut_conf_path):
                results["dracut_conf"] = self.safe_read_file(dracut_conf_path,
                                                             filter_func=lambda line: not line.strip().startswith(
                                                                 "#") and line.strip())
            else:
                results["dracut_conf"] = "Dracut configuration file not found at /etc/dracut.conf"

        if self.subsections["dracut_confdir"]:
            dracut_confdir_path = "/etc/dracut.conf.d/"
            if os.path.exists(dracut_confdir_path) and os.path.isdir(dracut_confdir_path):
                files = os.listdir(dracut_confdir_path)
                conf_files_content = []

                for file in files:
                    if file.endswith(".conf"):
                        path = os.path.join(dracut_confdir_path, file)
                        content = self.safe_read_file(path,
                                                      filter_func=lambda line: not line.strip().startswith(
                                                          "#") and line.strip())
                        if content:
                            conf_files_content.append(f"=== {file} ===\n{content}")

                if conf_files_content:
                    results["dracut_confdir"] = "\n\n".join(conf_files_content)
                else:
                    results["dracut_confdir"] = "No configuration files found in /etc/dracut.conf.d/"
            else:
                results["dracut_confdir"] = "Dracut configuration directory not found at /etc/dracut.conf.d/"

        if self.subsections["initramfs_info"]:
            # Try to get dracut module list
            dracut_modules = self.safe_run_command(["dracut", "--list-modules"],
                                                   filter_func=lambda line: line.strip())

            # Current kernel version
            kernel_version = self.safe_run_command(["uname", "-r"]).strip()

            # Check if initramfs exists for current kernel
            initramfs_path = f"/boot/initramfs-{kernel_version}.img"
            alt_initramfs_path = f"/boot/initrd-{kernel_version}.img"

            if os.path.exists(initramfs_path):
                initramfs_info = f"initramfs exists for current kernel ({kernel_version})"
            elif os.path.exists(alt_initramfs_path):
                initramfs_info = f"initrd exists for current kernel ({kernel_version})"
            else:
                initramfs_info = f"No initramfs/initrd found for current kernel ({kernel_version})"

            results["initramfs_info"] = f"{initramfs_info}\n\nDracut Modules:\n{dracut_modules}"

        return results


class BootParametersModule(DiagnosticModule):
    """Module for boot parameters and GRUB command line options."""

    def __init__(self):
        super().__init__(
            "boot_parameters",
            "Boot Parameters & GRUB Command-Line Options"
        )
        self.subsections = {
            "kernel_cmdline": True,
            "grub_entries": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["kernel_cmdline"]:
            # Get current kernel command line parameters
            cmdline = self.safe_read_file("/proc/cmdline")
            results["kernel_cmdline"] = f"Current Kernel Command Line:\n{cmdline}"

        if self.subsections["grub_entries"]:
            # Try to find any custom kernel parameters
            grub_entries = []

            # Check /etc/default/grub for GRUB_CMDLINE_LINUX
            grub_default = self.safe_read_file("/etc/default/grub")
            for line in grub_default.splitlines():
                if "GRUB_CMDLINE_LINUX" in line and not line.strip().startswith("#"):
                    grub_entries.append(line)

            if grub_entries:
                results["grub_entries"] = "GRUB Command Line Parameters:\n" + "\n".join(grub_entries)
            else:
                results["grub_entries"] = "No custom GRUB command line parameters found"

        return results


class GrubBootDiagnosticsModule(DiagnosticModule):
    """Module for GRUB/Boot Partition advanced diagnostics."""

    def __init__(self):
        super().__init__(
            "grub_boot_diagnostics",
            "GRUB/Boot Partition Advanced Diagnostics"
        )
        self.subsections = {
            "efi_system_partition": True,
            "boot_sequence_errors": True,
            "bootloader_chain": True,
            "partition_table_validation": True,
            "grub_module_analysis": True,
            "initramfs_content": True,
            "boot_partition_health": True,
            "grub_error_logs": True,
            "bootloader_verification": True,
            "boot_timing_analysis": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["efi_system_partition"]:
            # Check for UEFI vs Legacy BIOS
            efi_dir_exists = os.path.exists("/sys/firmware/efi")
            boot_mode = "UEFI" if efi_dir_exists else "Legacy BIOS"

            # Examine EFI boot entries if we're in UEFI mode
            efibootmgr_output = "Not in UEFI mode"
            if efi_dir_exists:
                efibootmgr_output = self.safe_run_command(["sudo", "efibootmgr", "-v"])

            # Check EFI system partition content
            esp_content = "Not in UEFI mode"
            if efi_dir_exists:
                # Try to find EFI System Partition
                esp_mount = self.safe_run_command(["findmnt", "-t", "vfat", "-o", "TARGET"],
                                                  filter_func=lambda line: "/boot/efi" in line or "/efi" in line)
                if not esp_mount or "Error" in esp_mount:
                    # Try using blkid to find ESP
                    blkid_esp = self.safe_run_command(["sudo", "blkid"],
                                                      filter_func=lambda
                                                          line: "PARTLABEL=\"EFI System Partition\"" in line)
                    esp_content = f"ESP not mounted, blkid shows: {blkid_esp}"
                else:
                    # Get the actual mount point from findmnt output
                    esp_path = esp_mount.strip().split('\n')[-1]
                    # List contents of ESP
                    esp_content = self.safe_run_command(["ls", "-la", esp_path])
                    # Check for EFI binaries
                    efi_binaries = self.safe_run_command(["find", esp_path, "-name", "*.efi", "-o", "-name", "*.EFI"])
                    if efi_binaries:
                        esp_content += f"\n\nEFI Binaries Found:\n{efi_binaries}"

            results[
                "efi_system_partition"] = f"Boot Mode: {boot_mode}\n\nEFI Boot Entries:\n{efibootmgr_output}\n\nEFI System Partition Content:\n{esp_content}"

        if self.subsections["boot_sequence_errors"]:
            # Filter early boot messages for firmware, ACPI, and EFI errors
            dmesg_early_errors = self.safe_run_command(
                ["dmesg"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["firmware", "acpi", "efi", "uefi", "bios", "pci", "smbios", "dmi"]
                ) and any(
                    error in line.lower() for error in
                    ["error", "fail", "warn", "critical", "alert"]
                ),
                trim_lines=20
            )

            # Check for critical boot failures
            boot_failures = self.safe_run_command(
                ["journalctl", "-b", "-p", "err..emerg"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["boot", "init", "start", "mount", "systemd"]
                ),
                trim_lines=20
            )

            results[
                "boot_sequence_errors"] = f"Early Boot Firmware/ACPI/EFI Errors:\n{dmesg_early_errors}\n\nCritical Boot Failures:\n{boot_failures}"

        if self.subsections["bootloader_chain"]:
            # Check for multiboot configurations
            os_prober = self.safe_run_command(["sudo", "os-prober"])

            # Check boot order
            boot_order = "Not available in BIOS mode"
            if os.path.exists("/sys/firmware/efi"):
                boot_order = self.safe_run_command(["sudo", "efibootmgr"])

            # Check secure boot status if in UEFI mode
            secure_boot = "Not available in BIOS mode"
            if os.path.exists("/sys/firmware/efi"):
                mokutil = self.safe_run_command(["mokutil", "--sb-state"])
                if "Error" in mokutil:
                    # Alternative check
                    secure_boot = self.safe_read_file("/sys/kernel/security/securelevel",
                                                       filter_func=lambda line: line.strip())
                else:
                    secure_boot = mokutil

            results[
                "bootloader_chain"] = f"Detected Operating Systems (os-prober):\n{os_prober}\n\nBoot Order:\n{boot_order}\n\nSecure Boot Status:\n{secure_boot}"

        if self.subsections["partition_table_validation"]:
            # Check GPT/MBR integrity
            gdisk_check = self.safe_run_command(["sudo", "gdisk", "-l", "/dev/sda"],
                                                filter_func=lambda line: "corrupt" in line.lower() or
                                                                         "error" in line.lower() or
                                                                         "problem" in line.lower() or
                                                                         "warning" in line.lower() or
                                                                         "Partition table scan" in line or
                                                                         "MBR" in line or
                                                                         "GPT" in line)

            # Check for hybrid partition tables
            fdisk_info = self.safe_run_command(["sudo", "fdisk", "-l", "/dev/sda"],
                                               filter_func=lambda line: "gpt" in line.lower() or
                                                                        "mbr" in line.lower() or
                                                                        "dos" in line.lower() or
                                                                        "hybrid" in line.lower())

            # Check partition alignment
            parted_align = self.safe_run_command(["sudo", "parted", "-l", "/dev/sda", "align-check", "opt", "1"],
                                                 filter_func=lambda line: "aligned" in line.lower() or
                                                                          "not aligned" in line.lower())

            results[
                "partition_table_validation"] = f"Partition Table Integrity Check:\n{gdisk_check}\n\nPartition Table Type Information:\n{fdisk_info}\n\nPartition Alignment Check:\n{parted_align}"

        if self.subsections["grub_module_analysis"]:
            # Try to list available GRUB modules
            grub_modules = "Not available"

            # Try different paths for different distros
            module_paths = [
                "/boot/grub/i386-pc",
                "/boot/grub/x86_64-efi",
                "/boot/grub2/i386-pc",
                "/boot/grub2/x86_64-efi"
            ]

            for path in module_paths:
                if os.path.exists(path):
                    modules = self.safe_run_command(["ls", path],
                                                    filter_func=lambda line: line.endswith(".mod"))
                    if modules and not "Error" in modules:
                        grub_modules = f"GRUB modules in {path}:\n{modules}"
                        break

            # Check which modules are configured to load
            grub_config = self.safe_read_file("/boot/grub/grub.cfg",
                                              filter_func=lambda line: "insmod" in line)
            if "File not found" in grub_config:
                grub_config = self.safe_read_file("/boot/grub2/grub.cfg",
                                                  filter_func=lambda line: "insmod" in line)

            # Calculate most commonly loaded modules
            insmod_pattern = re.compile(r'insmod\s+(\w+)')
            modules_loaded = []
            for line in grub_config.splitlines():
                matches = insmod_pattern.findall(line)
                modules_loaded.extend(matches)

            # Count occurrences of each module
            module_counts = {}
            for module in modules_loaded:
                if module in module_counts:
                    module_counts[module] += 1
                else:
                    module_counts[module] = 1

            # Sort by frequency
            sorted_modules = sorted(module_counts.items(), key=lambda x: x[1], reverse=True)
            module_summary = "Most frequently loaded modules:\n"
            for module, count in sorted_modules[:10]:
                module_summary += f"{module}: {count} times\n"

            results[
                "grub_module_analysis"] = f"Available GRUB Modules:\n{grub_modules}\n\n{module_summary}\n\nInsmod Commands in GRUB Config:\n{grub_config}"

        if self.subsections["initramfs_content"]:
            # Get current kernel version
            kernel_version = self.safe_run_command(["uname", "-r"]).strip()

            # Find initramfs file
            initramfs_paths = [
                f"/boot/initramfs-{kernel_version}.img",
                f"/boot/initrd-{kernel_version}.img",
                f"/boot/initrd.img-{kernel_version}",
                f"/boot/initramfs-{kernel_version}.img"
            ]

            initramfs_file = None
            for path in initramfs_paths:
                if os.path.exists(path):
                    initramfs_file = path
                    break

            if initramfs_file:
                # List contents of initramfs (non-destructively)
                lsinitramfs = self.safe_run_command(["lsinitramfs", initramfs_file],
                                                    filter_func=lambda line: any(
                                                        term in line for term in
                                                        ["/drivers/", "/fs/", "/modules", "bin/", "sbin/", "conf/"]
                                                    ))

                # Check for storage drivers
                storage_drivers = self.safe_run_command(["lsinitramfs", initramfs_file],
                                                        filter_func=lambda line: "/drivers/ata" in line or
                                                                                 "/drivers/block" in line or
                                                                                 "/drivers/nvme" in line or
                                                                                 "/drivers/scsi" in line)

                # Check for filesystem modules
                fs_modules = self.safe_run_command(["lsinitramfs", initramfs_file],
                                                   filter_func=lambda line: "/fs/" in line)

                results[
                    "initramfs_content"] = f"Initramfs File: {initramfs_file}\n\nStorage Drivers in Initramfs:\n{storage_drivers}\n\nFilesystem Modules in Initramfs:\n{fs_modules}\n\nSelected Initramfs Content:\n{lsinitramfs}"
            else:
                results["initramfs_content"] = f"No initramfs file found for kernel version {kernel_version}"

        if self.subsections["boot_partition_health"]:
            # Identify boot partition
            boot_partition = self.safe_run_command(["findmnt", "/boot", "-o", "SOURCE", "-n"]).strip()
            if not boot_partition:
                # Boot might be on the root partition
                boot_partition = self.safe_run_command(["findmnt", "/", "-o", "SOURCE", "-n"]).strip()

            # Remove unnecessary prefixes/characters
            boot_partition = boot_partition.replace('[', '').replace(']', '')
            if boot_partition.startswith("/dev/mapper/"):
                # This is likely an LVM volume, we'll need special handling
                boot_is_lvm = True
            else:
                boot_is_lvm = False

            # Run filesystem check (read-only to be safe)
            if boot_is_lvm:
                fsck_output = f"Boot partition is on LVM ({boot_partition}). Skipping fsck for safety."
            else:
                fsck_output = self.safe_run_command(["sudo", "fsck", "-n", boot_partition])

            # Check for bad blocks (read-only)
            if boot_is_lvm:
                badblocks_output = f"Boot partition is on LVM ({boot_partition}). Skipping badblocks for safety."
            else:
                badblocks_output = self.safe_run_command(["sudo", "badblocks", "-v", "-s", "-n", boot_partition])

            # Get SMART data for the physical device
            device = boot_partition.split("/")[-1]
            if device.startswith("sd") or device.startswith("hd") or device.startswith("nvme"):
                # Extract the base device (e.g., sda from sda1)
                base_device = re.match(r'([a-z]+)', device).group(1)
                smart_data = self.safe_run_command(["sudo", "smartctl", "-a", f"/dev/{base_device}"],
                                                   filter_func=lambda line: any(
                                                       term in line for term in
                                                       ["SMART overall-health", "SMART Health Status",
                                                        "Reallocated_Sector",
                                                        "Current_Pending_Sector", "Offline_Uncorrectable", "Error"]
                                                   ))
            else:
                smart_data = f"Unable to determine physical device for {boot_partition}"

            results[
                "boot_partition_health"] = f"Boot Partition: {boot_partition}\n\nFilesystem Check Results:\n{fsck_output}\n\nBad Blocks Check:\n{badblocks_output}\n\nDisk Health (SMART):\n{smart_data}"

        if self.subsections["grub_error_logs"]:
            # GRUB doesn't have its own log file, so we need to extract relevant messages from other logs
            journal_grub = self.safe_run_command(
                ["journalctl"],
                filter_func=lambda line: "grub" in line.lower() and any(
                    term in line.lower() for term in
                    ["error", "fail", "warn", "fatal"]
                ),
                trim_lines=20
            )

            # Check for grub installation issues in /var/log
            var_log_grub = "Not found"
            if os.path.exists("/var/log/grub-install.log"):
                var_log_grub = self.safe_read_file("/var/log/grub-install.log",
                                                   filter_func=lambda line: any(
                                                       term in line.lower() for term in
                                                       ["error", "fail", "warn", "fatal"]
                                                   ))

            # Check for boot.log for GRUB messages
            boot_log_grub = "Not found"
            if os.path.exists("/var/log/boot.log"):
                boot_log_grub = self.safe_read_file("/var/log/boot.log",
                                                    filter_func=lambda line: "grub" in line.lower())

            results[
                "grub_error_logs"] = f"GRUB Error Messages in Journal:\n{journal_grub}\n\nGRUB Installation Log Issues:\n{var_log_grub}\n\nGRUB Messages in Boot Log:\n{boot_log_grub}"

        if self.subsections["bootloader_verification"]:
            # Check MBR/GPT for bootloader installation
            # This is potentially dangerous, so we just examine the first few bytes non-destructively
            mbr_check = self.safe_run_command(
                ["sudo", "dd", "if=/dev/sda", "bs=512", "count=1", "status=none", "|", "hexdump", "-C", "|", "head",
                 "-n", "3"])

            # Check for bootloader files
            bootloader_files = []
            bootloader_paths = [
                "/boot/grub",
                "/boot/grub2",
                "/boot/efi/EFI"
            ]

            for path in bootloader_paths:
                if os.path.exists(path):
                    bootloader_files.append(f"Bootloader directory found: {path}")
                    # List key files
                    if os.path.isdir(path):
                        ls_output = self.safe_run_command(["ls", "-la", path])
                        bootloader_files.append(ls_output)

            # Check boot entries on all disks
            disks = self.safe_run_command(["lsblk", "-d", "-n", "-o", "NAME", "-p"])
            boot_entries = []

            for disk in disks.splitlines():
                if disk:
                    disk_entry = self.safe_run_command(
                        ["sudo", "dd", "if=" + disk, "bs=512", "count=1", "status=none", "|", "strings", "|", "grep",
                         "-i", "grub"])
                    boot_entries.append(f"Boot signature check for {disk}:\n{disk_entry}")

            results["bootloader_verification"] = f"MBR Check:\n{mbr_check}\n\nBootloader Files:\n" + "\n".join(
                bootloader_files) + "\n\nBoot Entries on Disks:\n" + "\n".join(boot_entries)

        if self.subsections["boot_timing_analysis"]:
            # Use systemd-analyze for boot timing
            systemd_analyze = self.safe_run_command(["systemd-analyze"])

            # Get blame information for slow services
            systemd_blame = self.safe_run_command(["systemd-analyze", "blame", "|", "head", "-n", "10"])

            # Get critical chain for boot sequence
            systemd_critical = self.safe_run_command(["systemd-analyze", "critical-chain"])

            results[
                "boot_timing_analysis"] = f"Boot Timing Summary:\n{systemd_analyze}\n\nSlowest Boot Components:\n{systemd_blame}\n\nBoot Critical Chain:\n{systemd_critical}"

        return results