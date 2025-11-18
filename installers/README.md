# Aegis SIEM - Installation Packages

This directory contains enterprise-ready installation packages for Aegis SIEM.

## 📦 Available Installers

### Server + Dashboard (Unified Package)

| Platform | Installer | Status |
|----------|-----------|--------|
| Debian/Ubuntu | `server-linux/install.sh` | ✅ Ready |
| RHEL/CentOS | Coming soon | 🚧 Planned |
| Windows Server | Coming soon | 🚧 Planned |

### Agent (Monitoring Client)

| Platform | Installer | Status |
|----------|-----------|--------|
| Debian/Ubuntu | `agent-linux-deb/install.sh` | ✅ Ready |
| Arch Linux | `agent-linux-arch/install.sh` | ✅ Ready |
| Windows | Coming soon | 🚧 Planned |
| macOS | Coming soon | 🚧 Planned |

## 🚀 Quick Start

### Step 1: Install Server (Debian/Ubuntu)

```bash
# On your server machine
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/server-linux
sudo bash install.sh
```

This installs:
- PostgreSQL database
- Aegis backend server (FastAPI)
- Aegis dashboard (React web UI)
- Nginx reverse proxy
- Systemd services

**Access dashboard at:** `http://YOUR_SERVER_IP`

### Step 2: Create Admin User

```bash
cd /opt/aegis-siem/server
sudo -u aegis ./venv/bin/python scripts/generate_invitation.py
```

Use the invitation code to register via the dashboard.

### Step 3: Install Agents (On Each Device)

**For Debian/Ubuntu:**
```bash
cd Aegis/installers/agent-linux-deb
sudo bash install.sh
```

**For Arch Linux:**
```bash
cd Aegis/installers/agent-linux-arch
sudo bash install.sh
```

You'll need:
- Server URL (e.g., `http://192.168.1.100:8000`)
- Registration token (generate from dashboard or server)

## 📋 Deployment Scenarios

### Scenario 1: Small Office (5-10 Devices)

**Hardware:**
- 1x Server: 2 CPU, 4GB RAM, 50GB SSD
- Desktop/laptop agents

**Steps:**
1. Install server on dedicated machine or VM
2. Access dashboard, create users
3. Generate registration tokens
4. Install agents on each device
5. Configure alerts and monitoring

### Scenario 2: Enterprise (100+ Devices)

**Hardware:**
- 1x Server: 8 CPU, 16GB RAM, 500GB SSD
- Database on separate machine (recommended)
- Load balancer (optional)

**Steps:**
1. Install PostgreSQL on dedicated database server
2. Install Aegis server pointing to external database
3. Set up reverse proxy/load balancer
4. Deploy agents using configuration management (Ansible/Puppet)
5. Configure high availability

### Scenario 3: MSP/Multi-Tenant

**Hardware:**
- Multiple isolated server instances
- Kubernetes cluster (advanced)

**Steps:**
1. Deploy separate Aegis instance per customer
2. Use virtual appliances or containers
3. Centralized monitoring dashboard
4. Automated deployment pipeline

## 🏗️ Installation Architecture

```
┌─────────────────────────────────────────┐
│           Aegis Server                  │
│  ┌──────────────────────────────────┐   │
│  │  Nginx (Port 80/443)             │   │
│  │    ├─> Dashboard (Static)        │   │
│  │    └─> API Proxy → Backend       │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Backend Server (Port 8000)      │   │
│  │    ├─> FastAPI                   │   │
│  │    ├─> ML Detection              │   │
│  │    └─> Alert Correlation         │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  PostgreSQL Database             │   │
│  │    ├─> Logs, Metrics, Alerts     │   │
│  │    └─> User Management           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
                   ▲
                   │ HTTPS/WebSocket
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐          ┌────▼────┐
   │ Agent 1 │          │ Agent 2 │
   │ (Linux) │          │ (Arch)  │
   └─────────┘          └─────────┘
```

## 🔧 Installation Details

### Server Installer Features

- ✅ **Automated setup** - PostgreSQL, Python, Node.js, Nginx
- ✅ **Secure by default** - Generated passwords, JWT secrets
- ✅ **Systemd integration** - Auto-start on boot
- ✅ **Log management** - Centralized logging
- ✅ **Configuration backup** - Credentials saved securely
- ✅ **Uninstall script** - Clean removal option

### Agent Installer Features

- ✅ **Auto-registration** - One-command setup with token
- ✅ **Systemd service** - Runs as system service
- ✅ **Minimal dependencies** - Python + psutil
- ✅ **Secure communication** - HTTPS with JWT
- ✅ **Log rotation** - Automatic log management
- ✅ **Easy uninstall** - Clean removal

## 📁 Directory Structure

