# Linux System Diagnostic Tool

A comprehensive system information reporting tool for Linux diagnostics that generates concise, customizable reports with enhanced visual navigation.

## Features

- Interactive TUI (Text User Interface) for module selection
- Support for multiple output formats (text, HTML, JSON)
- Comprehensive system diagnostics covering:
  - Storage and partitions
  - Boot and GRUB configuration
  - Hardware information
  - System services
  - Network configuration
  - Security settings
  - Package management
  - User accounts
  - Logs and monitoring
- Detailed reporting with hierarchical organization
- Modular and extensible architecture

## Installation

### Method 1: Manual Installation

```bash
# Clone the repository
git clone https://github.com/eraxe/diagtool.git
cd sysdiag

# Install using the installation script
sudo python3 -m sysdiag.install install
```

### Method 2: From Source Directory

```bash
# Navigate to the source directory
cd /path/to/sysdiag

# Run directly (some features require root)
sudo python3 -m sysdiag.main
```

## Usage

### Basic Usage

```bash
sysdiag
```

This will launch the interactive TUI, where you can select which diagnostic modules to run.

### Command Line Options

```bash
# Run with all modules without interactive mode
sysdiag -y

# Specify an output file
sysdiag -o /path/to/report.txt

# Generate report in a specific format (txt, json, html)
sysdiag -f html

# Check all modules by default in the TUI
sysdiag -c

# Use ASCII characters instead of Unicode
sysdiag -a

# Show version information
sysdiag --version

# Show help message
sysdiag -h
```

## Project Structure

```
sysdiag/
├── __init__.py                 # Package initialization
├── main.py                     # Entry point script
├── install.py                  # Installation manager
├── modules/                    # Diagnostic modules
│   ├── __init__.py
│   ├── base.py                 # Base module class
│   ├── storage.py              # Storage/disk related modules 
│   ├── bootloader.py           # Boot related modules
│   ├── system.py               # System related modules
│   ├── network.py              # Network related modules
│   └── security.py             # Security related modules
└── ui/                         # User interface components
    ├── __init__.py
    ├── tui.py                  # Text User Interface
    └── report.py               # Report generation
```

## Diagnostic Modules

The tool includes the following diagnostic modules:

1. **Storage & Partition Modules**
   - Partition & Disk Layout
   - Filesystem Table & Mount Points
   - Storage I/O Performance

2. **Boot Related Modules**
   - Boot Loader Configurations
   - initramfs & Dracut Configuration
   - Boot Parameters
   - GRUB/Boot Partition Advanced Diagnostics

3. **System Information Modules**
   - Kernel Boot & System Logs
   - Hardware & Driver Information
   - Custom Scripts & Environmental Variables
   - Recovery & Emergency Diagnostics
   - System Service Status
   - Virtualization & Container Status
   - Log Analysis & Monitoring
   - Package Management

4. **Network Modules**
   - Network Configuration

5. **Security Modules**
   - Security Information
   - User Account Information

## Extending the Tool

### Adding a New Diagnostic Module

1. Create a new module class that extends `DiagnosticModule` in the appropriate file:

```python
from .base import DiagnosticModule

class MyNewModule(DiagnosticModule):
    """Module for my new diagnostics."""

    def __init__(self):
        super().__init__(
            "my_new_module",  # Module name
            "My New Diagnostic Module"  # Module description
        )
        self.subsections = {
            "subsection1": True,
            "subsection2": True
        }

    def run(self) -> Dict[str, str]:
        results = {}

        if self.subsections["subsection1"]:
            # Perform diagnostics for subsection1
            results["subsection1"] = "Results for subsection1"

        if self.subsections["subsection2"]:
            # Perform diagnostics for subsection2
            results["subsection2"] = "Results for subsection2"

        return results
```

2. Add your module to the module registry in `modules/__init__.py`:

```python
from .mynewfile import MyNewModule

def get_all_modules():
    """Return a list of all module instances."""
    return [
        # ... existing modules ...
        MyNewModule(),
    ]
```

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Linux community for the various diagnostic tools
- Python community for the libraries used in this project
