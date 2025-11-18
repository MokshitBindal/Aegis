# Aegis SIEM Agent Installer (Arch Linux)

Installation scripts for Aegis SIEM Agent on Arch Linux systems.

## Installation Methods

### Method 1: Direct Script Installation (Recommended)

```bash
# Clone repository
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/agent-linux-arch

# Run installer
sudo bash install.sh
```

### Method 2: Build and Install Package

```bash
# Install build dependencies
sudo pacman -S base-devel

# Build package
cd Aegis/installers/agent-linux-arch
makepkg -si

# Configure and register
sudo aegis-agent-setup
```

## What Gets Installed

- Aegis agent monitoring service
- Python virtual environment with dependencies
- Systemd service for auto-start
- Log rotation configuration

## Prerequisites

- Arch Linux (latest)
- Root access
- Internet connection
- Aegis server URL and registration token

## Post-Installation

### Check Agent Status

```bash
sudo systemctl status aegis-agent
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u aegis-agent -f

# Last 50 lines
sudo journalctl -u aegis-agent -n 50
```

### Restart Agent

```bash
sudo systemctl restart aegis-agent
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop aegis-agent
sudo systemctl disable aegis-agent

# Remove files
sudo rm -rf /opt/aegis-agent
sudo rm -rf /etc/aegis-agent
sudo rm -rf /var/log/aegis-agent
sudo rm /etc/systemd/system/aegis-agent.service

# Remove user
sudo userdel -r aegis-agent

# Reload systemd
sudo systemctl daemon-reload
```

Or if installed via package:

```bash
sudo pacman -R aegis-agent
```

## Troubleshooting

### Agent Won't Start

```bash
# Check logs
sudo journalctl -u aegis-agent -n 100

# Check permissions
ls -la /opt/aegis-agent

# Verify Python environment
sudo -u aegis-agent /opt/aegis-agent/venv/bin/python --version
```

### Can't Connect to Server

```bash
# Test connectivity
curl -v http://YOUR_SERVER:8000/health

# Check firewall
sudo iptables -L -n

# Verify credentials
sudo cat /opt/aegis-agent/agent.credentials
```

## Security Features

The systemd service includes hardening:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=true` - No access to home directories

## Files and Directories

```
/opt/aegis-agent/          # Installation directory
├── venv/                  # Python virtual environment
├── main.py               # Agent entry point
├── agent.id              # Unique agent identifier
└── agent.credentials     # Server credentials

/etc/aegis-agent/         # Configuration
└── install-info.txt      # Installation details

/var/log/aegis-agent/     # Logs
├── agent.log             # Standard output
└── agent-error.log       # Error output
```

## Support

- GitHub Issues: https://github.com/MokshitBindal/Aegis/issues
- Documentation: See main repository
