# Aegis SIEM

**Enterprise Security Information and Event Management System**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)

Aegis SIEM is a comprehensive security monitoring platform designed for enterprises. It provides real-time threat detection, anomaly analysis using machine learning, and centralized security event management across multiple devices.

---

## 🚀 Features

- **Real-time Monitoring** - Track system metrics, logs, commands, and processes across all devices
- **ML-Based Anomaly Detection** - Isolation Forest algorithm detects suspicious behavior automatically
- **Alert Management** - Comprehensive triage workflow with assignment and escalation
- **Multi-Platform Support** - Monitor Linux, Windows, and macOS systems
- **Role-Based Access Control** - Owner, Admin, and Device User roles
- **Interactive Dashboard** - Modern React-based web interface
- **Scalable Architecture** - PostgreSQL backend, FastAPI server, agent-based monitoring

---

## 📋 Quick Start

### Prerequisites

- **Server:** Debian 11+ or Ubuntu 20.04+ with 2GB RAM, 2 CPU cores
- **Agent:** Linux (Debian/Ubuntu/Arch), Windows, or macOS
- **Root/sudo access** for installation

### Installation

#### 1. Install Server (Debian/Ubuntu)

```bash
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/server-linux
sudo bash install.sh
```

This installs:

- PostgreSQL database
- Backend API server
- Frontend dashboard
- Nginx reverse proxy

**Access dashboard:** `http://YOUR_SERVER_IP`

#### 2. Install Agent (Debian/Ubuntu)

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

- Server URL
- Registration token (generate from dashboard)

---

## 📖 Documentation

- **[Installation Guide](installers/README.md)** - Complete setup instructions
- **[Testing Guide](TESTING_GUIDE.md)** - VM testing procedures
- **[Server Installer](installers/server-linux/README.md)** - Server installation details
- **[Agent Installer (Debian)](installers/agent-linux-deb/)** - Debian/Ubuntu agent setup
- **[Agent Installer (Arch)](installers/agent-linux-arch/README.md)** - Arch Linux agent setup

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│        Aegis Server                 │
│  ┌──────────────────────────────┐   │
│  │  React Dashboard (Nginx)     │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  FastAPI Backend             │   │
│  │  - REST API                  │   │
│  │  - ML Detection              │   │
│  │  - Alert Correlation         │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  PostgreSQL Database         │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
            ▲
            │ HTTPS/WebSocket
            │
    ┌───────┴───────┐
    │               │
┌───▼───┐       ┌───▼───┐
│Agent 1│       │Agent 2│
│(Linux)│       │(Arch) │
└───────┘       └───────┘
```

---

## 🛠️ Technology Stack

**Backend:**

- FastAPI (Python 3.11+)
- PostgreSQL
- asyncpg
- Pydantic

**Frontend:**

- React 18
- TypeScript
- Vite
- TailwindCSS

**ML Engine:**

- scikit-learn (Isolation Forest)
- pandas, numpy
- Feature engineering pipeline

**Agents:**

- Python 3.11+
- psutil (system metrics)
- systemd integration

---

## 🔒 Security Features

- **JWT Authentication** - Secure token-based authentication
- **RBAC** - Role-based access control
- **Encrypted Communication** - HTTPS/WSS support
- **Secure Credential Storage** - Hashed passwords (bcrypt)
- **ML Anomaly Detection** - Behavioral analysis
- **Alert Deduplication** - Prevents alert spam
- **Audit Logging** - Command and activity tracking

---

## 📊 System Requirements

### Server (Minimum)

- 2 CPU cores
- 2GB RAM
- 10GB disk space
- Debian 11+ or Ubuntu 20.04+

### Server (Recommended for 50+ devices)

- 4+ CPU cores
- 8GB RAM
- 100GB disk space
- SSD storage

### Agent (Per Device)

- 512MB RAM
- 1 CPU core
- 100MB disk space
- Linux, Windows, or macOS

---

## 🧪 Testing

### VM Testing

Test the complete installation on virtual machines:

1. Create Debian VM for server (2GB RAM, 2 CPU)
2. Create Arch VM for agent (1GB RAM, 1 CPU)
3. Follow [Testing Guide](TESTING_GUIDE.md)

### Test Scenarios

- Normal operation baseline
- High resource usage alerts
- Suspicious command detection
- Network activity monitoring
- ML anomaly detection

---

## 📦 Components

### Server (`aegis-server/`)

FastAPI backend with ML detection, alert correlation, and data management.

### Dashboard (`aegis-dashboard/`)

React-based web interface for monitoring and management.

### Agent (`aegis-agent/`)

Lightweight monitoring agent for data collection.

### ML Engine (`aegis-ml-engine/`)

Machine learning model training and evaluation tools.

### Installers (`installers/`)

Production-ready installation scripts for all platforms.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Author

**Mokshit Bindal**

- GitHub: [@MokshitBindal](https://github.com/MokshitBindal)

---

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/MokshitBindal/Aegis/issues)
- **Documentation:** See `installers/README.md` and component READMEs

---

## 🎯 Roadmap

- [x] Core monitoring (logs, metrics, commands, processes)
- [x] ML-based anomaly detection
- [x] Alert management and triage
- [x] Multi-platform agent support
- [x] Enterprise installers
- [ ] Windows agent installer
- [ ] macOS agent installer
- [ ] Mobile dashboard app
- [ ] Advanced reporting
- [ ] SIEM integrations (Splunk, ELK)

---

**Ready to secure your infrastructure? [Get started now!](installers/README.md)**
