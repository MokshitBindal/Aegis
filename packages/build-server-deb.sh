#!/bin/bash
# Build Aegis SIEM Server .deb package

set -e

VERSION="1.0.0"
ARCH="amd64"
PACKAGE_NAME="aegis-siem-server_${VERSION}_${ARCH}"
BUILD_DIR="$(pwd)/packages/aegis-server-deb"
DIST_DIR="$(pwd)/dist"

echo "📦 Building Aegis SIEM Server .deb package v${VERSION}"

# Clean previous builds
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Create package structure
mkdir -p "${BUILD_DIR}/opt/aegis-siem/server"
mkdir -p "${BUILD_DIR}/opt/aegis-siem/dashboard"
mkdir -p "${BUILD_DIR}/etc/systemd/system"
mkdir -p "${BUILD_DIR}/etc/nginx/sites-available"
mkdir -p "${BUILD_DIR}/var/log/aegis-siem"
mkdir -p "${BUILD_DIR}/usr/share/doc/aegis-siem-server"

echo "📂 Copying server files..."
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' \
    --exclude='.pytest_cache' --exclude='*.db' \
    aegis-server/ "${BUILD_DIR}/opt/aegis-siem/server/"

echo "📂 Copying dashboard files..."
rsync -av --exclude='node_modules' --exclude='dist' --exclude='.vite' \
    aegis-dashboard/ "${BUILD_DIR}/opt/aegis-siem/dashboard/"

echo "📂 Copying systemd service..."
cat > "${BUILD_DIR}/etc/systemd/system/aegis-server.service" << 'EOF'
[Unit]
Description=Aegis SIEM Server
After=network.target postgresql.service

[Service]
Type=simple
User=aegis-server
Group=aegis-server
WorkingDirectory=/opt/aegis-siem/server
Environment="PATH=/opt/aegis-siem/server/venv/bin"
ExecStart=/opt/aegis-siem/server/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "📂 Copying Nginx configuration..."
cat > "${BUILD_DIR}/etc/nginx/sites-available/aegis-siem" << 'EOF'
server {
    listen 80;
    server_name _;

    # Dashboard static files
    location / {
        root /opt/aegis-siem/dashboard/dist;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

echo "📂 Copying documentation..."
cp README.md "${BUILD_DIR}/usr/share/doc/aegis-siem-server/"
cp TESTING_GUIDE.md "${BUILD_DIR}/usr/share/doc/aegis-siem-server/" 2>/dev/null || true

echo "📂 Creating copyright file..."
cat > "${BUILD_DIR}/usr/share/doc/aegis-siem-server/copyright" << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Aegis SIEM
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
