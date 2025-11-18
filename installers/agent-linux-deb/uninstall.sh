#!/bin/bash
#
# Aegis SIEM Agent Uninstallation Script
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}"
echo "╔═══════════════════════════════════════╗"
echo "║   Aegis SIEM Agent Uninstallation    ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   exit 1
fi

read -p "Remove Aegis SIEM Agent? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] Stopping service...${NC}"
systemctl stop aegis-agent 2>/dev/null || true
systemctl disable aegis-agent 2>/dev/null || true

echo -e "${YELLOW}[2/4] Removing service...${NC}"
rm -f /etc/systemd/system/aegis-agent.service
systemctl daemon-reload

echo -e "${YELLOW}[3/4] Removing files...${NC}"
rm -rf /opt/aegis-agent
rm -rf /etc/aegis-agent
rm -rf /var/log/aegis-agent

echo -e "${YELLOW}[4/4] Removing user...${NC}"
userdel -r aegis-agent 2>/dev/null || true

echo ""
echo -e "${GREEN}✓ Agent uninstalled successfully${NC}"
echo ""
