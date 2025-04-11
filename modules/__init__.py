#!/usr/bin/env python3
"""
Module initialization - imports all diagnostic modules and provides a function to get all module instances.
"""

from .base import DiagnosticModule

# Import all modules
from .storage import PartitionDiskModule, FilesystemModule, StorageIOPerformanceModule
from .bootloader import (
    BootLoaderModule, InitramfsModule, BootParametersModule, GrubBootDiagnosticsModule
)
from .system import (
    KernelLogsModule, HardwareInfoModule, CustomScriptsModule, RecoveryDiagnosticsModule,
    SystemServiceStatusModule, VirtualizationContainerModule, LogAnalysisModule, PackageManagementModule
)
from .network import NetworkConfigModule
from .security import SecurityInfoModule, UserAccountModule


def get_all_modules():
    """Return a list of all module instances."""
    return [
        # Storage modules
        PartitionDiskModule(),
        FilesystemModule(),
        StorageIOPerformanceModule(),

        # Boot modules
        BootLoaderModule(),
        InitramfsModule(),
        BootParametersModule(),
        GrubBootDiagnosticsModule(),

        # System modules
        KernelLogsModule(),
        HardwareInfoModule(),
        CustomScriptsModule(),
        RecoveryDiagnosticsModule(),
        SystemServiceStatusModule(),
        VirtualizationContainerModule(),
        LogAnalysisModule(),
        PackageManagementModule(),

        # Network modules
        NetworkConfigModule(),

        # Security modules
        SecurityInfoModule(),
        UserAccountModule()
    ]