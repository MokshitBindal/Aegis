# Aegis SIEM - VM Testing Quick Checklist

**Two-Machine Testing: Arch (Server+Agent) + Ubuntu (Agent)**

Use this checklist to track your testing progress. Print or keep open during testing.

---

## 🖥️ VM Setup

### VM 1: Arch Linux (Server + Agent)

**VM Creation**

- [ ] Download Arch Linux ISO
- [ ] Create VM (4GB RAM, 2 CPU, 30GB disk)
- [ ] Configure bridged network adapter
- [ ] Boot and install Arch Linux
- [ ] Set hostname: `aegis-server`
- [ ] Create user: `aegis`
- [ ] Enable SSH
- [ ] Note VM IP: `________________`

**System Prep**

- [ ] Update system: `sudo pacman -Syu`
- [ ] Install PostgreSQL: `sudo pacman -S postgresql`
- [ ] Install Python: `sudo pacman -S python python-pip`
- [ ] Install Node.js: `sudo pacman -S nodejs npm`
- [ ] Install Nginx: `sudo pacman -S nginx`
- [ ] Install Git: `sudo pacman -S git`
- [ ] Initialize PostgreSQL: `sudo -u postgres initdb`
- [ ] Start PostgreSQL: `sudo systemctl start postgresql`
- [ ] Clone repository: `git clone https://github.com/MokshitBindal/Aegis.git`

### VM 2: Ubuntu 22.04 (Agent Only)

**VM Creation**

- [ ] Download Ubuntu 22.04 LTS ISO
- [ ] Create VM (2GB RAM, 1 CPU, 15GB disk)
- [ ] Configure bridged network adapter (same network as VM1)
- [ ] Boot and install Ubuntu Server
- [ ] Set hostname: `aegis-agent`
- [ ] Create user: `aegis`
- [ ] Enable OpenSSH server during installation
- [ ] Note VM IP: `________________`

**System Prep**

- [ ] Update system: `sudo apt update && sudo apt upgrade -y`
- [ ] Install Git: `sudo apt install -y git`
- [ ] Clone repository: `git clone https://github.com/MokshitBindal/Aegis.git`

---

## 🔧 Server Installation (VM 1 - Arch)

### Database Setup

- [ ] Create PostgreSQL database: `aegis_db`
- [ ] Create PostgreSQL user: `aegis_user`
- [ ] Set database password (note it): `________________`
- [ ] Grant privileges to aegis_user

### Server Backend

- [ ] Navigate to: `~/Aegis/aegis-server`
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy config: `cp config.toml.example config.toml`
- [ ] Generate JWT secret: `openssl rand -hex 32`
- [ ] Edit config.toml with database credentials
- [ ] Initialize database: `python aegis-manage.py init-db`
- [ ] Create systemd service: `/etc/systemd/system/aegis-server.service`
- [ ] Enable service: `sudo systemctl enable aegis-server`
- [ ] Start service: `sudo systemctl start aegis-server`
- [ ] Verify service: `sudo systemctl status aegis-server`
- [ ] Test API: `curl http://localhost:8000/health`

### Dashboard Frontend

- [ ] Navigate to: `~/Aegis/aegis-dashboard`
- [ ] Install dependencies: `npm install`
- [ ] Build production: `npm run build`
- [ ] Verify dist folder: `ls -la dist/`

### Nginx Configuration

- [ ] Create Nginx config: `/etc/nginx/conf.d/aegis-dashboard.conf`
- [ ] Test config: `sudo nginx -t`
- [ ] Enable Nginx: `sudo systemctl enable nginx`
- [ ] Start Nginx: `sudo systemctl start nginx`
- [ ] Verify Nginx: `sudo systemctl status nginx`

### Admin User

- [ ] Create admin user: `python aegis-manage.py create-owner`
- [ ] Username: `________________`
- [ ] Password: `________________`
- [ ] Email: `________________`

### Verification

- [ ] Open browser: `http://<ARCH_VM_IP>`
- [ ] Dashboard loads successfully
- [ ] Login with admin credentials
- [ ] Dashboard displays correctly

---

## 🤖 Agent Installation

### VM 1 (Arch) - Local Agent

**Generate Token**

- [ ] Login to dashboard
- [ ] Navigate to Devices page
- [ ] Generate registration token
- [ ] Token: `________________________________`

**Install Agent**

