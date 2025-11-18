#!/bin/bash
# Build Aegis SIEM Agent .deb package

set -e

VERSION="1.0.0"
ARCH="amd64"
PACKAGE_NAME="aegis-siem-agent_${VERSION}_${ARCH}"
BUILD_DIR="$(pwd)/packages/aegis-agent-deb"
DIST_DIR="$(pwd)/dist"

echo "📦 Building Aegis SIEM Agent .deb package v${VERSION}"

# Create dist directory
mkdir -p "${DIST_DIR}"

# Create package structure
mkdir -p "${BUILD_DIR}/opt/aegis-agent"
mkdir -p "${BUILD_DIR}/etc/systemd/system"
mkdir -p "${BUILD_DIR}/var/log/aegis-agent"
mkdir -p "${BUILD_DIR}/usr/share/doc/aegis-siem-agent"

echo "📂 Copying agent files..."
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' \
    --exclude='.pytest_cache' --exclude='*.db' --exclude='agent.id' \
    --exclude='agent.credentials' \
    aegis-agent/ "${BUILD_DIR}/opt/aegis-agent/"

echo "📂 Creating .env template..."
cat > "${BUILD_DIR}/opt/aegis-agent/.env.example" << 'EOF'
# Aegis SIEM Agent Configuration

# Server connection
AEGIS_SERVER_URL=https://your-server.example.com
REGISTRATION_TOKEN=your-registration-token-here

# Agent settings
AGENT_NAME=agent-hostname
COLLECTION_INTERVAL=60
LOG_LEVEL=INFO
EOF

echo "📂 Copying systemd service..."
cat > "${BUILD_DIR}/etc/systemd/system/aegis-agent.service" << 'EOF'
[Unit]
Description=Aegis SIEM Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=aegis-agent
Group=aegis-agent
WorkingDirectory=/opt/aegis-agent
Environment="PATH=/opt/aegis-agent/venv/bin"
ExecStart=/opt/aegis-agent/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aegis-agent /var/log/aegis-agent
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "📂 Copying documentation..."
cp README.md "${BUILD_DIR}/usr/share/doc/aegis-siem-agent/"

echo "📂 Creating copyright file..."
cat > "${BUILD_DIR}/usr/share/doc/aegis-siem-agent/copyright" << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Aegis SIEM Agent
Upstream-Contact: Mokshit Bindal
Source: https://github.com/MokshitBindal/Aegis

Files: *
Copyright: 2025 Mokshit Bindal
License: MIT
EOF

echo "🔧 Setting permissions..."
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

echo "🏗️  Building package..."
dpkg-deb --build "${BUILD_DIR}" "${DIST_DIR}/${PACKAGE_NAME}.deb"

echo "✅ Package built successfully!"
echo "📦 Output: ${DIST_DIR}/${PACKAGE_NAME}.deb"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${DIST_DIR}/${PACKAGE_NAME}.deb"
echo "  sudo apt-get install -f  # Install dependencies"
