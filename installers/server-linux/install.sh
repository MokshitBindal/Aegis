#!/bin/bash
#
# Aegis SIEM Server Installation Script
# Installs: PostgreSQL, Backend Server, Frontend Dashboard
# Supports: Debian 11+, Ubuntu 20.04+
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Version
AEGIS_VERSION="1.0.0"

# Installation directories
INSTALL_DIR="/opt/aegis-siem"
SERVER_DIR="$INSTALL_DIR/server"
DASHBOARD_DIR="$INSTALL_DIR/dashboard"
CONFIG_DIR="/etc/aegis-siem"
LOG_DIR="/var/log/aegis-siem"
DATA_DIR="/var/lib/aegis-siem"

# Service user
AEGIS_USER="aegis"
AEGIS_GROUP="aegis"

# Default values
DB_NAME="aegis_siem"
DB_USER="aegis_user"
DB_PASSWORD=""
JWT_SECRET=""
SERVER_PORT="8000"
DASHBOARD_PORT="80"
DOMAIN=""

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║   Aegis SIEM Server Installation     ║"
echo "║          Version $AEGIS_VERSION              ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   echo "Please run: sudo $0"
   exit 1
fi

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}ERROR: Cannot determine OS${NC}"
    exit 1
fi

if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
    echo -e "${RED}ERROR: This installer supports Debian/Ubuntu only${NC}"
    echo "Detected: $OS"
    exit 1
fi

echo -e "${GREEN}✓ OS Check: $OS $VER${NC}"

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to prompt user input
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        eval $var_name="${input:-$default}"
    else
        while true; do
            read -p "$prompt: " input
            if [ -n "$input" ]; then
                eval $var_name="$input"
                break
            else
                echo -e "${RED}This field is required${NC}"
            fi
        done
    fi
}

# Interactive configuration
echo ""
echo -e "${BLUE}=== Configuration ===${NC}"
echo ""

prompt_input "Database Name" "$DB_NAME" "DB_NAME"
prompt_input "Database User" "$DB_USER" "DB_USER"

# Generate or ask for password
read -p "Generate secure database password? (Y/n): " generate_db_pass
if [[ "$generate_db_pass" =~ ^[Nn]$ ]]; then
    read -s -p "Enter database password: " DB_PASSWORD
    echo ""
else
    DB_PASSWORD=$(generate_password)
    echo -e "${GREEN}Generated database password${NC}"
fi

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)
echo -e "${GREEN}Generated JWT secret${NC}"

prompt_input "Server API Port" "$SERVER_PORT" "SERVER_PORT"
prompt_input "Dashboard Port" "$DASHBOARD_PORT" "DASHBOARD_PORT"
prompt_input "Domain (leave empty for IP)" "" "DOMAIN"

echo ""
echo -e "${BLUE}=== Installation Summary ===${NC}"
echo "Database: $DB_NAME"
echo "DB User: $DB_USER"
echo "Server Port: $SERVER_PORT"
echo "Dashboard Port: $DASHBOARD_PORT"
echo "Domain: ${DOMAIN:-Not set (will use IP)}"
echo ""
read -p "Continue with installation? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Installation cancelled"
    exit 0
fi

# Start installation
echo ""
echo -e "${BLUE}=== Starting Installation ===${NC}"
echo ""

# 1. Update system
echo -e "${YELLOW}[1/10] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# 2. Install dependencies
echo -e "${YELLOW}[2/10] Installing dependencies...${NC}"
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    curl \
    git \
    supervisor \
    gnupg \
    ca-certificates

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
apt-get install -y -qq nodejs

echo -e "${GREEN}✓ Dependencies installed${NC}"

# 3. Create user
echo -e "${YELLOW}[3/10] Creating service user...${NC}"
if ! id "$AEGIS_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$AEGIS_USER"
    echo -e "${GREEN}✓ User created: $AEGIS_USER${NC}"
else
    echo -e "${YELLOW}User $AEGIS_USER already exists${NC}"
fi

# 4. Create directories
echo -e "${YELLOW}[4/10] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR" "$SERVER_DIR" "$DASHBOARD_DIR" "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR"
mkdir -p "$SERVER_DIR/models" "$SERVER_DIR/ml_data"
chown -R "$AEGIS_USER:$AEGIS_GROUP" "$INSTALL_DIR" "$LOG_DIR" "$DATA_DIR"
chmod 750 "$CONFIG_DIR"
echo -e "${GREEN}✓ Directories created${NC}"

# 5. Setup PostgreSQL
echo -e "${YELLOW}[5/10] Configuring PostgreSQL...${NC}"
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" > /dev/null 2>&1 || true
sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" > /dev/null 2>&1 || true
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo -e "${GREEN}✓ PostgreSQL configured${NC}"

# 6. Install Backend Server
echo -e "${YELLOW}[6/10] Installing backend server...${NC}"

# Copy server files (assuming script is run from repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd ../.. && pwd)"
cp -r "$SCRIPT_DIR/aegis-server/"* "$SERVER_DIR/" || {
    echo -e "${RED}ERROR: Cannot find server files. Run this script from the repository root.${NC}"
    exit 1
}

# Create Python virtual environment
cd "$SERVER_DIR"
sudo -u "$AEGIS_USER" python3 -m venv venv
sudo -u "$AEGIS_USER" "$SERVER_DIR/venv/bin/pip" install --upgrade pip > /dev/null 2>&1
sudo -u "$AEGIS_USER" "$SERVER_DIR/venv/bin/pip" install -r requirements.txt > /dev/null 2>&1

