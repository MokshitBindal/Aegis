# Aegis SIEM - VM Testing Setup Guide

**Two-Machine Testing Environment**

This guide provides step-by-step instructions for setting up a complete Aegis SIEM test environment with:

- **VM 1 (Arch Linux):** Server + Dashboard + Agent
- **VM 2 (Ubuntu):** Agent only

---

## 📋 Overview

### Testing Architecture

```
┌─────────────────────────────────────────┐
│         VM 1 (Arch Linux)               │
│  ┌──────────────────────────────────┐   │
│  │     Aegis Server + Dashboard     │   │
│  │  - PostgreSQL Database           │   │
│  │  - FastAPI Backend (Port 8000)   │   │
│  │  - React Frontend (Port 80)      │   │
│  │  - Nginx Reverse Proxy           │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │     Aegis Agent (Local)          │   │
│  │  - Monitors VM 1 itself          │   │
│  └──────────────────────────────────┘   │
│  IP: 192.168.x.x (Your network)         │
└─────────────────────────────────────────┘
                   ▲
                   │ HTTPS API
                   │
┌─────────────────────────────────────────┐
│         VM 2 (Ubuntu)                   │
│  ┌──────────────────────────────────┐   │
│  │     Aegis Agent                  │   │
│  │  - Monitors VM 2                 │   │
│  │  - Reports to VM 1 Server        │   │
│  └──────────────────────────────────┘   │
│  IP: 192.168.x.y (Same network)         │
└─────────────────────────────────────────┘
```

### Why This Setup?

- **Real-world scenario:** Server monitors itself + external devices
- **Multi-platform testing:** Tests Arch and Ubuntu support
- **Minimal resources:** Only 2 VMs needed
- **Full feature test:** All components in action

---

## 🖥️ VM Requirements

### VM 1: Arch Linux (Server + Agent)

| Component    | Specification                                |
| ------------ | -------------------------------------------- |
| **OS**       | Arch Linux (latest)                          |
| **RAM**      | 4GB (2GB minimum)                            |
| **CPU**      | 2 cores                                      |
| **Disk**     | 30GB                                         |
| **Network**  | Bridged Adapter                              |
| **Services** | PostgreSQL, Nginx, Aegis Server, Aegis Agent |

**Why Arch for Server?**

- Tests installation on Arch (bleeding edge)
- Pacman package manager testing
- Systemd integration validation
- Rolling release compatibility

### VM 2: Ubuntu 22.04 LTS (Agent Only)

| Component    | Specification                         |
| ------------ | ------------------------------------- |
| **OS**       | Ubuntu 22.04 LTS                      |
| **RAM**      | 2GB (1GB minimum)                     |
| **CPU**      | 1 core                                |
| **Disk**     | 15GB                                  |
| **Network**  | Bridged Adapter (same network as VM1) |
| **Services** | Aegis Agent only                      |

**Why Ubuntu for Agent?**

- Most popular Linux distribution
- Stable LTS release
- Representative of enterprise deployments
- Debian package testing

---

## 🚀 Step-by-Step Setup

## Phase 1: Prepare VM 1 (Arch Linux)

### 1.1 Create Arch Linux VM

**Using VirtualBox:**

```bash
# Download Arch Linux ISO
wget https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso

# Create VM
VBoxManage createvm --name "Aegis-Arch-Server" --ostype "ArchLinux_64" --register
VBoxManage modifyvm "Aegis-Arch-Server" --memory 4096 --cpus 2 --nic1 bridged --bridgeadapter1 eth0
VBoxManage createhd --filename "Aegis-Arch-Server.vdi" --size 30720

# Add storage controller
VBoxManage storagectl "Aegis-Arch-Server" --name "SATA" --add sata --controller IntelAHCI

# Attach disks
VBoxManage storageattach "Aegis-Arch-Server" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "Aegis-Arch-Server.vdi"
VBoxManage storageattach "Aegis-Arch-Server" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium archlinux-x86_64.iso

# Start VM
VBoxManage startvm "Aegis-Arch-Server"
```

