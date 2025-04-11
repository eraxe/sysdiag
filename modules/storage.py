#!/usr/bin/env python3
"""
Storage related diagnostic modules.
"""

import os
import re
from typing import Dict

from .base import DiagnosticModule

class PartitionDiskModule(DiagnosticModule):
    """Module for partition and disk layout information."""

    def __init__(self):
        super().__init__(
            "partition_disk",
            "Partition & Disk Layout"
        )
        self.subsections = {
            "lsblk": True,
            "fdisk": True,
            "blkid": True,
            "lvm": True,
            "raid": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["lsblk"]:
            results["lsblk"] = self.safe_run_command(["lsblk", "-o", "NAME,SIZE,FSTYPE,TYPE,MOUNTPOINT"])

        if self.subsections["fdisk"]:
            results["fdisk"] = self.safe_run_command(["sudo", "fdisk", "-l"],
                                                     filter_func=lambda
                                                         line: "Disk /dev" in line or "Device" in line or "/dev/" in line)

        if self.subsections["blkid"]:
            results["blkid"] = self.safe_run_command(["sudo", "blkid"])

        if self.subsections["lvm"]:
            vgs_output = self.safe_run_command(["sudo", "vgs"])
            lvs_output = self.safe_run_command(["sudo", "lvs"])
            pvs_output = self.safe_run_command(["sudo", "pvs"])

            results[
                "lvm"] = "VG Summary:\n" + vgs_output + "\n\nLV Summary:\n" + lvs_output + "\n\nPV Summary:\n" + pvs_output

        if self.subsections["raid"]:
            # Check if mdadm is installed and mdstat exists
            md_stat_path = "/proc/mdstat"
            if os.path.exists(md_stat_path):
                results["raid"] = self.safe_read_file(md_stat_path)
            else:
                results["raid"] = "No RAID detected (mdstat not available)"

        return results


class FilesystemModule(DiagnosticModule):
    """Module for filesystem and mount point information."""

    def __init__(self):
        super().__init__(
            "filesystem",
            "Filesystem Table & Mount Points"
        )
        self.subsections = {
            "fstab": True,
            "mounts": True,
            "discrepancies": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["fstab"]:
            results["fstab"] = self.safe_read_file("/etc/fstab")

        if self.subsections["mounts"]:
            results["mount_output"] = self.safe_run_command(["mount"])
            results["findmnt_output"] = self.safe_run_command(["findmnt"])

        if self.subsections["discrepancies"]:
            # Check for UUID discrepancies between fstab and blkid
            fstab = self.safe_read_file("/etc/fstab")
            blkid = self.safe_run_command(["sudo", "blkid"])

            # Extract UUIDs from fstab
            fstab_uuids = {}
            for line in fstab.splitlines():
                if "UUID=" in line and not line.strip().startswith("#"):
                    parts = line.split()
                    for part in parts:
                        if part.startswith("UUID="):
                            uuid = part.split("=", 1)[1].strip('"')
                            mount_point = parts[1] if len(parts) > 1 else "unknown"
                            fstab_uuids[uuid] = mount_point

            # Extract UUIDs from blkid
            blkid_uuids = {}
            for line in blkid.splitlines():
                if "UUID=" in line:
                    device = line.split(":", 1)[0].strip()
                    uuid_start = line.find("UUID=")
                    if uuid_start != -1:
                        uuid_part = line[uuid_start:].split(" ", 1)[0]
                        uuid = uuid_part.split("=", 1)[1].strip('"')
                        blkid_uuids[uuid] = device

            # Find discrepancies
            discrepancies = []
            for uuid, mount in fstab_uuids.items():
                if uuid not in blkid_uuids:
                    discrepancies.append(f"UUID {uuid} in fstab (mount: {mount}) not found in system devices.")

            if discrepancies:
                results["discrepancies"] = "\n".join(discrepancies)
            else:
                results["discrepancies"] = "No UUID discrepancies found."

        return results


class StorageIOPerformanceModule(DiagnosticModule):
    """Module for storage I/O performance diagnostics."""

    def __init__(self):
        super().__init__(
            "storage_io_performance",
            "Storage I/O Performance"
        )
        self.subsections = {
            "disk_performance": True,
            "storage_utilization": True,
            "io_scheduler": True,
            "storage_subsystem_errors": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["disk_performance"]:
            # Run a basic I/O test with dd (read only, for safety)
            io_test = self.safe_run_command(["dd", "if=/dev/zero", "of=/dev/null", "bs=1M", "count=1000"])

            # Check disk queue statistics
            disk_queue = self.safe_read_file("/proc/diskstats")

            # Check I/O statistics using iostat if available
            iostat = self.safe_run_command(["iostat", "-dx", "1", "3"])

            results[
                "disk_performance"] = f"Basic I/O Test (memory only, for safety):\n{io_test}\n\nDisk Queue Statistics:\n{disk_queue}\n\nI/O Statistics:\n{iostat}"

        if self.subsections["storage_utilization"]:
            # Display disk usage
            disk_usage = self.safe_run_command(["df", "-h"])

            # Check for full filesystems
            full_filesystems = self.safe_run_command(["df", "-h"],
                                                     filter_func=lambda
                                                         line: "100%" in line or "9%" in line and line.startswith("/"))

            # Check inode utilization
            inode_usage = self.safe_run_command(["df", "-i"])

            results[
                "storage_utilization"] = f"Disk Space Usage:\n{disk_usage}\n\nNear-Full Filesystems:\n{full_filesystems}\n\nInode Utilization:\n{inode_usage}"

        if self.subsections["io_scheduler"]:
            # Check current I/O scheduler settings
            scheduler_settings = "I/O Scheduler Settings:\n"

            # Find block devices
            block_devices = self.safe_run_command(["lsblk", "-d", "-n", "-o", "NAME"])

            for device in block_devices.splitlines():
                if device.strip():
                    # Check scheduler for this device
                    device_scheduler = self.safe_read_file(f"/sys/block/{device}/queue/scheduler",
                                                           filter_func=lambda line: line.strip())

                    # Check other block device parameters
                    read_ahead = self.safe_read_file(f"/sys/block/{device}/queue/read_ahead_kb",
                                                     filter_func=lambda line: line.strip())

                    nr_requests = self.safe_read_file(f"/sys/block/{device}/queue/nr_requests",
                                                      filter_func=lambda line: line.strip())

                    scheduler_settings += f"\nDevice: {device}\n"
                    scheduler_settings += f"  Scheduler: {device_scheduler}\n"
                    scheduler_settings += f"  Read-ahead: {read_ahead} KB\n"
                    scheduler_settings += f"  Max requests: {nr_requests}\n"

            # Check for device saturation
            device_saturation = self.safe_run_command(["iostat", "-dx", "1", "2"],
                                                    filter_func=lambda line: "avg-cpu" not in line and
                                                                            "Device" not in line and
                                                                            line.strip() and
                                                                            any(term in line for term in
                                                                                [device, "sd", "nvme", "xvd"]))

            results["io_scheduler"] = f"{scheduler_settings}\n\nDevice Saturation:\n{device_saturation}"

        if self.subsections["storage_subsystem_errors"]:
            # Check for disk controller errors
            controller_errors = self.safe_run_command(
                ["dmesg"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["ata", "scsi", "nvme", "mmc", "ahci", "sata", "raid"]
                ) and any(
                    error in line.lower() for error in
                    ["error", "fail", "fault", "timeout", "reset"]
                ),
                trim_lines=20
            )

            # Check storage error logs
            storage_errors = self.safe_run_command(
                ["journalctl"],
                filter_func=lambda line: any(
                    term in line.lower() for term in
                    ["ata", "scsi", "nvme", "mmc", "ahci", "sata", "raid", "disk", "block"]
                ) and any(
                    error in line.lower() for error in
                    ["error", "fail", "fault", "timeout", "reset"]
                ),
                trim_lines=20
            )

            # Monitor disk retries and timeouts
            disk_retries = self.safe_run_command(
                ["cat", "/sys/devices/virtual/block/*/device/timeout"],
                filter_func=lambda line: line.strip()
            )

            # Check SMART errors
            smart_errors = self.safe_run_command(
                ["sudo", "smartctl", "-l", "error", "/dev/sda"],
                filter_func=lambda line: line.strip()
            )
            if "command not found" in smart_errors or "Error" in smart_errors:
                smart_errors = "SMART tools not available or device doesn't support SMART"

            results[
                "storage_subsystem_errors"] = f"Disk Controller Errors:\n{controller_errors}\n\nStorage Error Logs:\n{storage_errors}\n\nDisk Retries/Timeouts:\n{disk_retries}\n\nSMART Errors:\n{smart_errors}"

        return results