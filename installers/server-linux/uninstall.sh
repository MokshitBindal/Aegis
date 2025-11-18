#!/bin/bash
#
# Aegis SIEM Server Uninstallation Script
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}"
echo "╔═══════════════════════════════════════╗"
echo "║   Aegis SIEM Server Uninstallation   ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   exit 1
fi

echo -e "${YELLOW}This will remove:${NC}"
echo "  - Aegis SIEM server and dashboard"
echo "  - System services"
echo "  - Configuration files"
echo ""
read -p "Keep database and data? (Y/n): " keep_data
read -p "Continue with uninstallation? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting uninstallation...${NC}"
echo ""

# Stop services
echo -e "${YELLOW}[1/5] Stopping services...${NC}"
systemctl stop aegis-server 2>/dev/null || true
systemctl disable aegis-server 2>/dev/null || true

# Remove Nginx config
echo -e "${YELLOW}[2/5] Removing Nginx configuration...${NC}"
rm -f /etc/nginx/sites-enabled/aegis-dashboard
rm -f /etc/nginx/sites-available/aegis-dashboard
systemctl reload nginx 2>/dev/null || true

# Remove systemd service
echo -e "${YELLOW}[3/5] Removing systemd service...${NC}"
rm -f /etc/systemd/system/aegis-server.service
systemctl daemon-reload

# Remove files
echo -e "${YELLOW}[4/5] Removing installation files...${NC}"
rm -rf /opt/aegis-siem
rm -rf /etc/aegis-siem
rm -rf /var/log/aegis-siem

if [[ ! "$keep_data" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Removing database and data...${NC}"
    rm -rf /var/lib/aegis-siem
    
    # Optionally remove PostgreSQL database
    read -p "Remove PostgreSQL database? (y/N): " remove_db
    if [[ "$remove_db" =~ ^[Yy]$ ]]; then
        read -p "Database name [aegis_siem]: " db_name
        db_name=${db_name:-aegis_siem}
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS $db_name;" 2>/dev/null || true
        sudo -u postgres psql -c "DROP USER IF EXISTS aegis_user;" 2>/dev/null || true
        echo -e "${GREEN}✓ Database removed${NC}"
    fi
fi

# Remove user
echo -e "${YELLOW}[5/5] Removing service user...${NC}"
userdel -r aegis 2>/dev/null || true

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Uninstallation Complete! ✓         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""

if [[ "$keep_data" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Note: Data preserved in /var/lib/aegis-siem${NC}"
fi