**Using VMware/KVM:** Adjust commands accordingly or use GUI.

### 1.2 Install Arch Linux

**Boot into Arch ISO and run:**

```bash
# Check network connectivity
ping -c 3 google.com

# Option 1: Quick install using archinstall
archinstall
```

**archinstall Configuration:**

- **Language:** English
- **Mirrors:** Select your region
- **Locale:** en_US.UTF-8
- **Disk layout:** Use entire disk
- **Filesystem:** ext4
- **Hostname:** aegis-server
- **Root password:** Set a secure password
- **User account:** Create user (e.g., `aegis`)
- **Profile:** Minimal (no desktop)
- **Audio:** None
- **Kernels:** linux
- **Network:** NetworkManager
- **Additional packages:** `git openssh sudo base-devel`
- **Enable services:** NetworkManager, sshd

**Option 2: Manual Installation (if you prefer)**

```bash
# Partition disk
cfdisk /dev/sda
# Create: 512M EFI, remaining Linux filesystem

# Format partitions
mkfs.fat -F32 /dev/sda1
mkfs.ext4 /dev/sda2

# Mount
mount /dev/sda2 /mnt
mkdir /mnt/boot
mount /dev/sda1 /mnt/boot

# Install base system
pacstrap /mnt base linux linux-firmware networkmanager sudo git openssh base-devel vim

# Generate fstab
genfstab -U /mnt >> /mnt/etc/fstab

# Chroot
arch-chroot /mnt

# Set timezone
ln -sf /usr/share/zoneinfo/Region/City /etc/localtime
hwclock --systohc

# Locale
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# Hostname
echo "aegis-server" > /etc/hostname

# Root password
passwd

# Create user
useradd -m -G wheel -s /bin/bash aegis
passwd aegis

# Enable sudo for wheel group
EDITOR=vim visudo
# Uncomment: %wheel ALL=(ALL:ALL) ALL

# Enable services
systemctl enable NetworkManager
systemctl enable sshd

# Install bootloader
bootctl install
echo "default arch" > /boot/loader/loader.conf
cat > /boot/loader/entries/arch.conf << EOF
title   Arch Linux
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=/dev/sda2 rw
EOF

# Exit and reboot
exit
umount -R /mnt
reboot
```

### 1.3 Post-Installation Setup (Arch)

**SSH into the VM:**

```bash
# Find VM IP
ip addr show

# From host machine
ssh aegis@<ARCH_VM_IP>
```

**Update system:**

```bash
sudo pacman -Syu
```

**Install dependencies for Aegis Server:**

```bash
# Install PostgreSQL
sudo pacman -S postgresql python python-pip nodejs npm nginx

# Initialize PostgreSQL
sudo -u postgres initdb -D /var/lib/postgres/data

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify services
sudo systemctl status postgresql
sudo systemctl status nginx
```

**Clone Aegis repository:**

```bash
cd ~
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis
```

---

## Phase 2: Install Aegis Server on VM 1

### 2.1 Manual Server Installation (Arch)

Since we don't have a dedicated Arch server installer yet, we'll install manually:

```bash
cd ~/Aegis

# Install server dependencies
cd aegis-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 2.2 Setup PostgreSQL Database

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE aegis_db;
CREATE USER aegis_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE aegis_db TO aegis_user;
\q
EOF
```

### 2.3 Configure Server

```bash
cd ~/Aegis/aegis-server

# Copy config template
cp config.toml.example config.toml

# Edit configuration
nano config.toml
```

**Update config.toml:**

```toml
[database]
user = "aegis_user"
password = "your_secure_password_here"
database = "aegis_db"
host = "localhost"

[jwt]
secret_key = "generate_with_openssl_rand_hex_32"
algorithm = "HS256"
access_token_expire_minutes = 60
```

**Generate JWT secret:**

```bash
openssl rand -hex 32
# Copy output and paste into config.toml
```

### 2.4 Initialize Database

