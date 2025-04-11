#!/usr/bin/env python3
"""
Linux System Diagnostic Tool - Installation Manager

This script manages the installation, updating, and removal of the Linux System
Diagnostic Tool on your system. It handles permissions, creates necessary directories,
and sets up command aliases for easy access.

Usage:
    ./install.py install [--dest DIR]
    ./install.py update
    ./install.py remove
    ./install.py status
"""

import os
import sys
import shutil
import subprocess
import argparse
import stat
import logging
import platform
import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sysdiag-installer")

# Constants
DEFAULT_BIN_DIR = "/usr/local/bin"
DEFAULT_LIB_DIR = "/usr/local/lib"
TOOL_NAME = "sysdiag"
COMPLETION_DIR = "/etc/bash_completion.d"
SERVICE_DIR = "/etc/systemd/system"
CONFIG_DIR = "/etc/sysdiag"
MAN_DIR = "/usr/local/share/man/man1"
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def check_root_privileges():
    """Check if the script is run with root privileges."""
    return os.geteuid() == 0


def ensure_root():
    """Ensure the script is run with root privileges or exit."""
    if not check_root_privileges():
        logger.error("This operation requires root privileges. Please run with sudo.")
        sys.exit(1)


def check_python_version():
    """Check if Python version is at least 3.6."""
    version_info = sys.version_info
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 6):
        logger.error("Python 3.6 or higher is required.")
        sys.exit(1)


def create_directory(path):
    """Create directory if it doesn't exist."""
    try:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory: {path}")
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        sys.exit(1)


def make_executable(path):
    """Make a file executable."""
    try:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
        logger.info(f"Made {path} executable")
    except Exception as e:
        logger.error(f"Failed to make {path} executable: {e}")
        sys.exit(1)


def copy_file(source, destination):
    """Copy a file from source to destination."""
    try:
        shutil.copy2(source, destination)
        logger.info(f"Copied {source} to {destination}")
        return True
    except FileNotFoundError:
        logger.error(f"Source file {source} not found")
        return False
    except Exception as e:
        logger.error(f"Failed to copy file: {e}")
        return False


def copy_directory(source, destination):
    """Copy a directory recursively."""
    try:
        if os.path.exists(destination):
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        logger.info(f"Copied directory {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy directory: {e}")
        return False


def write_file(path, content):
    """Write content to a file."""
    try:
        with open(path, 'w') as f:
            f.write(content)
        logger.info(f"Created file: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {path}: {e}")
        return False


def create_bash_completion():
    """Create bash completion script."""
    completion_path = os.path.join(COMPLETION_DIR, "sysdiag-completion.bash")
    completion_content = """# Bash completion for sysdiag tool
_sysdiag()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--help --output --yes --format --check-all --ascii --version"

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _sysdiag sysdiag
"""
    create_directory(COMPLETION_DIR)
    return write_file(completion_path, completion_content)


def create_man_page():
    """Create man page for the tool."""
    create_directory(MAN_DIR)
    man_path = os.path.join(MAN_DIR, "sysdiag.1")
    # Using a raw string to avoid escape sequence issues
    man_content = r""".TH SYSDIAG 1 "Linux System Diagnostic Tool"
.SH NAME
sysdiag \- Linux System Diagnostic Tool
.SH SYNOPSIS
.B sysdiag
[\fIOPTIONS\fR]
.SH DESCRIPTION
.B sysdiag
is a comprehensive system information reporting tool for Linux diagnostics 
that generates concise, customizable reports.
.SH OPTIONS
.TP
.BR \-o ", " \-\-output=\fIFILE\fR
Write report to FILE instead of the default filename.
.TP
.BR \-y ", " \-\-yes
Run with default modules, no interactive mode.
.TP
.BR \-f ", " \-\-format=\fIFORMAT\fR
Specify output format: txt, json, or html.
.TP
.BR \-c ", " \-\-check\-all
Check all modules by default.
.TP
.BR \-a ", " \-\-ascii
Use ASCII instead of Unicode characters.
.TP
.BR \-h ", " \-\-help
Show help message and exit.
.TP
.BR \-\-version
Show version information and exit.
.SH EXAMPLES
.TP
.B sysdiag
Run the tool in interactive mode.
.TP
.B sysdiag -y -o my_report.txt
Run with all default modules and save to my_report.txt.
.SH AUTHOR
Linux System Administrator
.SH SEE ALSO
.BR lsblk (8),
.BR fdisk (8),
.BR systemd (1)
"""
    write_file(man_path, man_content)
    subprocess.run(["gzip", "-f", man_path], check=False)
    logger.info(f"Created man page: {man_path}.gz")