# Create config file
cat > "$CONFIG_DIR/server.conf" <<EOF
[database]
user = "$DB_USER"
password = "$DB_PASSWORD"
database = "$DB_NAME"
host = "localhost"
port = 5432

[jwt]
secret_key = "$JWT_SECRET"
algorithm = "HS256"
access_token_expire_minutes = 60

[server]
host = "0.0.0.0"
port = $SERVER_PORT
workers = 4
EOF

ln -sf "$CONFIG_DIR/server.conf" "$SERVER_DIR/config.toml"
chown root:$AEGIS_GROUP "$CONFIG_DIR/server.conf"
chmod 640 "$CONFIG_DIR/server.conf"

echo -e "${GREEN}✓ Backend server installed${NC}"

# 7. Install Dashboard
echo -e "${YELLOW}[7/10] Installing dashboard...${NC}"

cp -r "$SCRIPT_DIR/aegis-dashboard/"* "$DASHBOARD_DIR/"

# Create production .env file
cat > "$DASHBOARD_DIR/.env.production" <<EOF
VITE_API_URL=http://localhost:$SERVER_PORT/api
EOF

# Build dashboard
cd "$DASHBOARD_DIR"
sudo -u "$AEGIS_USER" npm install > /dev/null 2>&1
sudo -u "$AEGIS_USER" npm run build > /dev/null 2>&1

echo -e "${GREEN}✓ Dashboard built${NC}"

# 8. Configure services
echo -e "${YELLOW}[8/10] Configuring systemd services...${NC}"

# Backend service
cat > /etc/systemd/system/aegis-server.service <<EOF
[Unit]
Description=Aegis SIEM Backend Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$AEGIS_USER
Group=$AEGIS_GROUP
WorkingDirectory=$SERVER_DIR
Environment="PATH=$SERVER_DIR/venv/bin"
ExecStart=$SERVER_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $SERVER_PORT --workers 4
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/server.log
StandardError=append:$LOG_DIR/server-error.log

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
cat > /etc/nginx/sites-available/aegis-dashboard <<EOF
server {
    listen $DASHBOARD_PORT;
    server_name ${DOMAIN:-_};
    
    root $DASHBOARD_DIR/dist;
    index index.html;
    
    # Frontend
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # API Proxy
    location /api/ {
        proxy_pass http://localhost:$SERVER_PORT/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket support
    location /ws {
        proxy_pass http://localhost:$SERVER_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/aegis-dashboard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

echo -e "${GREEN}✓ Services configured${NC}"

# 9. Initialize database schema
echo -e "${YELLOW}[9/10] Initializing database schema...${NC}"
cd "$SERVER_DIR"
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
sudo -u "$AEGIS_USER" "$SERVER_DIR/venv/bin/python" -c "
from internal.storage.init_db import init_database
import asyncio
asyncio.run(init_database())
print('Database initialized successfully')
" 2>/dev/null || echo -e "${YELLOW}Note: Database schema will be created on first run${NC}"

echo -e "${GREEN}✓ Database initialized${NC}"

# 10. Start services
echo -e "${YELLOW}[10/10] Starting services...${NC}"

systemctl daemon-reload
systemctl enable aegis-server
systemctl start aegis-server

nginx -t > /dev/null 2>&1
systemctl restart nginx
systemctl enable nginx

echo -e "${GREEN}✓ Services started${NC}"

# Save credentials
cat > "$CONFIG_DIR/credentials.txt" <<EOF
===========================================
   Aegis SIEM Installation Credentials
===========================================

Database:
  Name: $DB_NAME
  User: $DB_USER
  Password: $DB_PASSWORD

JWT Secret: $JWT_SECRET

Server:
  URL: http://localhost:$SERVER_PORT
  Logs: $LOG_DIR/server.log

Dashboard:
  URL: http://$(hostname -I | awk '{print $1}'):$DASHBOARD_PORT
  ${DOMAIN:+Domain: http://$DOMAIN}

Installation Directory: $INSTALL_DIR

Service Management:
  Backend: systemctl status aegis-server
  Nginx: systemctl status nginx
  Logs: journalctl -u aegis-server -f

===========================================
IMPORTANT: Save these credentials securely!
===========================================
EOF

chmod 600 "$CONFIG_DIR/credentials.txt"

# Installation complete
echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════╗"
echo "║   Installation Complete! ✓            ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Access your Aegis SIEM Dashboard:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):$DASHBOARD_PORT"
[ -n "$DOMAIN" ] && echo "  http://$DOMAIN"
echo ""
echo -e "${BLUE}Credentials saved to:${NC}"
echo "  $CONFIG_DIR/credentials.txt"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  View server logs:    journalctl -u aegis-server -f"
echo "  Restart server:      systemctl restart aegis-server"
echo "  Server status:       systemctl status aegis-server"
echo "  Nginx status:        systemctl status nginx"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Create admin user: cd $SERVER_DIR && ./venv/bin/python scripts/generate_invitation.py"
echo "  2. Install agents on your devices"
echo "  3. Configure ML model training"
echo ""
echo -e "${GREEN}Thank you for installing Aegis SIEM!${NC}"
echo ""
