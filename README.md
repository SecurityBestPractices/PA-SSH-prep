# PA-SSH-prep

![Coverage](coverage.svg)

Windows GUI application that automates initial Palo Alto Networks firewall setup via SSH.

## Features

- **One-click setup** - Automates the entire initial configuration process
- **Network auto-detection** - Automatically detects subnet mask, gateway, and DNS from your Windows network adapter
- **License activation** - Fetches licenses from Palo Alto license server
- **Content updates** - Downloads and installs the latest threat content
- **PAN-OS upgrades** - Automatically determines upgrade path and handles multi-step upgrades with reboots
- **Progress tracking** - Real-time status updates and progress bar
- **Error handling** - Audio alerts and helpful suggestions when issues occur

## Requirements

- Windows 10/11
- Network connectivity to the firewall (default: 192.168.1.1)
- Firewall with factory default settings (admin/admin)

## Installation

### Option 1: Download Release
Download the latest `PA-SSH-prep.exe` from [Releases](https://github.com/SecurityBestPractices/PA-SSH-prep/releases).

### Option 2: Build from Source
```bash
# Clone the repository
git clone https://github.com/SecurityBestPractices/PA-SSH-prep.git
cd PA-SSH-prep

# Install dependencies
pip install -r requirements.txt

# Build executable
pyinstaller --onefile --windowed --name PA-SSH-prep ^
    --hidden-import=netmiko --hidden-import=paramiko ^
    --hidden-import=ntc_templates --hidden-import=textfsm ^
    --collect-all=netmiko --collect-all=ntc_templates ^
    launcher.py

# Output: dist/PA-SSH-prep.exe
```

## Usage

1. Connect your computer to the same network as the firewall (192.168.1.x)
2. Run `PA-SSH-prep.exe`
3. Enter the **new management IP** for the firewall
4. Enter a **new admin password** (min 8 chars, must include uppercase, lowercase, and number)
5. Enter the **target PAN-OS version** (e.g., `11.2.10-h2` or `12.1.4`)
6. Review the auto-detected network settings (edit if needed)
7. Click **OK** to start the setup process

The application will:
1. Connect to the firewall at 192.168.1.1 with default credentials
2. Configure management IP, subnet, gateway, and DNS
3. Change the admin password
4. Commit and reconnect on the new IP
5. Fetch licenses
6. Download and install content updates
7. Upgrade PAN-OS through the required version path (with automatic reboots)

## Workflow Phases

| Phase | Description |
|-------|-------------|
| 1. Initial Config | Set IP, DNS, password on factory-default firewall |
| 2. Licensing | Fetch licenses from Palo Alto license server |
| 3. Content Update | Download and install latest threat content |
| 4. PAN-OS Upgrade | Step through required versions to reach target |

## PAN-OS Upgrade Paths

The application automatically handles required upgrade steps:

```
9.0.x → 9.1.x → 10.0.x → 10.1.x → 10.2.x → 11.0.x → 11.1.x → 11.2.x → 12.1.x
```

Note: The base version for 12.1 is 12.1.2 (not 12.1.0).

Each major version upgrade requires a reboot. The application waits for the firewall to come back online before continuing.

## Version Format

Enter the target version in one of these formats:
- `X.Y.Z` - Standard release (e.g., `11.2.4`, `12.1.4`)
- `X.Y.Z-hN` - Hotfix release (e.g., `11.2.10-h2`)

## Technology Stack

- **Python 3.11+** - Core language
- **Netmiko** - SSH library with PAN-OS device support
- **tkinter** - GUI framework (built into Python)
- **PyInstaller** - Packages as standalone Windows executable

## Testing

Run the test suite with pytest:

```bash
# Install dependencies (includes pytest)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/test_utils.py
```

The test suite includes 312 tests with 98% code coverage.

## Troubleshooting

| Error | Solution |
|-------|----------|
| Connection refused | Ensure firewall is powered on and SSH is enabled |
| Authentication failed | Verify firewall has factory default credentials (admin/admin) |
| License fetch failed | Check firewall has internet connectivity |
| Timeout waiting for reboot | Allow more time; upgrades can take 10+ minutes |

## License

MIT License

## Contributing

Pull requests welcome. For major changes, please open an issue first to discuss.
