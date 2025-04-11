#!/usr/bin/env python3
"""
Main entry point for the Linux System Diagnostic Tool.
"""

import os
import sys
import argparse
import logging
import curses
from typing import List

from .modules import get_all_modules
from .modules.base import DiagnosticModule
from .ui.tui import EnhancedTUI
from .ui.report import ReportGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sysdiag")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Linux System Diagnostic Tool")
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("-y", "--yes", action="store_true", help="Run with default modules, no interactive mode")
    parser.add_argument("-f", "--format", choices=["txt", "json", "html"], default="txt", help="Output format")
    parser.add_argument("-c", "--check-all", action="store_true", help="Check all modules by default")
    parser.add_argument("-a", "--ascii", action="store_true", help="Use ASCII instead of Unicode characters")
    parser.add_argument("--version", action="store_true", help="Show version information")
    return parser.parse_args()


def check_root_privileges():
    """Check if running with root privileges."""
    if os.geteuid() != 0:
        logger.warning("Some diagnostic features require root privileges.")
        logger.warning("Consider running this script with sudo for complete diagnostics.")
        return False
    return True


def run_interactive_mode(modules: List[DiagnosticModule], args):
    """Run the tool in interactive mode."""
    try:
        tui = EnhancedTUI(modules)
        selected_modules = tui.run()

        if not selected_modules:
            logger.info("No modules selected. Exiting.")
            sys.exit(0)

        logger.info("Generating diagnostic report...")
        report_gen = ReportGenerator(selected_modules)
        report = report_gen.generate()

        # Show export options
        def show_export_ui(stdscr):
            tui = EnhancedTUI(selected_modules)
            result = tui.show_export_options(stdscr, report)
            return result

        export_result = curses.wrapper(show_export_ui)

        if export_result and export_result != "Export cancelled":
            logger.info(export_result)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(0)


def run_non_interactive_mode(modules: List[DiagnosticModule], args):
    """Run the tool in non-interactive mode."""
    selected_modules = [m for m in modules if m.enabled]
    if not selected_modules:
        # If nothing selected and in non-interactive mode, select all
        selected_modules = modules
        for module in selected_modules:
            module.enabled = True
            module.set_all_subsections(True)

    logger.info("Generating diagnostic report...")
    report_gen = ReportGenerator(selected_modules)
    report = report_gen.generate()

    format_ext = args.format
    output_file = args.output

    if not output_file:
        hostname = ReportGenerator.get_hostname_static()
        timestamp = import_date_time().now().strftime("%Y%m%d_%H%M%S")
        output_file = f"sysdiag_{hostname}_{timestamp}.{format_ext}"

    if args.format == "json":
        # Convert to JSON
        sections = report_gen.parse_report_to_json(report)
        with open(output_file, "w") as f:
            import json
            json.dump(sections, f, indent=2)
    elif args.format == "html":
        # Convert to HTML
        html = report_gen.generate_html_report(report)
        with open(output_file, "w") as f:
            f.write(html)
    else:
        # Plain text
        with open(output_file, "w") as f:
            f.write(report)

    logger.info(f"Diagnostic report saved to: {output_file}")


def import_date_time():
    """Import datetime module."""
    import datetime
    return datetime


def show_version():
    """Show version information."""
    from . import __version__
    print(f"Linux System Diagnostic Tool version {__version__}")
    print("A comprehensive system diagnostic tool for Linux systems")
    print("Copyright © 2025")


def main():
    """Main function."""
    args = parse_arguments()

    if args.version:
        show_version()
        sys.exit(0)

    # Check if running as root
    has_root = check_root_privileges()
    if not has_root and args.ascii:
        print("WARNING: Some diagnostic features require root privileges.")
        print("Consider running this script with sudo for complete diagnostics.")

    # Initialize modules
    modules = get_all_modules()

    # If check-all is specified, enable all modules
    if args.check_all:
        for module in modules:
            module.enabled = True
            module.set_all_subsections(True)

    # Run in interactive or non-interactive mode
    if args.yes:
        run_non_interactive_mode(modules, args)
    else:
        run_interactive_mode(modules, args)


if __name__ == "__main__":
    main()