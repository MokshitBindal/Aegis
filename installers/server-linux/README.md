# Aegis SIEM Server Installer (Linux)

This directory contains the installation scripts for Aegis SIEM server (backend + dashboard) on Linux systems.

## Supported Systems

- Debian 11+
- Ubuntu 20.04+
- Ubuntu 22.04+

## What Gets Installed

- PostgreSQL database server
- Aegis backend API server (FastAPI)
- Aegis dashboard (React web UI)
- Nginx web server (reverse proxy)
- Systemd services for auto-start

## Installation

### Prerequisites

- Fresh Debian/Ubuntu server
- Root or sudo access
- Minimum 2GB RAM
- 10GB disk space
- Internet connection

### Quick Install

```bash
# Clone the repository
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/server-linux

# Run installer
sudo bash install.sh
```

### Interactive Setup

The installer will prompt you for:

1. **Database Name** (default: aegis_siem)
2. **Database User** (default: aegis_user)
3. **Database Password** (auto-generated or custom)
4. **Server API Port** (default: 8000)
5. **Dashboard Port** (default: 80)
6. **Domain** (optional)

### Automated/Silent Install

For automated deployments, export environment variables:

```bash
export AEGIS_DB_NAME="aegis_siem"
export AEGIS_DB_USER="aegis_user"
export AEGIS_DB_PASSWORD="your_secure_password"
export AEGIS_SERVER_PORT="8000"
export AEGIS_DASHBOARD_PORT="80"
export AEGIS_DOMAIN="siem.example.com"
export AEGIS_AUTO_CONFIRM="yes"

sudo -E bash install.sh
```

## Post-Installation

### Create First Admin User

```bash
cd /opt/aegis-siem/server
sudo -u aegis ./venv/bin/python scripts/generate_invitation.py
```

Use the invitation code to register via the web dashboard.

### Access Dashboard

```bash
# Get your server IP
hostname -I

# Access at:
# http://YOUR_SERVER_IP
```

### Service Management

```bash
# Check server status
sudo systemctl status aegis-server

# View logs
sudo journalctl -u aegis-server -f

# Restart server
sudo systemctl restart aegis-server

# Check Nginx
sudo systemctl status nginx
```

### Credentials

All credentials are saved to:
```
/etc/aegis-siem/credentials.txt
```

**IMPORTANT:** Backup this file securely!

## Configuration

### Server Configuration

Edit: `/etc/aegis-siem/server.conf`

```toml
[database]
user = "aegis_user"
password = "..."
database = "aegis_siem"
host = "localhost"
port = 5432

[jwt]
secret_key = "..."
algorithm = "HS256"
access_token_expire_minutes = 60
```

After changes:
```bash
sudo systemctl restart aegis-server
```

### Nginx Configuration

Edit: `/etc/nginx/sites-available/aegis-dashboard`

After changes:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Firewall Configuration

### Open Required Ports

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp    # Dashboard
sudo ufw allow 8000/tcp  # API (if accessed directly)
sudo ufw enable

# firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

### Using Self-Signed Certificate

```bash
# Generate certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/aegis-selfsigned.key \
  -out /etc/ssl/certs/aegis-selfsigned.crt

# Update Nginx config to use SSL
# (modify /etc/nginx/sites-available/aegis-dashboard)
```

## Uninstallation

```bash
cd /path/to/Aegis/installers/server-linux
sudo bash uninstall.sh
```

Options:
- Keep database and data (default: yes)
- Remove PostgreSQL database (optional)
- Remove system user

## Troubleshooting

### Server Won't Start

```bash
# Check logs
sudo journalctl -u aegis-server -n 50

# Common issues:
# 1. Database connection - verify PostgreSQL is running
# 2. Port already in use - check with: sudo netstat -tulpn | grep 8000
# 3. Permission issues - check file ownership: ls -la /opt/aegis-siem
```

### Dashboard Not Loading

```bash
# Check Nginx
sudo nginx -t
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Verify dashboard built correctly
ls -la /opt/aegis-siem/dashboard/dist
```

### Database Connection Issues

```bash
# Test PostgreSQL
sudo -u postgres psql -c "\l"

# Test connection from server
sudo -u aegis psql -h localhost -U aegis_user -d aegis_siem

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### Can't Access from Other Machines

```bash
# Check firewall
sudo ufw status
sudo iptables -L -n

# Check Nginx is listening
sudo netstat -tulpn | grep nginx

# Verify server bind address
# Should be 0.0.0.0, not 127.0.0.1
```

## Upgrade

To upgrade to a new version:

```bash
# Backup database
sudo -u postgres pg_dump aegis_siem > aegis_backup.sql

# Pull latest code
cd /path/to/Aegis
git pull origin main

# Stop services
sudo systemctl stop aegis-server

# Update server
cd aegis-server
sudo -u aegis ./venv/bin/pip install -r requirements.txt

# Update dashboard
cd ../aegis-dashboard
sudo -u aegis npm install
sudo -u aegis npm run build

# Copy new files
sudo cp -r dist/* /opt/aegis-siem/dashboard/dist/

# Restart services
sudo systemctl start aegis-server
sudo systemctl reload nginx
```

## System Requirements

### Minimum
- 2 CPU cores
- 2GB RAM
- 10GB disk space
- Ubuntu 20.04+ or Debian 11+

### Recommended
- 4 CPU cores
- 4GB RAM
- 50GB disk space (for logs/metrics)
- SSD storage

### Production (100+ agents)
- 8+ CPU cores
- 16GB+ RAM
- 500GB+ disk space
- Dedicated database server

## Security Recommendations

1. **Change default ports** - Use non-standard ports
2. **Enable firewall** - Only allow required ports
3. **Use HTTPS** - Get SSL certificate
4. **Regular backups** - Backup database daily
5. **Update regularly** - Keep system packages updated
6. **Strong passwords** - Use generated passwords
7. **Monitor logs** - Check for suspicious activity
8. **Limit access** - Use VPN or IP whitelist

## Support

- Documentation: See `/opt/aegis-siem/docs/`
- Logs: `/var/log/aegis-siem/`
- GitHub Issues: https://github.com/MokshitBindal/Aegis/issues

## Files and Directories

```
/opt/aegis-siem/          # Installation directory
├── server/               # Backend server
│   ├── venv/            # Python virtual environment
│   ├── models/          # ML models
│   └── config.toml      # Configuration (symlink)
└── dashboard/           # Frontend dashboard
    └── dist/            # Built static files

/etc/aegis-siem/         # Configuration
├── server.conf          # Main configuration
└── credentials.txt      # Installation credentials

/var/log/aegis-siem/     # Log files
├── server.log           # Server logs
└── server-error.log     # Error logs

/var/lib/aegis-siem/     # Data directory
```

## License

See main repository LICENSE file.