- [ ] Navigate to: `~/Aegis/installers/agent-linux-arch`
- [ ] Run installer: `sudo bash install.sh`
- [ ] Server URL: `http://localhost:8000`
- [ ] Paste registration token
- [ ] Verify installation: `sudo systemctl status aegis-agent`
- [ ] Check logs: `sudo journalctl -u aegis-agent -f`
- [ ] Verify in dashboard: Device appears, Status: Online

### VM 2 (Ubuntu) - Remote Agent

**Generate New Token**

- [ ] SSH to VM 1: `ssh aegis@<ARCH_VM_IP>`
- [ ] Generate new token (via dashboard or CLI)
- [ ] Token: `________________________________`

**Install Agent**

- [ ] SSH to VM 2: `ssh aegis@<UBUNTU_VM_IP>`
- [ ] Navigate to: `~/Aegis/installers/agent-linux-deb`
- [ ] Run installer: `sudo bash install.sh`
- [ ] Server URL: `http://<ARCH_VM_IP>:8000`
- [ ] Paste registration token
- [ ] Verify installation: `sudo systemctl status aegis-agent`
- [ ] Check logs: `sudo journalctl -u aegis-agent -f`
- [ ] Test connectivity: `curl http://<ARCH_VM_IP>:8000/health`
- [ ] Verify in dashboard: Device appears, Status: Online

---

## ✅ Functionality Testing

### Data Collection (Both Agents)

**VM 1 (Arch):**

- [ ] Generate commands: `ls -la /etc && ps aux && df -h`
- [ ] Check commands appear in dashboard
- [ ] Verify metrics updating (CPU, Memory, Disk, Network)
- [ ] Check system logs appearing

**VM 2 (Ubuntu):**

- [ ] Generate commands: `cat /proc/cpuinfo && netstat -tulpn`
- [ ] Check commands appear in dashboard
- [ ] Verify metrics updating
- [ ] Check system logs appearing

### Alert Testing

**High CPU Alert:**

- [ ] On VM 2: `yes > /dev/null & yes > /dev/null &`
- [ ] Wait 2-3 minutes
- [ ] Check Alerts page - High CPU alert appears
- [ ] Kill processes: `killall yes`
- [ ] Alert details show correct device (Ubuntu)

**High Memory Alert (optional):**

- [ ] Install stress-ng: `sudo apt install stress-ng`
- [ ] Run: `stress-ng --vm 2 --vm-bytes 90% --timeout 120s`
- [ ] Check alert generation

### ML Anomaly Detection

**Baseline Period:**

- [ ] Wait 10-15 minutes for normal baseline
- [ ] Monitor both VMs' activity in dashboard

**Anomalous Activity (VM 2):**

- [ ] Install unusual package: `sudo apt install nmap`
- [ ] Run suspicious commands:
  ```bash
  sudo su -
  cat /etc/shadow
  nc -l 9999 &
  ```
- [ ] Wait 5-10 minutes
- [ ] Check for ML anomaly alerts
- [ ] Verify anomaly score shown
- [ ] Check feature contributions

### Real-Time Monitoring

**Live Dashboard Updates:**

- [ ] Open dashboard in browser
- [ ] Navigate to Devices page
- [ ] Click on VM 1 (Arch) device
- [ ] Generate activity on VM 1
- [ ] Observe metrics update in real-time (should update every 60s)
- [ ] Switch to VM 2 (Ubuntu) device
- [ ] Generate activity on VM 2
- [ ] Observe metrics update

**Command Logging:**

- [ ] Open Command Log page
- [ ] Run commands on both VMs simultaneously
- [ ] Verify commands appear with timestamps
- [ ] Check device names are correct
- [ ] Verify command details are accurate

---

## 🔍 System Health Checks

### Server Health (VM 1)

**Services Status:**

```bash
sudo systemctl status postgresql
sudo systemctl status aegis-server
sudo systemctl status nginx
```

- [ ] PostgreSQL: Active (running)
- [ ] aegis-server: Active (running)
- [ ] Nginx: Active (running)

**Logs Check:**

```bash
sudo journalctl -u aegis-server -n 50
```

- [ ] No critical errors
- [ ] Connection logs present
- [ ] API requests logged

**Database Check:**

```bash
sudo -u postgres psql -d aegis_db -c "SELECT COUNT(*) FROM devices;"
```

- [ ] Returns 2 (both devices)

**API Health:**

```bash
curl http://localhost:8000/health
```

- [ ] Returns: `{"status":"healthy",...}`

### Agent Health

**VM 1 Agent:**

```bash
sudo systemctl status aegis-agent
sudo journalctl -u aegis-agent -n 50
```

- [ ] Service active
- [ ] No connection errors
- [ ] Data submission logs present

**VM 2 Agent:**

