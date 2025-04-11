#!/usr/bin/env python3
"""
Base module for all diagnostic modules.
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Callable

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sysdiag")

class DiagnosticModule:
    """Base class for all diagnostic modules."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enabled = False  # All modules unchecked by default
        self.subsections = {}
        self.parent = None  # For hierarchical modules
        self.children = []  # For hierarchical modules

    def run(self) -> Dict[str, str]:
        """Run the diagnostic tasks and return results."""
        raise NotImplementedError("Subclasses must implement this method")

    def safe_run_command(self, command: List[str], trim_lines: int = 0,
                         filter_func: Optional[Callable[[str], bool]] = None) -> str:
        """
        Run a command safely, handling errors and filtering output.

        Args:
            command: Command to run as a list of strings
            trim_lines: Number of last lines to keep (0 for all)
            filter_func: Function to filter lines (should return True to keep line)

        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )

            output = result.stdout if result.returncode == 0 else f"Error: {result.stderr}"

            # Apply filtering if provided
            if filter_func and result.returncode == 0:
                lines = output.splitlines()
                filtered_lines = [line for line in lines if filter_func(line)]
                output = "\n".join(filtered_lines)

            # Trim to last N lines if requested
            if trim_lines > 0 and result.returncode == 0:
                lines = output.splitlines()
                if len(lines) > trim_lines:
                    output = "\n".join(lines[-trim_lines:])
                    output = f"[...showing only last {trim_lines} lines...]\n{output}"

            return output
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Failed to run command {' '.join(command)}: {str(e)}"

    def safe_read_file(self, file_path: str, trim_lines: int = 0,
                       filter_func: Optional[Callable[[str], bool]] = None) -> str:
        """
        Read a file safely, handling errors and filtering output.

        Args:
            file_path: Path to the file
            trim_lines: Number of last lines to keep (0 for all)
            filter_func: Function to filter lines (should return True to keep line)

        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Apply filtering if provided
            if filter_func:
                lines = content.splitlines()
                filtered_lines = [line for line in lines if filter_func(line)]
                content = "\n".join(filtered_lines)

            # Trim to last N lines if requested
            if trim_lines > 0:
                lines = content.splitlines()
                if len(lines) > trim_lines:
                    content = "\n".join(lines[-trim_lines:])
                    content = f"[...showing only last {trim_lines} lines...]\n{content}"

            return content
        except FileNotFoundError:
            return f"File not found: {file_path}"
        except PermissionError:
            return f"Permission denied: {file_path}"
        except Exception as e:
            return f"Failed to read file {file_path}: {str(e)}"

    def set_all_subsections(self, enabled: bool):
        """Set all subsections to enabled or disabled."""
        for key in self.subsections:
            self.subsections[key] = enabled