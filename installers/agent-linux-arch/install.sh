#!/bin/bash
#
# Aegis SIEM Agent Installation Script for Arch Linux
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

AEGIS_VERSION="1.0.0"
INSTALL_DIR="/opt/aegis-agent"
CONFIG_DIR="/etc/aegis-agent"
LOG_DIR="/var/log/aegis-agent"
AEGIS_USER="aegis-agent"
AEGIS_GROUP="aegis-agent"

SERVER_URL=""
REGISTRATION_TOKEN=""

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║   Aegis SIEM Agent Installation      ║"
echo "║          Arch Linux                  ║"
echo "║          Version $AEGIS_VERSION              ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   exit 1
fi

# Check if Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo -e "${RED}ERROR: This installer is for Arch Linux only${NC}"
    exit 1
fi

echo -e "${GREEN}✓ OS Check: Arch Linux${NC}"

# Configuration
echo ""
echo -e "${BLUE}=== Configuration ===${NC}"
echo ""

read -p "Aegis Server URL (e.g., http://192.168.1.100:8000): " SERVER_URL
while [ -z "$SERVER_URL" ]; do
    echo -e "${RED}Server URL is required${NC}"
    read -p "Aegis Server URL: " SERVER_URL
done

read -p "Registration Token: " REGISTRATION_TOKEN
while [ -z "$REGISTRATION_TOKEN" ]; then
    echo -e "${RED}Registration token is required${NC}"
    read -p "Registration Token: " REGISTRATION_TOKEN
done

echo ""
echo -e "${BLUE}=== Installation Summary ===${NC}"
echo "Server URL: $SERVER_URL"
echo "Token: ${REGISTRATION_TOKEN:0:8}..."
echo ""
read -p "Continue with installation? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    exit 0
fi

echo ""
echo -e "${BLUE}=== Starting Installation ===${NC}"
echo ""

# 1. Update system
echo -e "${YELLOW}[1/7] Updating system packages...${NC}"
pacman -Sy --noconfirm

# 2. Install dependencies
echo -e "${YELLOW}[2/7] Installing dependencies...${NC}"
pacman -S --needed --noconfirm \
    python \
    python-pip \
    python-virtualenv \
    systemd \
    curl

echo -e "${GREEN}✓ Dependencies installed${NC}"

# 3. Create user
echo -e "${YELLOW}[3/7] Creating service user...${NC}"
if ! id "$AEGIS_USER" &>/dev/null; then
    useradd -r -s /usr/bin/nologin -d "$INSTALL_DIR" -m "$AEGIS_USER"
    echo -e "${GREEN}✓ User created: $AEGIS_USER${NC}"
else
    echo -e "${YELLOW}User $AEGIS_USER already exists${NC}"
fi

# 4. Create directories
echo -e "${YELLOW}[4/7] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"
chown -R "$AEGIS_USER:$AEGIS_GROUP" "$INSTALL_DIR" "$LOG_DIR"
echo -e "${GREEN}✓ Directories created${NC}"

# 5. Install agent
echo -e "${YELLOW}[5/7] Installing agent...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd ../.. && pwd)"
cp -r "$SCRIPT_DIR/aegis-agent/"* "$INSTALL_DIR/" || {
    echo -e "${RED}ERROR: Cannot find agent files${NC}"
    exit 1
}

cd "$INSTALL_DIR"
sudo -u "$AEGIS_USER" python -m venv venv
sudo -u "$AEGIS_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip > /dev/null 2>&1
sudo -u "$AEGIS_USER" "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt > /dev/null 2>&1

echo -e "${GREEN}✓ Agent installed${NC}"

# 6. Register agent
echo -e "${YELLOW}[6/7] Registering agent with server...${NC}"

export AEGIS_SERVER_URL="$SERVER_URL"
cd "$INSTALL_DIR"
sudo -u "$AEGIS_USER" "$INSTALL_DIR/venv/bin/python" main.py register --token "$REGISTRATION_TOKEN" 2>&1 | tee /tmp/aegis-register.log

if grep -q "registered successfully" /tmp/aegis-register.log; then
    echo -e "${GREEN}✓ Agent registered${NC}"
else
    echo -e "${RED}ERROR: Registration failed. Check server URL and token.${NC}"
    cat /tmp/aegis-register.log
    exit 1
fi

# 7. Configure service
echo -e "${YELLOW}[7/7] Configuring systemd service...${NC}"

cat > /etc/systemd/system/aegis-agent.service <<EOF
[Unit]
Description=Aegis SIEM Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$AEGIS_USER
Group=$AEGIS_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="AEGIS_SERVER_URL=$SERVER_URL"
ExecStart=$INSTALL_DIR/venv/bin/python main.py run
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/agent.log
StandardError=append:$LOG_DIR/agent-error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aegis-agent
systemctl start aegis-agent

echo -e "${GREEN}✓ Service configured and started${NC}"

# Save info
cat > "$CONFIG_DIR/install-info.txt" <<EOF
Aegis SIEM Agent Installation
=============================

Server URL: $SERVER_URL
Installed: $(date)
Installation Directory: $INSTALL_DIR

Service Management:
  Status: systemctl status aegis-agent
  Stop:   systemctl stop aegis-agent
  Start:  systemctl start aegis-agent
  Logs:   journalctl -u aegis-agent -f

Logs: $LOG_DIR/agent.log
EOF

chmod 600 "$CONFIG_DIR/install-info.txt"

echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════╗"
echo "║   Installation Complete! ✓            ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Agent Status:${NC}"
systemctl status aegis-agent --no-pager | head -10
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:      journalctl -u aegis-agent -f"
echo "  Check status:   systemctl status aegis-agent"
echo "  Restart agent:  systemctl restart aegis-agent"
echo ""
echo -e "${GREEN}Agent is now monitoring this system!${NC}"
echo ""
