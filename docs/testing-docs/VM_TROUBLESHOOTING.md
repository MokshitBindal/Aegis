# Aegis SIEM - VM Testing Troubleshooting Guide

**Quick fixes for common issues during VM testing**

---

## 🔧 Server Issues (VM 1 - Arch)

### PostgreSQL Won't Start

**Symptoms:**

```bash
sudo systemctl status postgresql
# Shows: failed, exit code
```

**Solutions:**

```bash
# 1. Check if PostgreSQL is initialized
ls -la /var/lib/postgres/data/

# If empty or missing, initialize:
sudo -u postgres initdb -D /var/lib/postgres/data

# 2. Check permissions
sudo chown -R postgres:postgres /var/lib/postgres/data
sudo chmod 700 /var/lib/postgres/data

# 3. Try starting manually
sudo -u postgres postgres -D /var/lib/postgres/data

# 4. Check logs
sudo journalctl -u postgresql -n 100

# 5. Restart
sudo systemctl restart postgresql
```

---

### Aegis Server Won't Start

**Symptoms:**

```bash
sudo systemctl status aegis-server
# Shows: failed, exit code 1
```

**Solutions:**

```bash
# 1. Check logs
sudo journalctl -u aegis-server -n 100

# Common issues:

# a) Database connection failed
# Edit config.toml with correct credentials
cd ~/Aegis/aegis-server
nano config.toml

# Test database connection
psql -h localhost -U aegis_user -d aegis_db
# If fails, recreate user:
sudo -u postgres psql
DROP USER IF EXISTS aegis_user;
CREATE USER aegis_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aegis_db TO aegis_user;
\q

# b) Port 8000 already in use
sudo netstat -tulpn | grep 8000
# Kill conflicting process or change port in systemd service

# c) Python dependencies missing
cd ~/Aegis/aegis-server
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# d) Permission issues
sudo chown -R aegis:aegis ~/Aegis/aegis-server

# 2. Try running manually to see errors
cd ~/Aegis/aegis-server
source venv/bin/activate
python main.py
# Or:
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. Recreate systemd service
sudo nano /etc/systemd/system/aegis-server.service
# Verify paths are correct

sudo systemctl daemon-reload
sudo systemctl restart aegis-server
```

---

### Dashboard Shows 404 Not Found

**Symptoms:**

- Browser shows "404 Not Found" when accessing server IP
- Or Nginx default page appears

**Solutions:**

```bash
# 1. Check if dashboard is built
ls -la ~/Aegis/aegis-dashboard/dist/
# Should contain: index.html, assets/, etc.

# If missing, rebuild:
cd ~/Aegis/aegis-dashboard
npm install
npm run build

# 2. Check Nginx configuration
sudo nano /etc/nginx/conf.d/aegis-dashboard.conf
# Verify root path: root /home/aegis/Aegis/aegis-dashboard/dist;

# 3. Test Nginx config
sudo nginx -t

# 4. Check file permissions
sudo chmod 755 ~/Aegis/aegis-dashboard/dist
sudo chmod 644 ~/Aegis/aegis-dashboard/dist/index.html

# 5. Check Nginx is running
sudo systemctl status nginx

# 6. View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# 7. Restart Nginx
sudo systemctl restart nginx

# 8. Test directly
curl http://localhost/
# Should return HTML content

# 9. Check firewall (if enabled)
sudo ufw status
sudo ufw allow 80/tcp
```

---

### API Returns 500 Internal Server Error

**Symptoms:**

- Dashboard loads but API calls fail
- Browser console shows 500 errors

**Solutions:**

```bash
# 1. Check server logs in real-time
sudo journalctl -u aegis-server -f

# 2. Test API directly
curl http://localhost:8000/health

# 3. Common causes:

# a) Database connection issues
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection from server
cd ~/Aegis/aegis-server
source venv/bin/activate
python << EOF
import asyncpg
import asyncio

async def test():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            database='aegis_db',
            user='aegis_user',
            password='your_password'
        )
        print("✅ Database connection successful")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test())
EOF

# b) Missing database tables
cd ~/Aegis/aegis-server
source venv/bin/activate
python aegis-manage.py init-db

# c) JWT secret not configured
nano config.toml
# Ensure [jwt] section has secret_key

# 4. Restart server
sudo systemctl restart aegis-server
```

