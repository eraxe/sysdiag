#!/usr/bin/env python3
"""
Report Generator for the Linux System Diagnostic Tool.
"""

import os
import json
import datetime
import subprocess
import logging
import re
from typing import List, Dict, Any, Optional

from ..modules.base import DiagnosticModule

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sysdiag.report")


class ReportGenerator:
    """Generates the final diagnostic report."""

    def __init__(self, modules: List[DiagnosticModule]):
        self.modules = modules

    def generate(self) -> str:
        """Generate the diagnostic report."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hostname = self.get_hostname()

        report = [
            "=" * 80,
            f"🔍 LINUX SYSTEM DIAGNOSTIC REPORT 🔍",
            f"📅 Generated: {timestamp}",
            f"💻 Hostname: {hostname}",
            "=" * 80,
            ""
        ]

        # Add system overview
        system_info = self.get_system_info()
        report.append("📋 SYSTEM OVERVIEW")
        report.append("-" * 80)
        for key, value in system_info.items():
            report.append(f"{key}: {value}")
        report.append("")

        # Run each module and add its results to the report
        for module in self.modules:
            logger.info(f"Running module: {module.name}")

            # Get appropriate icon for the module
            icon = self.get_module_icon(module.name)
            report.append(f"{icon} {module.description.upper()}")
            report.append("-" * 80)

            try:
                results = module.run()

                if not results:
                    report.append("No results collected for this module.")

                for section, content in results.items():
                    # Format section header
                    section_title = section.replace("_", " ").title()
                    report.append(f"### 📌 {section_title} ###")
                    report.append(content)
                    report.append("")
            except Exception as e:
                logger.error(f"Error running module {module.name}: {str(e)}")
                report.append(f"❌ ERROR: Failed to run this module: {str(e)}")

            report.append("")

        return "\n".join(report)

    def get_module_icon(self, module_name):
        """Return an appropriate icon for the module based on its name."""
        icons = {
            "partition_disk": "💾",
            "filesystem": "📁",
            "bootloader": "🔄",
            "initramfs": "🧩",
            "kernel_logs": "📜",
            "hardware_info": "🖥️",
            "custom_scripts": "📝",
            "recovery_diagnostics": "🚑",
            "boot_parameters": "⚙️",
            "grub_boot_diagnostics": "🛠️",
            "network_config": "🌐",
            "security_info": "🔒",
            "user_account": "👤",
            "package_management": "📦",
            "storage_io_performance": "⚡",
            "system_service_status": "🚦",
            "virtualization_container": "📦",
            "log_analysis": "📊"
        }
        return icons.get(module_name, "•")

    def get_hostname(self) -> str:
        """Get the system hostname."""
        return self.get_hostname_static()

    @staticmethod
    def get_hostname_static() -> str:
        """Static method to get system hostname."""
        try:
            return subprocess.run(
                ["hostname"],
                capture_output=True,
                text=True,
                check=False
            ).stdout.strip()
        except Exception:
            return "unknown-host"

    def get_system_info(self) -> Dict[str, str]:
        """Get basic system information."""
        info = {}

        try:
            # Get OS information
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.split("=", 1)
                            if key == "PRETTY_NAME":
                                info["OS"] = value.strip().strip('"')
                                break

            # Get kernel version
            kernel = subprocess.run(
                ["uname", "-r"],
                capture_output=True,
                text=True,
                check=False
            ).stdout.strip()
            info["Kernel"] = kernel

            # Get uptime
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.read().split()[0])
                    days, remainder = divmod(uptime_seconds, 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    info["Uptime"] = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

            # Get CPU count
            if os.path.exists("/proc/cpuinfo"):
                cpu_count = 0
                cpu_model = "Unknown"
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("processor"):
                            cpu_count += 1
                        if line.startswith("model name") and "Unknown" in cpu_model:
                            cpu_model = line.split(":", 1)[1].strip()
                info["CPU Count"] = str(cpu_count)
                info["CPU Model"] = cpu_model

            # Get memory information
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            mem_kb = int(line.split()[1])
                            mem_gb = mem_kb / 1024 / 1024
                            info["Memory"] = f"{mem_gb:.2f} GB"
                            break

        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            info["Error"] = str(e)

        return info

    def save_to_file(self, report: str, filename: str = None) -> str:
        """Save the report to a file."""
        if filename is None:
            hostname = self.get_hostname()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sysdiag_{hostname}_{timestamp}.txt"

        try:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            with open(filename, "w") as f:
                f.write(report)
            return filename
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            return None

    def parse_report_to_json(self, report):
        """Parse a text report into a JSON structure."""
        sections = {}
        current_section = None
        current_subsection = None
        current_content = []

        for line in report.splitlines():
            # Check for main section headers (all caps with dashes below)
            if line and all(c.isupper() or c.isspace() or c in "🔍📅💻📋💾📁🔄🧩📜🖥️📝🚑⚙️🛠️🌐🔒👤📦⚡🚦📊" for c in line):
                if current_section and current_subsection:
                    if current_section not in sections:
                        sections[current_section] = {}
                    sections[current_section][current_subsection] = "\n".join(current_content)
                    current_content = []

                current_section = line.strip()
                current_subsection = None

            # Check for subsection headers
            elif line.startswith("### ") and line.endswith(" ###"):
                if current_section and current_subsection:
                    if current_section not in sections:
                        sections[current_section] = {}
                    sections[current_section][current_subsection] = "\n".join(current_content)
                    current_content = []

                current_subsection = line.strip("# ")

            # Add content lines
            elif current_section and current_subsection:
                current_content.append(line)

        # Don't forget the last section
        if current_section and current_subsection and current_content:
            if current_section not in sections:
                sections[current_section] = {}
            sections[current_section][current_subsection] = "\n".join(current_content)

        return sections

    def generate_html_report(self, report):
        """Generate an HTML version of the report."""
        # Basic HTML template
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Linux System Diagnostic Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        h2 { color: #3498db; margin-top: 30px; border-bottom: 1px solid #ddd; }
        h3 { color: #2980b9; }
        pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
        .timestamp { color: #7f8c8d; font-style: italic; }
        .section { margin-bottom: 30px; }
    </style>
</head>
<body>
    <h1>Linux System Diagnostic Report</h1>
    <div class="timestamp">Generated: {timestamp}</div>

    {content}
</body>
</html>
"""
        # Parse the text report
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_html = []

        in_section = False
        in_subsection = False
        section_name = ""

        for line in report.splitlines():
            # Skip empty lines at the start
            if not in_section and not line.strip():
                continue

            # Process section headers
            if line and all(c.isupper() or c.isspace() for c in line) and "-" * 10 in next(
                    (report.splitlines()[i + 1:i + 2] or [""]), ""):
                if in_section:
                    content_html.append("</div>")  # Close previous section
                content_html.append(f'<div class="section">')
                content_html.append(f'<h2>{line}</h2>')
                in_section = True
                section_name = line

            # Process subsection headers
            elif line.startswith("### ") and line.endswith(" ###"):
                if in_subsection:
                    content_html.append("</pre>")  # Close previous subsection
                subsection_name = line.strip("# ")
                content_html.append(f'<h3>{subsection_name}</h3>')
                content_html.append('<pre>')
                in_subsection = True

            # Process dashed lines (section separators)
            elif line.startswith("-" * 10):
                continue  # Skip separator lines

            # Process content
            elif in_subsection:
                # Escape HTML entities
                escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                content_html.append(escaped_line)

            # Process other lines
            elif in_section and not in_subsection and line.strip():
                content_html.append(f'<p>{line}</p>')

        # Close any open tags
        if in_subsection:
            content_html.append("</pre>")
        if in_section:
            content_html.append("</div>")

        # Fill the template
        html_output = html_template.format(
            timestamp=timestamp,
            content="\n".join(content_html)
        )

        return html_output