def create_wrapper_script(bin_dir, module_path):
    """Create the wrapper script."""
    wrapper_path = os.path.join(bin_dir, TOOL_NAME)
    wrapper_content = f"""#!/usr/bin/env python3
import os
import sys
import importlib
import importlib.util

def main():
    # Set path to the installed module
    sysdiag_path = "{module_path}"

    # Add the path to sys.path if it's not already there
    if sysdiag_path not in sys.path:
        sys.path.insert(0, os.path.dirname(sysdiag_path))

    # Check if we're running as root or if we need to elevate
    if os.geteuid() != 0:
        print("Some diagnostic features require root privileges.")
        try:
            args = ["sudo", sys.executable] + sys.argv
            os.execvp("sudo", args)
        except Exception as e:
            print(f"Error running with sudo: {{e}}")
            sys.exit(1)

    # Import and run the main function
    try:
        from sysdiag.main import main as sysdiag_main
        sysdiag_main()
    except ImportError as e:
        print(f"Error importing sysdiag module: {{e}}")
        print(f"Make sure the module is correctly installed at {{sysdiag_path}}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running sysdiag: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""

    success = write_file(wrapper_path, wrapper_content)
    if success:
        make_executable(wrapper_path)
        return True
    return False


def create_config_directory():
    """Create configuration directory."""
    create_directory(CONFIG_DIR)
    default_config = os.path.join(CONFIG_DIR, "sysdiag.conf")
    config_content = """# Default configuration for sysdiag tool
# This file controls which modules are enabled by default

# Module enablement (true/false)
[modules]
partition_disk = true
filesystem = true
bootloader = true
initramfs = true
kernel_logs = true
hardware_info = true
custom_scripts = true
recovery_diagnostics = true
boot_parameters = true
grub_boot_diagnostics = true
network_config = true
security_info = true
user_account = true
package_management = true
storage_io_performance = true
system_service_status = true
virtualization_container = true
log_analysis = true