---

### Can't Login to Dashboard

**Symptoms:**

- Login page loads but credentials don't work
- "Invalid credentials" error

**Solutions:**

```bash
# 1. Verify admin user exists
sudo -u postgres psql -d aegis_db
SELECT username, email, role FROM users;
\q

# 2. If no users, create admin
cd ~/Aegis/aegis-server
source venv/bin/activate
python aegis-manage.py create-owner \
    --username admin \
    --email admin@aegis.local \
    --full-name "Admin User"

# 3. Reset password for existing user
python << EOF
import asyncio
from internal.auth.password import hash_password
from internal.storage.database import init_pool, execute_query

async def reset_password():
    await init_pool()
    new_password = "NewSecurePassword123!"
    hashed = hash_password(new_password)

    await execute_query("""
        UPDATE users SET password_hash = $1 WHERE username = 'admin'
    """, hashed)

    print(f"Password reset to: {new_password}")

asyncio.run(reset_password())
EOF

# 4. Check JWT configuration
cd ~/Aegis/aegis-server
nano config.toml
# Ensure secret_key is set in [jwt] section

# 5. Clear browser cache and cookies
# Then try logging in again
```

---

## 🤖 Agent Issues

### Agent Won't Install (Arch)

**Symptoms:**

```bash
cd ~/Aegis/installers/agent-linux-arch
sudo bash install.sh
# Shows errors during installation
```

**Solutions:**

```bash
# 1. Check prerequisites
which python3  # Should be >= 3.11
which systemctl

# 2. Install missing dependencies
sudo pacman -S python python-pip base-devel

# 3. Check if user aegis-agent already exists
id aegis-agent
# If exists and causing issues:
sudo userdel aegis-agent
sudo rm -rf /opt/aegis-agent

# 4. Try installation again
cd ~/Aegis/installers/agent-linux-arch
sudo bash install.sh

# 5. If still fails, check logs:
cat /tmp/aegis-agent-install.log
```

---

### Agent Won't Register

**Symptoms:**

```bash
sudo systemctl status aegis-agent
# Shows: Failed to register with server
```

**Solutions:**

```bash
# 1. Check server connectivity
curl http://<SERVER_IP>:8000/health
# Should return: {"status":"healthy",...}

# 2. Verify registration token is valid
# Generate new token on server:
ssh aegis@<SERVER_IP>
cd ~/Aegis/aegis-server
source venv/bin/activate
python << EOF
import asyncio
from internal.storage.database import init_pool, execute_query
import secrets

async def gen_token():
    await init_pool()
    token = secrets.token_urlsafe(32)
    await execute_query("""
        INSERT INTO device_tokens (token, created_by, expires_at)
        VALUES ($1, (SELECT id FROM users WHERE username='admin'), NOW() + INTERVAL '24 hours')
    """, token)
    print(f"New token: {token}")

asyncio.run(gen_token())
EOF

# 3. Re-register agent with new token
sudo systemctl stop aegis-agent
cd /opt/aegis-agent
sudo -u aegis-agent ./venv/bin/python main.py register --token <NEW_TOKEN>

# 4. Check agent configuration
sudo cat /opt/aegis-agent/.env
# Verify AEGIS_SERVER_URL is correct

# 5. Start agent
sudo systemctl start aegis-agent
sudo journalctl -u aegis-agent -f
```

---

### Agent Keeps Disconnecting

**Symptoms:**

```bash
sudo journalctl -u aegis-agent -f
# Shows: Connection lost, reconnecting...
```

**Solutions:**

```bash
# 1. Check network stability
ping -c 100 <SERVER_IP>
# Look for packet loss

# 2. Check server is running
curl http://<SERVER_IP>:8000/health

# 3. Check agent credentials
sudo cat /opt/aegis-agent/agent.credentials
# Should have device_id and token

# 4. Verify credentials on server
ssh aegis@<SERVER_IP>
sudo -u postgres psql -d aegis_db
SELECT id, name, status FROM devices;
\q

# 5. Check firewall rules
# On server:
sudo ufw status
sudo ufw allow 8000/tcp

# 6. Increase connection timeout (edit agent code if needed)
# Or check network quality

# 7. Restart both server and agent
# On server:
sudo systemctl restart aegis-server

# On agent:
sudo systemctl restart aegis-agent
```