```bash
cd ~/Aegis/aegis-server
source venv/bin/activate
python aegis-manage.py init-db
```

### 2.5 Build Dashboard

```bash
cd ~/Aegis/aegis-dashboard

# Install dependencies
npm install

# Build for production
npm run build
```

### 2.6 Create Systemd Service for Server

```bash
sudo nano /etc/systemd/system/aegis-server.service
```

**Add this content:**

```ini
[Unit]
Description=Aegis SIEM Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=aegis
Group=aegis
WorkingDirectory=/home/aegis/Aegis/aegis-server
Environment="PATH=/home/aegis/Aegis/aegis-server/venv/bin"
ExecStart=/home/aegis/Aegis/aegis-server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable aegis-server
sudo systemctl start aegis-server
sudo systemctl status aegis-server
```

### 2.7 Configure Nginx for Dashboard

```bash
sudo nano /etc/nginx/sites-available/aegis-dashboard
```

**Add this content (create sites-available/sites-enabled if they don't exist):**

```nginx
server {
    listen 80;
    server_name _;

    # Dashboard
    location / {
        root /home/aegis/Aegis/aegis-dashboard/dist;
        try_files $uri $uri/ /index.html;
    }

    # API Proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Create sites-enabled directory if needed:**

```bash
# Check if sites-available/sites-enabled exist
ls /etc/nginx/sites-available

# If not, modify main nginx.conf
sudo nano /etc/nginx/nginx.conf
# Add inside http block: include /etc/nginx/conf.d/*.conf;

# Create config in conf.d
sudo cp /etc/nginx/sites-available/aegis-dashboard /etc/nginx/conf.d/aegis-dashboard.conf
```

**Enable and restart Nginx:**

```bash
# If using sites-available/sites-enabled
sudo ln -s /etc/nginx/sites-available/aegis-dashboard /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 2.8 Create Admin User

```bash
cd ~/Aegis/aegis-server
source venv/bin/activate

# Create admin using management script
python aegis-manage.py create-owner \
    --username admin \
    --email admin@aegis.local \
    --full-name "Admin User"

# You'll be prompted for password
```

**Or use Python directly:**

```bash
python << EOF
import asyncio
from internal.auth.password import hash_password
from internal.storage.database import init_pool, close_pool
from internal.storage.database import execute_query

async def create_admin():
    await init_pool()

    hashed = hash_password("your_secure_password")

    await execute_query("""
        INSERT INTO users (username, email, full_name, password_hash, role)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (username) DO NOTHING
    """, "admin", "admin@aegis.local", "Admin User", hashed, "owner")

    print("Admin user created!")
    await close_pool()

asyncio.run(create_admin())
EOF
```

### 2.9 Test Server Installation

```bash
# Test API health
curl http://localhost:8000/health

# Should return: {"status":"healthy",...}

# Get VM IP
ip addr show | grep inet

# From host machine browser
# Navigate to: http://<ARCH_VM_IP>
```

**You should see the Aegis SIEM dashboard login page!**

---

## Phase 3: Install Aegis Agent on VM 1 (Arch)

Now we'll install the agent on the same Arch VM to monitor the server itself.

### 3.1 Install Agent on Arch

```bash
cd ~/Aegis/installers/agent-linux-arch
sudo bash install.sh
```

**Provide configuration:**

- **Server URL:** `http://localhost:8000` (since agent is on same machine)
- **Registration Token:** (generate from dashboard - see below)

### 3.2 Generate Registration Token

**Option 1: Via Dashboard**

1. Login to dashboard: `http://<ARCH_VM_IP>`
2. Go to "Devices" page
3. Click "Add Device" or "Generate Token"
4. Copy the token

**Option 2: Via CLI**

```bash
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
        INSERT INTO device_tokens (token, created_by)
        VALUES ($1, (SELECT id FROM users WHERE username='admin'))
    """, token)
    print(f"Token: {token}")

asyncio.run(gen_token())
EOF
```

### 3.3 Verify Agent Installation

```bash
# Check service
sudo systemctl status aegis-agent

# View logs
sudo journalctl -u aegis-agent -f

# Should see: "Agent registered successfully" or "Connected to server"
```

---

## Phase 4: Prepare VM 2 (Ubuntu)

### 4.1 Create Ubuntu VM

```bash
# Download Ubuntu 22.04 LTS
wget https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso

# Create VM in VirtualBox
VBoxManage createvm --name "Aegis-Ubuntu-Agent" --ostype "Ubuntu_64" --register
VBoxManage modifyvm "Aegis-Ubuntu-Agent" --memory 2048 --cpus 1 --nic1 bridged --bridgeadapter1 eth0
VBoxManage createhd --filename "Aegis-Ubuntu-Agent.vdi" --size 15360

# Add storage
VBoxManage storagectl "Aegis-Ubuntu-Agent" --name "SATA" --add sata --controller IntelAHCI
VBoxManage storageattach "Aegis-Ubuntu-Agent" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "Aegis-Ubuntu-Agent.vdi"
VBoxManage storageattach "Aegis-Ubuntu-Agent" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium ubuntu-22.04.3-live-server-amd64.iso

# Start VM
VBoxManage startvm "Aegis-Ubuntu-Agent"
```

### 4.2 Install Ubuntu

**Follow Ubuntu installer:**

1. Language: English
2. Update installer: Skip or update
3. Keyboard: English (US)
4. Network: Use DHCP (should auto-configure)
5. Proxy: Leave empty
6. Mirror: Use default
7. Storage: Use entire disk
8. Profile setup:
   - Name: Aegis Agent
   - Server name: aegis-agent
   - Username: aegis
   - Password: Set secure password
9. SSH: Install OpenSSH server ✓
10. Featured snaps: None needed
11. Install and reboot

### 4.3 Post-Installation (Ubuntu)

**SSH into Ubuntu VM:**

```bash
# Find IP
ip addr show

# From host
ssh aegis@<UBUNTU_VM_IP>
```

**Update system:**

```bash
sudo apt update && sudo apt upgrade -y
```

**Install git:**

```bash
sudo apt install -y git
```

**Clone repository:**

```bash
cd ~
git clone https://github.com/MokshitBindal/Aegis.git
```

---

## Phase 5: Install Aegis Agent on VM 2 (Ubuntu)

### 5.1 Run Agent Installer

```bash
cd ~/Aegis/installers/agent-linux-deb
sudo bash install.sh
```

**Configuration prompts:**

- **Server URL:** `http://<ARCH_VM_IP>:8000` (IP of VM 1)
- **Registration Token:** (generate new token from dashboard)

### 5.2 Generate New Registration Token

**On VM 1 (Arch) - via dashboard or CLI:**

```bash
# SSH to VM 1
ssh aegis@<ARCH_VM_IP>

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
        INSERT INTO device_tokens (token, created_by)
        VALUES ($1, (SELECT id FROM users WHERE username='admin'))
    """, token)
    print(f"Token: {token}")

asyncio.run(gen_token())
EOF
```

Copy the token and paste it during Ubuntu agent installation.

### 5.3 Verify Ubuntu Agent

```bash
# Check service
sudo systemctl status aegis-agent

# View logs
sudo journalctl -u aegis-agent -f

# Test connectivity to server
curl http://<ARCH_VM_IP>:8000/health
```

---

## Phase 6: Verification and Testing

### 6.1 Verify Both Agents in Dashboard

1. **Open dashboard:** `http://<ARCH_VM_IP>`
2. **Login** with admin credentials
3. **Go to Devices page**

**You should see:**

- **Device 1:** aegis-server (Arch Linux) - Status: Online
- **Device 2:** aegis-agent (Ubuntu 22.04) - Status: Online

### 6.2 Test Data Collection

**Generate activity on both VMs:**

**On VM 1 (Arch):**

```bash
# Generate commands
ls -la /etc
ps aux | grep python
df -h
free -m

# Generate CPU load
yes > /dev/null &
sleep 30
killall yes
```

**On VM 2 (Ubuntu):**

```bash
# Generate commands
cat /proc/cpuinfo
netstat -tulpn
sudo dmesg | tail

# Download something
wget https://speed.hetzner.de/10MB.bin
```

**Check dashboard after 1-2 minutes:**

- **Metrics:** CPU, Memory, Disk, Network graphs populated for both devices
- **Logs:** System logs from both VMs
- **Commands:** Recent commands listed for each device
- **Processes:** Running processes shown

### 6.3 Test Alert Generation

**On VM 2 (Ubuntu) - Stress test:**

```bash
# Install stress tool
sudo apt install -y stress-ng

# CPU stress
stress-ng --cpu 4 --timeout 120s
```

**Check dashboard:**

- Go to **Alerts** page
- Should see high CPU alert for Ubuntu agent
- Alert should show device name, timestamp, severity

### 6.4 Test ML Anomaly Detection

1. **Wait 10-15 minutes** for baseline establishment
2. **Perform anomalous activity:**

```bash
# On VM 2 (Ubuntu)
# Install unusual package
sudo apt install -y nmap

# Run suspicious commands
sudo su -
cat /etc/shadow
nc -l 9999 &
```

3. **Check dashboard** (ML alerts may take 5-10 minutes)
4. Look for anomaly alerts with scores

---

## 🎯 Success Criteria Checklist

### Server (VM 1 - Arch)

- [ ] PostgreSQL running and accessible
- [ ] Aegis server service active
- [ ] Nginx serving dashboard on port 80
- [ ] Dashboard accessible from host browser
- [ ] API health check returns 200 OK
- [ ] Admin user can login
- [ ] No errors in server logs

### Agent on VM 1 (Arch)

- [ ] Agent service running
- [ ] Registered with local server
- [ ] Appears in dashboard devices list
- [ ] Status shows "Online"
- [ ] Metrics being collected
- [ ] Commands logged

### Agent on VM 2 (Ubuntu)

- [ ] Agent service running
- [ ] Registered with VM 1 server
- [ ] Appears in dashboard devices list
- [ ] Status shows "Online"
- [ ] Metrics being collected
- [ ] Commands logged
- [ ] Can communicate with server over network

### Overall System

- [ ] Both devices monitored simultaneously
- [ ] Real-time metrics updates
- [ ] Log streaming working
- [ ] Alerts generated appropriately
- [ ] ML detection active
- [ ] No connectivity issues
- [ ] Dashboard responsive

---

## 🐛 Troubleshooting

### Server Won't Start (Arch)

```bash
# Check logs
sudo journalctl -u aegis-server -n 100

# Common issues:
# 1. Database connection failed
sudo systemctl status postgresql
sudo -u postgres psql -l

# 2. Port already in use
sudo netstat -tulpn | grep 8000

# 3. Permission issues
ls -la ~/Aegis/aegis-server
```

### Dashboard Shows 404

```bash
# Check if build exists
ls -la ~/Aegis/aegis-dashboard/dist/

# Rebuild
cd ~/Aegis/aegis-dashboard
npm run build

# Check Nginx config
sudo nginx -t
sudo systemctl restart nginx
```

### Agent Can't Connect to Server

**On Ubuntu VM:**

```bash
# Test network connectivity
ping <ARCH_VM_IP>

# Test API endpoint
curl http://<ARCH_VM_IP>:8000/health

# Check firewall (if any)
sudo ufw status

# Check agent config
sudo cat /opt/aegis-agent/.env

# View agent logs
sudo journalctl -u aegis-agent -n 50
```

### Agents Not Appearing in Dashboard

```bash
# Check registration tokens are valid
# Generate new token and re-register

# On agent VM
cd /opt/aegis-agent
sudo systemctl stop aegis-agent
sudo -u aegis-agent ./venv/bin/python main.py register --token NEW_TOKEN
sudo systemctl start aegis-agent
```

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL is accepting connections
sudo nano /var/lib/postgres/data/postgresql.conf
# Ensure: listen_addresses = 'localhost'

sudo nano /var/lib/postgres/data/pg_hba.conf
# Add: host aegis_db aegis_user 127.0.0.1/32 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 📊 Performance Monitoring

### Expected Resource Usage

**VM 1 (Arch - Server + Agent):**

- **RAM:** 1.5-2.5 GB used
- **CPU:** 5-15% idle, spikes during queries
- **Disk:** < 5 GB used
- **Network:** Minimal (< 100 KB/s)

**VM 2 (Ubuntu - Agent Only):**

- **RAM:** 200-400 MB used
- **CPU:** 1-5% idle
- **Disk:** < 500 MB used
- **Network:** Minimal (< 50 KB/s)

### Monitor Performance

```bash
# On each VM
htop

# Check disk usage
df -h

# Check network
iftop

# Monitor services
sudo systemctl status aegis-server
sudo systemctl status aegis-agent
```

---

## 🎬 Next Steps After Successful Testing

1. **Document findings** - Note any issues or improvements
2. **Create demo video** - Screen record the working system
3. **Test edge cases:**

   - Network disconnection
   - Server restart
   - Agent restart
   - High load scenarios
   - Multiple simultaneous alerts

4. **Performance tuning:**

   - Optimize collection intervals
   - Tune PostgreSQL settings
   - Adjust alert thresholds

5. **Security hardening:**

   - Enable HTTPS
   - Configure firewall
   - Set up proper authentication

6. **Prepare for production:**
   - Backup procedures
   - Monitoring and logging
   - Update documentation

---

## 📝 Testing Report Template

```markdown
# Aegis SIEM VM Testing Report

**Date:** 2025-11-19
**Environment:** VirtualBox / VMware / KVM

## VM 1: Arch Linux (Server + Agent)

- **Installation Time:** \_\_\_ minutes
- **Server Status:** ✅ Running / ❌ Failed
- **Agent Status:** ✅ Running / ❌ Failed
- **Dashboard Accessible:** ✅ Yes / ❌ No
- **Issues:** None / List issues

### Performance

- RAM Usage: \_\_\_GB
- CPU Usage: \_\_\_%
- Disk Usage: \_\_\_GB

## VM 2: Ubuntu (Agent Only)

- **Installation Time:** \_\_\_ minutes
- **Agent Status:** ✅ Running / ❌ Failed
- **Connected to Server:** ✅ Yes / ❌ No
- **Data Appearing:** ✅ Yes / ❌ No
- **Issues:** None / List issues

### Performance

- RAM Usage: \_\_\_MB
- CPU Usage: \_\_\_%

## Functionality Tests

- [ ] Both agents visible in dashboard
- [ ] Real-time metrics collection
- [ ] Log streaming
- [ ] Command logging
- [ ] Process monitoring
- [ ] Alert generation
- [ ] ML anomaly detection
- [ ] Network monitoring

## Issues Found

1.
2.

## Recommendations

1.
2.

## Overall Assessment

✅ Production Ready / ⚠️ Needs Minor Fixes / ❌ Major Issues

**Signature:** ******\_******
```

---

## 🚀 Quick Start Commands Summary

### VM 1 (Arch) - Full Setup

```bash
# After Arch installation
sudo pacman -Syu
sudo pacman -S postgresql python python-pip nodejs npm nginx git
sudo -u postgres initdb -D /var/lib/postgres/data
sudo systemctl start postgresql
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis

# Follow manual installation steps from Phase 2
```

### VM 2 (Ubuntu) - Agent Only

```bash
# After Ubuntu installation
sudo apt update && sudo apt upgrade -y
sudo apt install -y git
git clone https://github.com/MokshitBindal/Aegis.git
cd Aegis/installers/agent-linux-deb
sudo bash install.sh
```

---

**Ready to start testing? Let's secure your infrastructure! 🛡️**