# Output directory for reports
[output]
directory = /var/log/sysdiag
"""
    return write_file(default_config, config_content)


def install_tool(dest_dir):
    """Install the diagnostic tool."""
    ensure_root()
    logger.info(f"Installing Linux System Diagnostic Tool to {dest_dir}")

    # Create directories
    create_directory(dest_dir)
    create_directory(DEFAULT_BIN_DIR)
    create_directory("/var/log/sysdiag")

    # Install the package to the lib directory
    module_path = os.path.join(DEFAULT_LIB_DIR, "sysdiag")
    if not copy_directory(SOURCE_DIR, module_path):
        logger.error("Failed to copy module to lib directory")
        sys.exit(1)

    # Create wrapper script in bin directory
    if not create_wrapper_script(DEFAULT_BIN_DIR, module_path):
        logger.error("Failed to create wrapper script")
        sys.exit(1)

    # Create bash completion
    create_bash_completion()

    # Create config directory and default config
    create_config_directory()

    # Create man page
    create_man_page()

    logger.info("Installation completed successfully!")
    logger.info(f"You can now run the tool using: {TOOL_NAME}")


def update_tool():
    """Update the diagnostic tool."""
    ensure_root()
    logger.info("Updating Linux System Diagnostic Tool")

    # Check if installed
    module_path = os.path.join(DEFAULT_LIB_DIR, "sysdiag")
    if not os.path.exists(module_path):
        logger.error("Tool not installed. Please install first.")
        sys.exit(1)

    # Backup existing installation
    backup_path = f"{module_path}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        shutil.copytree(module_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        sys.exit(1)

    # Install the updated package
    if not copy_directory(SOURCE_DIR, module_path):
        # Restore from backup if update fails
        logger.info("Update failed, restoring from backup")
        shutil.rmtree(module_path)
        shutil.move(backup_path, module_path)
        sys.exit(1)

    # Update wrapper script
    create_wrapper_script(DEFAULT_BIN_DIR, module_path)

    # Update bash completion
    create_bash_completion()

    # Update man page
    create_man_page()

    logger.info("Update completed successfully!")


def remove_tool():
    """Remove the diagnostic tool."""
    ensure_root()
    logger.info("Removing Linux System Diagnostic Tool")

    files_to_remove = [
        os.path.join(DEFAULT_BIN_DIR, TOOL_NAME),
        os.path.join(COMPLETION_DIR, "sysdiag-completion.bash"),
        os.path.join(MAN_DIR, "sysdiag.1.gz")
    ]

    dirs_to_remove = [
        os.path.join(DEFAULT_LIB_DIR, "sysdiag"),
        CONFIG_DIR
    ]

    # Ask for confirmation
    confirm = input("This will completely remove the Linux System Diagnostic Tool. Continue? [y/N]: ")
    if confirm.lower() != 'y':
        logger.info("Removal cancelled.")
        return

    # Remove files
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")

    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                logger.info(f"Removed directory: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to remove directory {dir_path}: {e}")

    # Ask about removing log files
    remove_logs = input("Do you also want to remove all diagnostic logs? [y/N]: ")
    if remove_logs.lower() == 'y':
        log_dir = "/var/log/sysdiag"
        if os.path.exists(log_dir):
            try:
                shutil.rmtree(log_dir)
                logger.info(f"Removed log directory: {log_dir}")
            except Exception as e:
                logger.error(f"Failed to remove log directory: {e}")

    logger.info("Tool removed successfully.")


def check_status():
    """Check the installation status of the tool."""
    module_path = os.path.join(DEFAULT_LIB_DIR, "sysdiag")
    wrapper_script = os.path.join(DEFAULT_BIN_DIR, TOOL_NAME)
    config_dir = CONFIG_DIR

    print("\n=== Linux System Diagnostic Tool Status ===")

    if os.path.exists(module_path):
        # Get version
        try:
            version = "Unknown"
            init_path = os.path.join(module_path, "__init__.py")
            if os.path.exists(init_path):
                with open(init_path, 'r') as f:
                    for line in f:
                        if line.startswith("__version__"):
                            version = line.split("=")[1].strip().strip('"\'')
                            break

            mtime = os.path.getmtime(module_path)
            from datetime import datetime
            mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

            print(f"Status: INSTALLED")
            print(f"Version: {version}")
            print(f"Module Location: {module_path}")
            print(f"Last modified: {mod_time}")

            # Check if wrapper is executable
            if os.path.exists(wrapper_script) and os.access(wrapper_script, os.X_OK):
                print("Wrapper script: Present and executable ✓")
            elif os.path.exists(wrapper_script):
                print("Wrapper script: Present but not executable ✗")
            else:
                print("Wrapper script: Missing ✗")

            # Check config
            if os.path.exists(config_dir):
                print(f"Configuration: Present ✓")
            else:
                print(f"Configuration: Missing ✗")

            # Check if binary is in PATH
            paths = os.environ.get("PATH", "").split(os.pathsep)
            if DEFAULT_BIN_DIR in paths:
                print("PATH configuration: Correct ✓")
            else:
                print("PATH configuration: Not in PATH ✗")

        except Exception as e:
            print(f"Error checking status: {e}")
    else:
        print("Status: NOT INSTALLED")

    print("=" * 42)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Linux System Diagnostic Tool - Installation Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install the diagnostic tool")
    install_parser.add_argument("--dest", default=DEFAULT_BIN_DIR, help="Installation directory")

    # Update command
    subparsers.add_parser("update", help="Update the diagnostic tool")

    # Remove command
    subparsers.add_parser("remove", help="Remove the diagnostic tool")

    # Status command
    subparsers.add_parser("status", help="Check installation status")

    args = parser.parse_args()

    # Check Python version
    check_python_version()

    # Execute command
    if args.command == "install":
        install_tool(args.dest)
    elif args.command == "update":
        update_tool()
    elif args.command == "remove":
        remove_tool()
    elif args.command == "status":
        check_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()