---

### Agent Shows Offline in Dashboard

**Symptoms:**

- Agent service is running
- But dashboard shows device as "Offline"

**Solutions:**

```bash
# 1. Check agent status
sudo systemctl status aegis-agent
# Should be: active (running)

# 2. Check agent logs
sudo journalctl -u aegis-agent -n 100
# Look for connection errors

# 3. Test API connection from agent
curl http://<SERVER_IP>:8000/api/devices/heartbeat
# Should require auth, but confirms API is reachable

# 4. Check last_seen timestamp on server
ssh aegis@<SERVER_IP>
sudo -u postgres psql -d aegis_db
SELECT name, status, last_seen FROM devices;
\q

# 5. Verify credentials are correct
sudo cat /opt/aegis-agent/agent.credentials

# 6. Re-register agent
sudo systemctl stop aegis-agent
cd /opt/aegis-agent
sudo rm agent.credentials agent.id
# Generate new token on server
sudo -u aegis-agent ./venv/bin/python main.py register --token <NEW_TOKEN>
sudo systemctl start aegis-agent

# 7. Check dashboard refresh
# Hard refresh browser: Ctrl+Shift+R
# Or wait 60 seconds for auto-update
```

---

### No Data Appearing in Dashboard

**Symptoms:**

- Agent shows "Online"
- But no metrics, logs, or commands appear

**Solutions:**

```bash
# 1. Check agent is collecting data
sudo journalctl -u aegis-agent -f
# Should see: "Collected metrics", "Sending data", etc.

# 2. Check for errors in logs
sudo journalctl -u aegis-agent -n 100 | grep -i error

# 3. Verify database is receiving data
ssh aegis@<SERVER_IP>
sudo -u postgres psql -d aegis_db
SELECT COUNT(*) FROM metrics;
SELECT COUNT(*) FROM commands;
SELECT COUNT(*) FROM logs;
\q
# Should have data if agent is sending

# 4. Check collection intervals
# Edit agent config if collection is disabled
cd /opt/aegis-agent
sudo nano .env
# Ensure collection_interval is reasonable (e.g., 60)

# 5. Restart agent with verbose logging
sudo systemctl stop aegis-agent
cd /opt/aegis-agent
sudo -u aegis-agent ./venv/bin/python main.py --verbose

# 6. Check dashboard is querying correctly
# Open browser console (F12)
# Check for API errors when viewing device

# 7. Verify time synchronization
date
# Should match server time (important for time-series data)
```

---

## 🌐 Network Issues

### Can't Access Dashboard from Host Machine

**Symptoms:**

- Dashboard works on VM (curl localhost)
- But not accessible from host machine

**Solutions:**

```bash
# 1. Check VM network mode
# Should be: Bridged Adapter (not NAT)
# In VirtualBox:
VBoxManage modifyvm "Aegis-Arch-Server" --nic1 bridged --bridgeadapter1 eth0

# 2. Find VM IP
ip addr show
# Note the IP on main interface (e.g., 192.168.1.100)

# 3. Test from host
ping <VM_IP>
curl http://<VM_IP>

# 4. Check VM firewall
sudo ufw status
# If active:
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp

# Or disable for testing:
sudo ufw disable

# 5. Check Nginx is listening on all interfaces
sudo netstat -tulpn | grep :80
# Should show: 0.0.0.0:80

# Edit Nginx config if needed:
sudo nano /etc/nginx/conf.d/aegis-dashboard.conf
# Change: listen 80; to: listen 0.0.0.0:80;

# 6. Check iptables rules
sudo iptables -L -n
# Look for DROP rules blocking traffic
```

---

### VM 2 Can't Connect to VM 1 Server

**Symptoms:**

```bash
# On VM 2 (Ubuntu)
ping <VM1_IP>
# Fails or times out
```

**Solutions:**

