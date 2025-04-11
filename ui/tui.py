#!/usr/bin/env python3
"""
Enhanced TUI (Text User Interface) using curses for the Linux System Diagnostic Tool.
"""

import os
import sys
import curses
import tempfile
import subprocess
import json
import re
import datetime
import logging
from typing import List, Dict, Any, Optional, Callable

from ..modules.base import DiagnosticModule

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sysdiag.tui")


class EnhancedTUI:
    """Enhanced TUI for module selection and configuration using curses."""

    def __init__(self, modules: List[DiagnosticModule]):
        self.all_modules = modules
        self.modules = self.organize_modules()  # Root level modules
        self.current_pos = 0
        self.in_subsection = False
        self.current_module_index = 0
        self.current_subsection_pos = 0
        self.status_message = ""
        self.run_selected = False
        # Start with all modules expanded
        self.expanded_modules = set(range(len(modules)))

        # Determine if unicode is supported
        self.use_unicode = self.check_unicode_support()

    def check_unicode_support(self):
        """Check if the terminal supports unicode characters."""
        try:
            # Try to get the locale
            import locale
            locale_encoding = locale.getpreferredencoding()
            return locale_encoding.lower() in ('utf-8', 'utf8')
        except:
            return False

    def get_module_icon(self, module_name, use_ascii=False):
        """Return an appropriate icon for the module based on its name."""
        if use_ascii:
            # ASCII-only icons
            icons = {
                "partition_disk": "[D]",
                "filesystem": "[F]",
                "bootloader": "[B]",
                "initramfs": "[I]",
                "kernel_logs": "[K]",
                "hardware_info": "[H]",
                "custom_scripts": "[C]",
                "recovery_diagnostics": "[R]",
                "boot_parameters": "[P]",
                "grub_boot_diagnostics": "[G]",
                "network_config": "[N]",
                "security_info": "[S]",
                "user_account": "[U]",
                "package_management": "[P]",
                "storage_io_performance": "[I]",
                "system_service_status": "[S]",
                "virtualization_container": "[V]",
                "log_analysis": "[L]"
            }
        else:
            # Unicode icons (including emoji)
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
        return icons.get(module_name, "*")

    def organize_modules(self) -> List[DiagnosticModule]:
        """Organize modules into a hierarchical structure."""
        # Just return the flat list for now - we'll handle the tree view in the UI
        return self.all_modules

    def draw_main_menu(self, stdscr):
        """Draw the main menu with a tree-like structure and enhanced visuals."""
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Set up colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Highlighted items
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Enabled items
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)  # Disabled items
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Special highlights

        # Draw header
        header = " Linux System Diagnostic Tool "
        if self.use_unicode:
            header = " 🔍 Linux System Diagnostic Tool 🔍 "

        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, (w - len(header)) // 2, header)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        # Draw help text
        help_text = "↑/↓/j/k: Navigate | Space: Check/Uncheck | Enter: Expand/Collapse | r: Run | q: Quit"
        if not self.use_unicode:
            help_text = "Up/Down/j/k: Navigate | Space: Check/Uncheck | Enter: Expand/Collapse | r: Run | q: Quit"

        help_lines = [help_text[i:i + w - 4] for i in range(0, len(help_text), w - 4)]
        for i, line in enumerate(help_lines):
            stdscr.addstr(3 + i, 2, line)

        # Draw status message
        if self.status_message:
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(h - 2, 2, self.status_message)
            stdscr.attroff(curses.A_BOLD)

        # Choose appropriate characters based on unicode support
        if self.use_unicode:
            checkbox_on = "✅"
            checkbox_off = "❌"
            expand_collapse_on = "▼"
            expand_collapse_off = "▶"
        else:
            checkbox_on = "[X]"
            checkbox_off = "[ ]"
            expand_collapse_on = "[-]"
            expand_collapse_off = "[+]"

        # Draw modules list with tree-like view
        list_start_y = 5 + len(help_lines)
        max_visible_items = h - list_start_y - 3  # Leave room for status and bottom border

        # Calculate visible range
        visible_items = []
        for i, module in enumerate(self.modules):
            visible_items.append((i, 0, module))  # (index, indent_level, module)
            if i in self.expanded_modules:
                for subsection_name in module.subsections:
                    # Add a "fake" entry for each subsection
                    visible_items.append((i, 1, subsection_name))

        # Determine which slice of items to show
        if self.current_pos >= max_visible_items:
            start_idx = self.current_pos - max_visible_items + 1
        else:
            start_idx = 0

        end_idx = min(start_idx + max_visible_items, len(visible_items))

        # Draw each visible item
        for i in range(start_idx, end_idx):
            module_idx, indent_level, item = visible_items[i]
            y_pos = list_start_y + (i - start_idx)

            # Draw selection indicator
            if i == self.current_pos:
                stdscr.attron(curses.A_REVERSE)

            # Calculate indentation
            indent = indent_level * 4

            if isinstance(item, str):  # This is a subsection
                module = self.modules[module_idx]
                # Draw checkbox
                checkbox = checkbox_on if module.subsections[item] else checkbox_off
                # Format subsection name for display
                display_name = item.replace("_", " ").title()

                if module.subsections[item]:
                    stdscr.attron(curses.color_pair(3))
                else:
                    stdscr.attron(curses.color_pair(4))

                stdscr.addstr(y_pos, 2 + indent, f"{checkbox} {display_name}")

                if module.subsections[item]:
                    stdscr.attroff(curses.color_pair(3))
                else:
                    stdscr.attroff(curses.color_pair(4))

            else:  # This is a module
                module = item
                # Draw expand/collapse indicator
                if module.subsections:
                    expand_indicator = expand_collapse_on if module_idx in self.expanded_modules else expand_collapse_off
                else:
                    expand_indicator = "   "

                # Draw checkbox
                checkbox = checkbox_on if module.enabled else checkbox_off

                # Get module icon
                icon = self.get_module_icon(module.name, not self.use_unicode)

                if module.enabled:
                    stdscr.attron(curses.color_pair(3))
                else:
                    stdscr.attron(curses.color_pair(4))

                # Make the module name bold to stand out
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(y_pos, 2, f"{expand_indicator} {checkbox} {icon} {module.name}")
                stdscr.attroff(curses.A_BOLD)

                # Display the description in normal text
                stdscr.addstr(y_pos, 2 + len(f"{expand_indicator} {checkbox} {icon} {module.name}") + 1,
                              f"- {module.description}")

                if module.enabled:
                    stdscr.attroff(curses.color_pair(3))
                else:
                    stdscr.attroff(curses.color_pair(4))

            # Turn off highlight
            if i == self.current_pos:
                stdscr.attroff(curses.A_REVERSE)

        # Draw footer
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(h - 1, 2, "Press 'q' to quit, 'r' to run diagnostics")
        stdscr.attroff(curses.A_BOLD)
        stdscr.refresh()

    def draw_subsection_menu(self, stdscr, module_index):
        """Draw the subsection menu for a module."""
        module = self.modules[module_index]
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Set up colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Enabled
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)  # Disabled

        # Draw header
        icon = self.get_module_icon(module.name, not self.use_unicode)
        header = f" Configure {icon} {module.name} subsections "
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, (w - len(header)) // 2, header)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        # Draw help text
        help_text = "Use Up/Down to navigate, Space to toggle, Escape or 'q' to go back"
        stdscr.addstr(3, (w - len(help_text)) // 2, help_text)

        # Choose appropriate characters based on unicode support
        if self.use_unicode:
            checkbox_on = "✅"
            checkbox_off = "❌"
        else:
            checkbox_on = "[X]"
            checkbox_off = "[ ]"

        # Draw subsections list
        list_start_y = 5
        subsections = list(module.subsections.items())

        for i, (name, enabled) in enumerate(subsections):
            y_pos = list_start_y + i

            # Draw selection indicator
            if i == self.current_subsection_pos:
                stdscr.attron(curses.A_REVERSE)

            # Draw checkbox
            checkbox = checkbox_on if enabled else checkbox_off
            # Format subsection name for display
            display_name = name.replace("_", " ").title()

            if enabled:
                stdscr.attron(curses.color_pair(3))
            else:
                stdscr.attron(curses.color_pair(4))

            stdscr.addstr(y_pos, 4, f"{checkbox} {display_name}")

            if enabled:
                stdscr.attroff(curses.color_pair(3))
            else:
                stdscr.attroff(curses.color_pair(4))

            # Turn off highlight
            if i == self.current_subsection_pos:
                stdscr.attroff(curses.A_REVERSE)

        # Draw footer
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(h - 1, 2, "Press 'q' or Escape to go back to main menu")
        stdscr.attroff(curses.A_BOLD)
        stdscr.refresh()

    def draw_export_menu(self, stdscr):
        """Draw the export options menu."""
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Set up colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Options

        # Draw header
        header = " Export Options "
        if self.use_unicode:
            header = " 📊 Export Options 📊 "

        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, (w - len(header)) // 2, header)
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        # Draw options
        options = [
            "1. Export to text file (default location)",
            "2. Export to text file (custom location)",
            "3. Export to JSON format",
            "4. Export to HTML format",
            "5. Copy to clipboard (if available)",
            "6. Display on screen only"
        ]

        for i, option in enumerate(options):
            y_pos = 5 + i
            stdscr.attron(curses.color_pair(5))
            stdscr.addstr(y_pos, 4, option)
            stdscr.attroff(curses.color_pair(5))

        # Draw instructions
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(13, 4, "Enter the number of your choice (1-6), or press 'q' to go back:")
        stdscr.attroff(curses.A_BOLD)

        # Draw footer
        stdscr.addstr(h - 1, 2, "Press 'q' to go back without exporting")
        stdscr.refresh()

    def handle_export_choice(self, choice, report, stdscr=None):
        """Handle the export option chosen by the user."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = self.get_hostname()
        default_filename = f"sysdiag_{hostname}_{timestamp}"

        if choice == '1':
            # Default location
            filename = f"/tmp/{default_filename}.txt"
            success = self.write_to_file(report, filename)
            return f"Report exported to {filename}" if success else "Failed to export report"

        elif choice == '2':
            # Custom location
            if stdscr:
                curses.echo()
                h, w = stdscr.getmaxyx()
                stdscr.addstr(15, 4, "Enter file path: ")
                curses.curs_set(1)  # Show cursor
                filename = stdscr.getstr(15, 20, 50).decode('utf-8')
                curses.noecho()
                curses.curs_set(0)  # Hide cursor

                if not filename:
                    return "Export cancelled"

                success = self.write_to_file(report, filename)
                return f"Report exported to {filename}" if success else "Failed to export report"
            return "Export failed - no screen available"

        elif choice == '3':
            # JSON format
            filename = f"/tmp/{default_filename}.json"

            # Generate JSON object from report sections
            report_sections = self.parse_report_to_json(report)
            try:
                with open(filename, 'w') as f:
                    json.dump(report_sections, f, indent=2)
                return f"JSON report exported to {filename}"
            except Exception as e:
                return f"Failed to export JSON report: {str(e)}"

        elif choice == '4':
            # HTML format
            filename = f"/tmp/{default_filename}.html"
            html_content = self.generate_html_report(report)
            success = self.write_to_file(html_content, filename)
            return f"HTML report exported to {filename}" if success else "Failed to export HTML report"

        elif choice == '5':
            # Copy to clipboard (if xclip/xsel available)
            try:
                # Write to temp file first
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file.write(report.encode('utf-8'))
                temp_filename = temp_file.name
                temp_file.close()

                # Try xclip first, then xsel
                try:
                    subprocess.run(["xclip", "-selection", "clipboard", temp_filename], check=True)
                    os.unlink(temp_filename)
                    return "Report copied to clipboard using xclip"
                except (subprocess.SubprocessError, FileNotFoundError):
                    try:
                        subprocess.run(["xsel", "--clipboard", "--input", temp_filename], check=True)
                        os.unlink(temp_filename)
                        return "Report copied to clipboard using xsel"
                    except (subprocess.SubprocessError, FileNotFoundError):
                        os.unlink(temp_filename)
                        return "Clipboard utilities (xclip/xsel) not available"
            except Exception as e:
                return f"Failed to copy to clipboard: {str(e)}"

        elif choice == '6':
            # Display only - return a special marker
            return "__DISPLAY_ONLY__"

        else:
            return "Invalid choice"

    def get_hostname(self):
        """Get the system hostname."""
        try:
            return subprocess.run(
                ["hostname"],
                capture_output=True,
                text=True,
                check=False
            ).stdout.strip()
        except Exception:
            return "unknown-host"

    def write_to_file(self, content, filename):
        """Write content to a file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            with open(filename, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write to {filename}: {str(e)}")
            return False

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
        .toc { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .toc ul { list-style-type: none; }
        .toc li { margin: 5px 0; }
        .toc a { text-decoration: none; color: #3498db; }
        .toc a:hover { text-decoration: underline; }
        button.top { position: fixed; bottom: 20px; right: 20px; padding: 10px; 
                   background: #3498db; color: white; border: none; 
                   border-radius: 5px; cursor: pointer; }
        button.top:hover { background: #2980b9; }
    </style>
    <script>
        function scrollToTop() {
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    </script>
</head>
<body>
    <h1>Linux System Diagnostic Report</h1>
    <div class="timestamp">Generated: {timestamp}</div>

    <div class="toc">
        <h2>Table of Contents</h2>
        {toc}
    </div>

    {content}

    <button onclick="scrollToTop()" class="top">↑ Top</button>
</body>
</html>
"""
        # Parse the text report
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_html = []
        toc_items = []

        in_section = False
        in_subsection = False
        section_name = ""
        section_count = 0

        lines = report.splitlines()

        for i, line in enumerate(lines):
            # Skip empty lines at the start
            if not in_section and not line.strip():
                continue

            # Process section headers (all caps with dashes below)
            if (line and all(c.isupper() or c.isspace() or c in "🔍📅💻📋💾📁🔄🧩📜🖥️📝🚑⚙️🛠️🌐🔒👤📦⚡🚦📊" for c in line) and
                    i < len(lines) - 1 and "-" * 10 in lines[i + 1]):
                if in_section:
                    content_html.append("</div>")  # Close previous section

                section_count += 1
                section_id = f"section-{section_count}"
                content_html.append(f'<div id="{section_id}" class="section">')
                content_html.append(f'<h2>{line}</h2>')
                toc_items.append(f'<li><a href="#{section_id}">{line}</a></li>')

                in_section = True
                section_name = line

            # Process subsection headers
            elif line.startswith("### ") and line.endswith(" ###"):
                if in_subsection:
                    content_html.append("</pre>")  # Close previous subsection

                subsection_name = line.strip("# ")
                subsection_id = f"subsection-{section_count}-{len(toc_items)}"
                content_html.append(f'<h3 id="{subsection_id}">{subsection_name}</h3>')
                content_html.append('<pre>')
                toc_items.append(
                    f'<li style="margin-left: 20px;"><a href="#{subsection_id}">{subsection_name}</a></li>')

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

        # Generate table of contents
        toc_html = f'<ul>{"".join(toc_items)}</ul>'

        # Fill the template
        html_output = html_template.format(
            timestamp=timestamp,
            toc=toc_html,
            content="\n".join(content_html)
        )

        return html_output

    def display_report(self, stdscr, report):
        """Display the report on screen with scrolling."""
        stdscr.clear()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

        h, w = stdscr.getmaxyx()

        # Split the report into lines
        lines = report.splitlines()
        total_lines = len(lines)

        # Setup scrolling
        top_line = 0
        bottom_line = min(top_line + h - 2, total_lines - 1)

        # Display instructions in the header
        header = " Report Viewer - Use Up/Down/PgUp/PgDn to scroll, 'q' to exit "
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(0, 0, header + " " * (w - len(header)))
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        while True:
            # Clear and redraw the screen
            for i in range(1, h - 1):
                stdscr.addstr(i, 0, " " * (w - 1))

            # Display the visible portion of the report
            for i in range(top_line, bottom_line + 1):
                if i < total_lines and i - top_line + 1 < h:
                    try:
                        line = lines[i][:w - 1]  # Truncate to fit width

                        # Highlight section headers
                        if line and all(c.isupper() or c.isspace() or c in "🔍📅💻📋💾📁🔄🧩📜🖥️📝🚑⚙️🛠️🌐🔒👤📦⚡🚦📊" for c in line):
                            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                            stdscr.addstr(i - top_line + 1, 0, line)
                            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                        # Highlight subsection headers
                        elif line.startswith("### ") and line.endswith(" ###"):
                            stdscr.attron(curses.color_pair(3) | curses.A_UNDERLINE)
                            stdscr.addstr(i - top_line + 1, 0, line)
                            stdscr.attroff(curses.color_pair(3) | curses.A_UNDERLINE)
                        else:
                            stdscr.addstr(i - top_line + 1, 0, line)
                    except curses.error:
                        # Handle curses errors when trying to write at the bottom right corner
                        pass

            # Show scrollbar if needed
            if total_lines > h - 2:
                scrollbar_height = max(1, (h - 2) * (h - 2) // total_lines)
                scrollbar_pos = 1 + (h - 2 - scrollbar_height) * top_line // max(1, total_lines - (h - 2))

                for i in range(1, h - 1):
                    if scrollbar_pos <= i < scrollbar_pos + scrollbar_height:
                        try:
                            stdscr.addch(i, w - 1, curses.ACS_BLOCK)
                        except curses.error:
                            pass
                    else:
                        try:
                            stdscr.addch(i, w - 1, curses.ACS_VLINE)
                        except curses.error:
                            pass

            # Show position indicator
            footer = f" Line {top_line + 1}-{bottom_line + 1} of {total_lines} "
            try:
                stdscr.addstr(h - 1, 0, footer + " " * (w - len(footer) - 1))
            except curses.error:
                pass

            stdscr.refresh()

            # Handle keys
            key = stdscr.getch()

            if key == ord('q') or key == ord('Q') or key == 27:  # q, Q or ESC
                break
            elif key == curses.KEY_UP or key == ord('k') or key == ord('K'):
                if top_line > 0:
                    top_line -= 1
                    bottom_line = min(top_line + h - 3, total_lines - 1)
            elif key == curses.KEY_DOWN or key == ord('j') or key == ord('J'):
                if bottom_line < total_lines - 1:
                    top_line += 1
                    bottom_line = min(top_line + h - 3, total_lines - 1)
            elif key == curses.KEY_PPAGE:  # Page Up
                top_line = max(0, top_line - (h - 3))
                bottom_line = min(top_line + h - 3, total_lines - 1)
            elif key == curses.KEY_NPAGE:  # Page Down
                top_line = min(total_lines - 1, top_line + (h - 3))
                bottom_line = min(top_line + h - 3, total_lines - 1)
            elif key == curses.KEY_HOME:
                top_line = 0
                bottom_line = min(h - 3, total_lines - 1)
            elif key == curses.KEY_END:
                top_line = max(0, total_lines - (h - 2))
                bottom_line = total_lines - 1

    def toggle_current_item(self):
        """Toggle the currently selected item."""
        # Create a list of visible items for the current view
        visible_items = []
        for i, module in enumerate(self.modules):
            visible_items.append((i, 0, module))  # (index, indent_level, module)
            if i in self.expanded_modules:
                for subsection_name in module.subsections:
                    visible_items.append((i, 1, subsection_name))

        # Get the current item
        module_idx, indent_level, item = visible_items[self.current_pos]

        if isinstance(item, str):  # This is a subsection
            # Toggle the subsection
            module = self.modules[module_idx]
            module.subsections[item] = not module.subsections[item]
            self.status_message = f"Subsection '{item}' " + \
                                  ("enabled" if module.subsections[item] else "disabled")
        else:  # This is a module
            # Toggle the module
            module = item
            module.enabled = not module.enabled
            self.status_message = f"Module '{module.name}' " + \
                                  ("enabled" if module.enabled else "disabled")

    def toggle_expand_current_module(self):
        """Toggle the expansion state of the current module."""
        # Create a list of visible items for the current view
        visible_items = []
        for i, module in enumerate(self.modules):
            visible_items.append((i, 0, module))  # (index, indent_level, module)
            if i in self.expanded_modules:
                for subsection_name in module.subsections:
                    visible_items.append((i, 1, subsection_name))

        # Get the current item
        module_idx, indent_level, item = visible_items[self.current_pos]

        if indent_level == 0:  # This is a module
            # Toggle expansion
            if module_idx in self.expanded_modules:
                self.expanded_modules.remove(module_idx)
                self.status_message = f"Module '{self.modules[module_idx].name}' collapsed"
            else:
                self.expanded_modules.add(module_idx)
                self.status_message = f"Module '{self.modules[module_idx].name}' expanded"

    def run(self):
        """Run the enhanced TUI."""
        return curses.wrapper(self._run_ui)

    def _run_ui(self, stdscr):
        """Internal method to run the UI with curses."""
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(-1)  # No timeout for getch

        # Run the menu loop
        while not self.run_selected:
            self.draw_main_menu(stdscr)
            self.process_main_input(stdscr)

        # Return the selected modules
        return [module for module in self.modules if module.enabled]

    def process_main_input(self, stdscr):
        """Process input in the main menu."""
        key = stdscr.getch()

        if key == ord('q') or key == ord('Q'):
            # Confirm quit
            h, w = stdscr.getmaxyx()
            confirm_msg = "Are you sure you want to quit? (y/n)"
            stdscr.attron(curses.A_BOLD)
            stdscr.addstr(h - 4, (w - len(confirm_msg)) // 2, confirm_msg)
            stdscr.attroff(curses.A_BOLD)
            stdscr.refresh()

            confirm = stdscr.getch()
            if confirm == ord('y') or confirm == ord('Y'):
                sys.exit(0)

        elif key == ord('r') or key == ord('R'):
            # Run diagnostics
            selected_modules = [module for module in self.modules if module.enabled]
            if not selected_modules:
                self.status_message = "Error: No modules selected. Please select at least one module."
            else:
                self.run_selected = True

        elif key == ord('e') or key == ord('E'):
            # Show export options
            # This is just a placeholder - actual export happens after running diagnostics
            self.status_message = "Note: Export options available after running diagnostics"

        elif key == curses.KEY_UP or key == ord('k') or key == ord('K'):
            # Move selection up
            self.current_pos = max(0, self.current_pos - 1)

        elif key == curses.KEY_DOWN or key == ord('j') or key == ord('J'):
            # Create a list of visible items for the current view
            visible_items = []
            for i, module in enumerate(self.modules):
                visible_items.append((i, 0, module))
                if i in self.expanded_modules:
                    for subsection_name in module.subsections:
                        visible_items.append((i, 1, subsection_name))

            # Move selection down
            self.current_pos = min(len(visible_items) - 1, self.current_pos + 1)

        elif key == ord(' '):
            # Toggle module or subsection (check/uncheck)
            self.toggle_current_item()

        elif key == 10 or key == 13:  # Enter key
            # Toggle expand/collapse for the current module
            self.toggle_expand_current_module()

        elif key == curses.KEY_RIGHT:
            # Expand the current module if it's not already expanded
            visible_items = []
            for i, module in enumerate(self.modules):
                visible_items.append((i, 0, module))
                if i in self.expanded_modules:
                    for subsection_name in module.subsections:
                        visible_items.append((i, 1, subsection_name))

            module_idx, indent_level, item = visible_items[self.current_pos]
            if indent_level == 0 and module_idx not in self.expanded_modules:
                self.expanded_modules.add(module_idx)
                self.status_message = f"Module '{self.modules[module_idx].name}' expanded"

        elif key == curses.KEY_LEFT:
            # Collapse the current module if it's expanded
            visible_items = []
            for i, module in enumerate(self.modules):
                visible_items.append((i, 0, module))
                if i in self.expanded_modules:
                    for subsection_name in module.subsections:
                        visible_items.append((i, 1, subsection_name))

            module_idx, indent_level, item = visible_items[self.current_pos]
            if indent_level == 0 and module_idx in self.expanded_modules:
                self.expanded_modules.remove(module_idx)
                self.status_message = f"Module '{self.modules[module_idx].name}' collapsed"

        elif key == ord('a') or key == ord('A'):
            # Enable all modules
            for module in self.modules:
                module.enabled = True
                module.set_all_subsections(True)
            self.status_message = "All modules and subsections enabled"

        elif key == ord('n') or key == ord('N'):
            # Disable all modules
            for module in self.modules:
                module.enabled = False
                module.set_all_subsections(False)
            self.status_message = "All modules and subsections disabled"

    def show_export_options(self, stdscr, report):
        """Show and process export options."""
        self.draw_export_menu(stdscr)

        # Get user choice
        choice = stdscr.getkey()

        if choice in ['1', '2', '3', '4', '5', '6']:
            result = self.handle_export_choice(choice, report, stdscr)

            if result == "__DISPLAY_ONLY__":
                # Display the report
                self.display_report(stdscr, report)
                return None
            else:
                return result
        elif choice.lower() == 'q':
            return "Export cancelled"
        else:
            return "Invalid choice"