```
installers/
├── README.md (this file)
│
├── server-linux/          # Server + Dashboard (Debian/Ubuntu)
│   ├── install.sh         # Main installation script
│   ├── uninstall.sh       # Removal script
│   └── README.md          # Detailed documentation
│
├── agent-linux-deb/       # Agent for Debian/Ubuntu
│   ├── install.sh         # Installation script
│   ├── uninstall.sh       # Removal script
│   └── README.md          # Documentation
│
└── agent-linux-arch/      # Agent for Arch Linux
    ├── install.sh         # Installation script
    ├── PKGBUILD          # Arch package build file
    └── README.md          # Documentation
```

## 🛡️ Security Recommendations

### Server Hardening

1. **Firewall Configuration**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8000/tcp
   sudo ufw enable
   ```

2. **SSL/HTTPS Setup**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

3. **Database Security**
   - Change PostgreSQL default passwords
   - Restrict network access
   - Enable SSL connections

4. **Regular Updates**
   ```bash
   sudo apt-get update && sudo apt-get upgrade
   ```

### Agent Security

1. **Principle of Least Privilege**
   - Agents run as dedicated user
   - Minimal file system access

2. **Encrypted Communication**
   - Use HTTPS for server connection
   - JWT authentication

3. **Log Monitoring**
   - Monitor agent logs for anomalies
   - Alert on connection failures

## 🧪 Testing Your Installation

### Server Health Check

```bash
# Check all services
sudo systemctl status aegis-server
sudo systemctl status nginx
sudo systemctl status postgresql

# Test API endpoint
curl http://localhost:8000/health

# Check database connection
sudo -u postgres psql -d aegis_siem -c "SELECT COUNT(*) FROM users;"
```

### Agent Health Check

```bash
# Check agent service
sudo systemctl status aegis-agent

# View real-time logs
sudo journalctl -u aegis-agent -f

# Verify connection to server
sudo tail -f /var/log/aegis-agent/agent.log | grep "connected"
```

### Dashboard Check

1. Open browser: `http://YOUR_SERVER_IP`
2. Register with invitation code
3. Login with credentials
4. Check devices page - should see registered agents
5. Check alerts page - should see system data

## 🐛 Troubleshooting

### Common Server Issues

**Problem:** Database connection failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -l

# Check config
sudo cat /etc/aegis-siem/server.conf
```

**Problem:** Nginx 502 Bad Gateway
```bash
# Check backend status
sudo systemctl status aegis-server

# Check backend logs
sudo journalctl -u aegis-server -n 50

# Test backend directly
curl http://localhost:8000/
```

### Common Agent Issues

**Problem:** Agent won't start
```bash
# Check logs
sudo journalctl -u aegis-agent -n 100

# Verify Python environment
sudo -u aegis-agent /opt/aegis-agent/venv/bin/python --version

# Check permissions
sudo ls -la /opt/aegis-agent
```

**Problem:** Can't register agent
```bash
# Test server connectivity
curl -v http://YOUR_SERVER:8000/health

# Check firewall
sudo ufw status

# Verify token
# (Token must be valid and not expired)
```

## 📚 Additional Documentation

- **Server Installation:** `server-linux/README.md`
- **Agent Installation (Debian):** `agent-linux-deb/README.md`
- **Agent Installation (Arch):** `agent-linux-arch/README.md`
- **Main Documentation:** `../DEPLOYMENT_GUIDE.md`
- **Project Knowledge Base:** `../PROJECT_KNOWLEDGE_BASE.md`

## 🔄 Upgrade Process

### Server Upgrade

```bash
# Backup database
sudo -u postgres pg_dump aegis_siem > backup.sql

# Stop services
sudo systemctl stop aegis-server nginx

# Update code
cd /path/to/Aegis
git pull

# Update dependencies
cd /opt/aegis-siem/server
sudo -u aegis ./venv/bin/pip install -r requirements.txt

# Rebuild dashboard
cd /opt/aegis-siem/dashboard
sudo -u aegis npm install
sudo -u aegis npm run build

# Restart services
sudo systemctl start aegis-server nginx
```

### Agent Upgrade

```bash
# Stop agent
sudo systemctl stop aegis-agent

# Update code
cd /path/to/Aegis
git pull

# Update agent files
sudo cp -r aegis-agent/* /opt/aegis-agent/

# Update dependencies
cd /opt/aegis-agent
sudo -u aegis-agent ./venv/bin/pip install -r requirements.txt

# Start agent
sudo systemctl start aegis-agent
```

## 💼 Enterprise Support

### Deployment Services

We offer professional installation and configuration services:
- Automated deployment scripts
- Custom integrations
- Training and support
- Maintenance contracts

### Contact

- Email: your-email@example.com
- GitHub Issues: https://github.com/MokshitBindal/Aegis/issues

## 📄 License

See main repository LICENSE file.

---

**Ready to deploy Aegis SIEM? Start with the server installation!**

```bash
cd installers/server-linux && sudo bash install.sh
```