```bash
# 1. Verify both VMs on same network
# Check VM network settings in VirtualBox/VMware
# Both should use same Bridged Adapter

# 2. Check VM IPs are on same subnet
# On VM 1:
ip addr show | grep inet
# On VM 2:
ip addr show | grep inet
# Should be like: 192.168.1.x/24 (same network)

# 3. Test basic connectivity
# From VM 2:
ping <VM1_IP>

# 4. Test specific port
# From VM 2:
telnet <VM1_IP> 8000
# Or:
nc -zv <VM1_IP> 8000

# 5. Check firewalls on both VMs
# VM 1:
sudo ufw status
sudo ufw allow from <VM2_IP>

# VM 2:
sudo ufw status

# 6. Check server is listening
# On VM 1:
sudo netstat -tulpn | grep :8000
# Should show: 0.0.0.0:8000 or :::8000

# 7. Try with IP instead of hostname
# On VM 2 agent config:
sudo nano /opt/aegis-agent/.env
# Change AEGIS_SERVER_URL to use IP: http://192.168.1.100:8000
```

---

## 🗄️ Database Issues

### Can't Connect to PostgreSQL

**Symptoms:**

```bash
psql -h localhost -U aegis_user -d aegis_db
# Shows: connection refused or authentication failed
```

**Solutions:**

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Check it's listening
sudo netstat -tulpn | grep 5432

# 3. Edit PostgreSQL config
sudo nano /var/lib/postgres/data/postgresql.conf
# Find: listen_addresses
# Set: listen_addresses = 'localhost'

# 4. Edit pg_hba.conf for authentication
sudo nano /var/lib/postgres/data/pg_hba.conf
# Add line:
# host    aegis_db    aegis_user    127.0.0.1/32    md5

# 5. Restart PostgreSQL
sudo systemctl restart postgresql

# 6. Test connection as postgres user first
sudo -u postgres psql
\l  # List databases
\q

# 7. Reset user password
sudo -u postgres psql
ALTER USER aegis_user WITH PASSWORD 'new_password';
\q

# Update config.toml with new password
```

---

### Database Tables Missing

**Symptoms:**

- Server starts but API returns errors
- Logs show: relation "users" does not exist

**Solutions:**

```bash
# 1. Check existing tables
sudo -u postgres psql -d aegis_db
\dt  # List tables
\q

# 2. Initialize database
cd ~/Aegis/aegis-server
source venv/bin/activate
python aegis-manage.py init-db

# 3. If init-db script doesn't exist, create tables manually:
sudo -u postgres psql -d aegis_db < ~/Aegis/aegis-server/schema.sql

# 4. Grant permissions
sudo -u postgres psql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aegis_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aegis_user;
\q

# 5. Verify tables exist
sudo -u postgres psql -d aegis_db
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
\q
```

---

## 📊 Performance Issues

### High CPU Usage on Server

**Solutions:**

```bash
# 1. Identify culprit
htop
# Look for aegis-server, postgres, nginx

# 2. Check if ML model is causing load
sudo journalctl -u aegis-server | grep -i "anomaly"

# 3. Optimize PostgreSQL
sudo nano /var/lib/postgres/data/postgresql.conf
# Adjust: shared_buffers, work_mem, etc.

# 4. Reduce agent collection frequency
# On agents:
sudo nano /opt/aegis-agent/.env
# Increase collection_interval from 60 to 120 (seconds)

# 5. Check for slow queries
sudo -u postgres psql -d aegis_db
SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

# 6. Add database indexes if needed
# Identify slow queries and add appropriate indexes
```

---

### High Memory Usage

**Solutions:**

```bash
# 1. Check memory usage
free -m
htop

# 2. Restart services to free memory
sudo systemctl restart aegis-server
sudo systemctl restart postgresql

# 3. Optimize PostgreSQL memory
sudo nano /var/lib/postgres/data/postgresql.conf
# Set: shared_buffers = 256MB (for 2GB RAM system)
# Set: effective_cache_size = 1GB

# 4. Check for memory leaks
# Monitor over time:
watch -n 5 'free -m'

# 5. Reduce agent data retention
# Configure server to archive old data
# Or purge old metrics/logs from database
```

---

## 🔄 Recovery Procedures

### Complete Reset - Start Fresh

**If everything is broken and you want to start over:**

```bash
# On Server VM (VM 1):
sudo systemctl stop aegis-server
sudo systemctl stop aegis-agent
sudo systemctl stop nginx
sudo systemctl stop postgresql