```bash
sudo systemctl status aegis-agent
sudo journalctl -u aegis-agent -n 50
```

- [ ] Service active
- [ ] Connected to remote server
- [ ] Data submission logs present

---

## 📊 Performance Validation

### Resource Usage

**VM 1 (Arch):**

```bash
free -m    # Memory usage
top -bn1   # CPU usage
df -h      # Disk usage
```

- [ ] RAM usage: **\_\_** MB (expect: 1500-2500 MB)
- [ ] CPU usage: **\_\_** % (expect: 5-15% idle)
- [ ] Disk usage: **\_\_** GB (expect: < 5 GB)

**VM 2 (Ubuntu):**

```bash
free -m
top -bn1
df -h
```

- [ ] RAM usage: **\_\_** MB (expect: 200-400 MB)
- [ ] CPU usage: **\_\_** % (expect: 1-5% idle)
- [ ] Disk usage: **\_\_** MB (expect: < 500 MB)

### Network Performance

**Bandwidth Test:**

- [ ] On VM 2: `wget https://speed.hetzner.de/10MB.bin`
- [ ] Check dashboard network graph shows spike
- [ ] Verify bandwidth metrics accurate

**Latency Test:**

```bash
# From VM 2
ping -c 10 <ARCH_VM_IP>
```

- [ ] Average latency: **\_\_** ms (expect: < 5 ms local network)

---

## 🧪 Edge Case Testing

### Network Interruption

**Test:**

1. [ ] Note both devices online in dashboard
2. [ ] On VM 2: `sudo systemctl stop NetworkManager`
3. [ ] Wait 2-3 minutes
4. [ ] Check dashboard shows VM 2 as "Offline"
5. [ ] On VM 2: `sudo systemctl start NetworkManager`
6. [ ] Wait 1-2 minutes
7. [ ] Verify VM 2 reconnects automatically
8. [ ] Check no data loss (buffered data sent)

### Server Restart

**Test:**

1. [ ] Note both agents connected
2. [ ] On VM 1: `sudo systemctl restart aegis-server`
3. [ ] Wait for server to restart (30-60s)
4. [ ] Check both agents reconnect automatically
5. [ ] Verify data collection resumes

### Agent Restart

**Test:**

1. [ ] On VM 2: `sudo systemctl restart aegis-agent`
2. [ ] Check dashboard briefly shows offline
3. [ ] Verify agent comes back online
4. [ ] Check data collection continues

### High Load Scenario

**Test:**

1. [ ] On both VMs simultaneously:
   ```bash
   stress-ng --cpu 2 --timeout 300s
   ```
2. [ ] Monitor dashboard for 5 minutes
3. [ ] Check alerts generated for both devices
4. [ ] Verify system remains stable
5. [ ] Verify no missed data collection

---

## 🎯 Final Verification

### Dashboard Functionality

- [ ] All pages load without errors
- [ ] Devices page shows 2 devices
- [ ] Both devices show "Online" status
- [ ] Metrics graphs populated for both
- [ ] Alerts page shows test alerts
- [ ] Command log shows commands from both VMs
- [ ] Process monitoring displays current processes
- [ ] Log viewer shows system logs

### Data Accuracy

- [ ] Device hostnames correct (aegis-server, aegis-agent)
- [ ] IP addresses correct
- [ ] OS detection accurate (Arch Linux, Ubuntu 22.04)
- [ ] Metrics values reasonable
- [ ] Timestamps accurate

### Security

- [ ] Dashboard requires authentication
- [ ] API endpoints require auth token
- [ ] Agents use secure credentials
- [ ] No passwords in logs

---

## 📝 Issues Log

**Document any issues encountered:**

| Issue                        | VM  | Component | Severity | Resolution        | Time  |
| ---------------------------- | --- | --------- | -------- | ----------------- | ----- |
| Example: Service won't start | VM1 | Server    | High     | Fixed permissions | 10min |
|                              |     |           |          |                   |       |
|                              |     |           |          |                   |       |
|                              |     |           |          |                   |       |

---

## ✅ Sign-Off

**Testing completed by:** **********\_\_**********

**Date:** ******\_\_\_******

**Overall Result:**

- [ ] ✅ Production Ready - All tests passed
- [ ] ⚠️ Minor Issues - Needs small fixes
- [ ] ❌ Major Issues - Needs significant work

**Notes:**

```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

**Next Steps:**

1. ***
2. ***
3. ***

---

**Congratulations on completing the testing! 🎉**

For detailed troubleshooting, see `VM_SETUP_GUIDE.md`
