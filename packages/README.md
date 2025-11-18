# Aegis SIEM - Installation Packages

This directory contains build scripts for creating installation packages for Aegis SIEM.

## 📦 Available Packages

### Server Package
- **Platform:** Ubuntu/Debian (`.deb`)
- **File:** `aegis-siem-server_1.0.0_amd64.deb`
- **Includes:** Server, Dashboard, PostgreSQL integration, Nginx configuration

### Agent Packages
- **Ubuntu/Debian:** `aegis-siem-agent_1.0.0_amd64.deb`
- **Windows:** `Aegis-SIEM-Agent-1.0.0-Windows-x64.exe`
- **macOS:** `Aegis-SIEM-Agent-1.0.0-macOS.pkg`

## 🏗️ Building Packages

### Quick Build (All Platforms)

```bash
# Build all available packages
bash packages/build-all.sh
```

### Individual Builds

#### Server Package (Ubuntu/Debian)
```bash
bash packages/build-server-deb.sh
```

**Requirements:**
- dpkg-dev
- rsync
- Node.js 20+

#### Agent Package (Ubuntu/Debian)
```bash
bash packages/build-agent-deb.sh
```

**Requirements:**
- dpkg-dev
- rsync

#### Agent Package (macOS)
```bash
# Run on macOS
bash packages/build-agent-macos.sh
```

**Requirements:**
- macOS with pkgbuild
- Python 3.11+

#### Agent Package (Windows)
```powershell
# Run on Windows
powershell -File packages\build-agent-windows.ps1

# Then build with NSIS
makensis packages\aegis-agent-windows\installer.nsi
```

**Requirements:**
- NSIS (Nullsoft Scriptable Install System)
- Python 3.11+

## 📥 Installation

### Server (Ubuntu/Debian)

```bash
# Install package
sudo dpkg -i dist/aegis-siem-server_1.0.0_amd64.deb

# Install dependencies if needed
sudo apt-get install -f

# Configure
sudo nano /opt/aegis-siem/server/.env

# Start server
sudo systemctl start aegis-server
sudo systemctl status aegis-server

# Access dashboard
open http://localhost
```

### Agent (Ubuntu/Debian)

```bash
# Install package
sudo dpkg -i dist/aegis-siem-agent_1.0.0_amd64.deb

# Configure
sudo nano /opt/aegis-agent/.env

# Start agent
sudo systemctl start aegis-agent
sudo systemctl status aegis-agent
```

### Agent (Windows)

1. Run `Aegis-SIEM-Agent-1.0.0-Windows-x64.exe`
2. Follow installation wizard
3. Configure `C:\Program Files\Aegis\Agent\.env`
4. Start service: `sc start AegisSIEMAgent`

### Agent (macOS)

```bash
# Install package
sudo installer -pkg dist/Aegis-SIEM-Agent-1.0.0-macOS.pkg -target /

# Configure
sudo nano /usr/local/aegis-agent/.env

# Start agent
sudo launchctl start com.aegis.agent

# Check logs
tail -f /var/log/aegis-agent.log
```

## 🔧 Package Structure

### Server Package Structure
```
/opt/aegis-siem/
├── server/              # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── ...
└── dashboard/           # React frontend
    ├── package.json
    └── ...

/etc/systemd/system/
└── aegis-server.service

/etc/nginx/sites-available/
└── aegis-siem

/var/log/aegis-siem/
```

### Agent Package Structure
```
/opt/aegis-agent/        # Linux
C:\Program Files\Aegis\Agent\  # Windows
/usr/local/aegis-agent/  # macOS

Configuration:
- .env or .env.example

Logs:
- /var/log/aegis-agent/ (Linux/macOS)
- Windows Event Log (Windows)
```

## 📋 Version Information

**Current Version:** 1.0.0

Update version numbers in:
- `packages/aegis-server-deb/DEBIAN/control`
- `packages/aegis-agent-deb/DEBIAN/control`
- `packages/build-*.sh` scripts
- `.github/workflows/release.yml`

## 🚀 GitHub Release Workflow

Automated package building is configured in `.github/workflows/release.yml`.

### Create Release

```bash
# Tag a release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# GitHub Actions will automatically:
# 1. Build all packages
# 2. Create GitHub release
# 3. Upload packages as release assets
```

### Manual Release

```bash
# Trigger manual release
gh workflow run release.yml -f version=1.0.0
```

## 🐛 Troubleshooting

### Build Errors

**Missing dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install dpkg-dev rsync nodejs npm

# macOS
brew install rsync
```

**Permission errors:**
```bash
# Make scripts executable
chmod +x packages/*.sh
chmod +x packages/aegis-server-deb/DEBIAN/*
chmod +x packages/aegis-agent-deb/DEBIAN/*
```

### Installation Issues

**Server won't start:**
```bash
# Check logs
sudo journalctl -u aegis-server -f

# Check service status
sudo systemctl status aegis-server

# Verify database
sudo -u postgres psql -l | grep aegis
```

**Agent connection issues:**
```bash
# Check agent logs
sudo journalctl -u aegis-agent -f

# Verify configuration
cat /opt/aegis-agent/.env

# Test server connectivity
curl -v https://your-server/api/health
```

## 📚 Additional Resources

- [Installation Guide](../installers/README.md)
- [Testing Guide](../TESTING_GUIDE.md)
- [Main README](../README.md)
- [GitHub Repository](https://github.com/MokshitBindal/Aegis)

## 🤝 Contributing

To add support for new platforms:

1. Create build script: `packages/build-[component]-[platform].sh`
2. Add package metadata (control files, manifests)
3. Update `packages/build-all.sh`
4. Add to `.github/workflows/release.yml`
5. Update this README

## 📄 License

MIT License - See [LICENSE](../LICENSE) for details