# Remove all Aegis data
sudo rm -rf /opt/aegis-siem
sudo rm -rf /opt/aegis-agent
sudo rm -rf ~/Aegis/aegis-server/venv
sudo rm -rf ~/Aegis/aegis-dashboard/node_modules
sudo rm /etc/systemd/system/aegis-*.service
sudo systemctl daemon-reload

# Drop and recreate database
sudo -u postgres psql
DROP DATABASE IF EXISTS aegis_db;
DROP USER IF EXISTS aegis_user;
CREATE DATABASE aegis_db;
CREATE USER aegis_user WITH PASSWORD 'new_password';
GRANT ALL PRIVILEGES ON DATABASE aegis_db TO aegis_user;
\q

# Start fresh installation
cd ~/Aegis
git pull origin main
# Follow installation steps from VM_SETUP_GUIDE.md

# On Agent VM (VM 2):
sudo systemctl stop aegis-agent
sudo rm -rf /opt/aegis-agent
sudo userdel aegis-agent
cd ~/Aegis/installers/agent-linux-deb
sudo bash install.sh
```

---

## 📞 Getting Help

### Collect Diagnostic Information

Before asking for help, collect this info:

```bash
# System info
uname -a
cat /etc/os-release

# Service status
sudo systemctl status aegis-server
sudo systemctl status aegis-agent
sudo systemctl status postgresql
sudo systemctl status nginx

# Recent logs
sudo journalctl -u aegis-server -n 200 > server-logs.txt
sudo journalctl -u aegis-agent -n 200 > agent-logs.txt

# Configuration (remove passwords!)
cat ~/Aegis/aegis-server/config.toml
cat /opt/aegis-agent/.env

# Network info
ip addr show
netstat -tulpn | grep -E '(8000|80|5432)'

# Database info
sudo -u postgres psql -d aegis_db -c "\dt"
sudo -u postgres psql -d aegis_db -c "SELECT COUNT(*) FROM devices;"
```

### Common Log Locations

```bash
# Server logs
sudo journalctl -u aegis-server -f
/var/log/aegis-server.log (if configured)

# Agent logs
sudo journalctl -u aegis-agent -f
/var/log/aegis-agent/agent.log

# PostgreSQL logs
sudo journalctl -u postgresql -f
/var/lib/postgres/data/log/

# Nginx logs
/var/log/nginx/access.log
/var/log/nginx/error.log
```

---

## ✅ Health Check Script

Create this script to quickly verify system health:

```bash
#!/bin/bash
# aegis-health-check.sh

echo "=== Aegis SIEM Health Check ==="
echo ""

echo "1. Service Status:"
systemctl is-active aegis-server && echo "  ✅ Server: Running" || echo "  ❌ Server: Stopped"
systemctl is-active aegis-agent && echo "  ✅ Agent: Running" || echo "  ❌ Agent: Stopped"
systemctl is-active postgresql && echo "  ✅ PostgreSQL: Running" || echo "  ❌ PostgreSQL: Stopped"
systemctl is-active nginx && echo "  ✅ Nginx: Running" || echo "  ❌ Nginx: Stopped"
echo ""

echo "2. API Health:"
curl -s http://localhost:8000/health | jq '.' && echo "  ✅ API: Healthy" || echo "  ❌ API: Failed"
echo ""

echo "3. Database:"
sudo -u postgres psql -d aegis_db -c "SELECT COUNT(*) FROM devices;" 2>/dev/null && echo "  ✅ Database: Connected" || echo "  ❌ Database: Failed"
echo ""

echo "4. Dashboard:"
curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep 200 && echo "  ✅ Dashboard: Accessible" || echo "  ❌ Dashboard: Failed"
echo ""

echo "=== Health Check Complete ==="
```

**Usage:**

```bash
chmod +x aegis-health-check.sh
./aegis-health-check.sh
```

---

**Still having issues? Check the detailed guides:**

- [VM Setup Guide](VM_SETUP_GUIDE.md)
- [Testing Checklist](VM_TESTING_CHECKLIST.md)
- [General Testing Guide](TESTING_GUIDE.md)

Or open an issue on GitHub: https://github.com/MokshitBindal/Aegis/issues
