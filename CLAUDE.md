# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PA-SSH-prep is a Windows GUI application that automates initial Palo Alto Networks firewall setup via SSH. It handles IP configuration, licensing, content updates, and PAN-OS upgrades.

## Technology Stack

- **Python 3.11+** - Main language
- **Netmiko** - SSH library with PAN-OS device support
- **tkinter** - GUI (built into Python)
- **PyInstaller** - Creates standalone Windows .exe

## Project Structure

```
PA-SSH-prep/
├── src/
│   ├── main.py              # Entry point, GUI setup, orchestration
│   ├── gui.py               # tkinter GUI components
│   ├── network_detect.py    # Windows network settings detection
│   ├── ssh_client.py        # Netmiko wrapper for PAN-OS
│   ├── firewall_config.py   # IP, DNS, password configuration
│   ├── licensing.py         # License fetch operations
│   ├── content_update.py    # Content download/install
│   ├── panos_upgrade.py     # PAN-OS upgrade logic & paths
│   └── utils.py             # Logging, beep alerts, validation
├── requirements.txt         # Python dependencies
├── build.bat               # PyInstaller build script
└── CLAUDE.md               # This guidance file
```

## Build Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run from source
python -m src.main

# Build standalone executable
build.bat
# Output: dist/PA-SSH-prep.exe
```

## Workflow

The application performs these phases:
1. **Initial Config** - Connect to 192.168.1.1 (factory default), set new IP/DNS/password, commit
2. **Licensing** - Reconnect to new IP, fetch licenses from Palo Alto
3. **Content Update** - Download and install latest threat content
4. **PAN-OS Upgrade** - Iterative upgrade through required version path

## Key Implementation Notes

- PAN-OS requires stepping through major versions (can't jump directly)
- Must download base version (X.Y.0) before point releases
- SSH polling after reboots with 30-second intervals
- Error beeps using Windows winsound for operator attention
- Network settings auto-detected from Windows ipconfig
