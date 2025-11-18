#!/bin/bash
# Build Aegis SIEM Agent macOS .pkg installer

set -e

VERSION="1.0.0"
PACKAGE_NAME="Aegis-SIEM-Agent-${VERSION}-macOS"
BUILD_DIR="$(pwd)/packages/aegis-agent-macos"
DIST_DIR="$(pwd)/dist"
PKG_ROOT="${BUILD_DIR}/root"
PKG_SCRIPTS="${BUILD_DIR}/scripts"

echo "📦 Building Aegis SIEM Agent macOS .pkg v${VERSION}"

# Create directories
mkdir -p "${DIST_DIR}"
mkdir -p "${PKG_ROOT}/usr/local/aegis-agent"
mkdir -p "${PKG_ROOT}/Library/LaunchDaemons"
mkdir -p "${PKG_SCRIPTS}"

echo "📂 Copying agent files..."
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' \
    --exclude='.pytest_cache' --exclude='*.db' --exclude='agent.id' \
    --exclude='agent.credentials' \
    aegis-agent/ "${PKG_ROOT}/usr/local/aegis-agent/"

echo "📂 Creating .env template..."
cat > "${PKG_ROOT}/usr/local/aegis-agent/.env.example" << 'EOF'
# Aegis SIEM Agent Configuration
AEGIS_SERVER_URL=https://your-server.example.com
REGISTRATION_TOKEN=your-token-here
AGENT_NAME=$(hostname)
COLLECTION_INTERVAL=60
LOG_LEVEL=INFO
EOF

echo "📂 Creating LaunchDaemon plist..."
cat > "${PKG_ROOT}/Library/LaunchDaemons/com.aegis.agent.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aegis.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/aegis-agent/venv/bin/python3</string>
        <string>/usr/local/aegis-agent/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/usr/local/aegis-agent</string>
    <key>StandardOutPath</key>
    <string>/var/log/aegis-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/aegis-agent.error.log</string>
</dict>
</plist>
EOF

echo "📂 Creating postinstall script..."
cat > "${PKG_SCRIPTS}/postinstall" << 'EOF'
#!/bin/bash
set -e

echo "🔧 Configuring Aegis SIEM Agent..."

# Install Python dependencies
cd /usr/local/aegis-agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Set permissions
chown -R root:wheel /usr/local/aegis-agent
chmod 755 /usr/local/aegis-agent

# Load LaunchDaemon
launchctl load /Library/LaunchDaemons/com.aegis.agent.plist

echo "✅ Aegis SIEM Agent installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Configure: /usr/local/aegis-agent/.env"
echo "2. Start: sudo launchctl start com.aegis.agent"
echo "3. Check logs: tail -f /var/log/aegis-agent.log"

exit 0
EOF

echo "📂 Creating preinstall script..."
cat > "${PKG_SCRIPTS}/preinstall" << 'EOF'
#!/bin/bash
# Stop agent if running
launchctl unload /Library/LaunchDaemons/com.aegis.agent.plist 2>/dev/null || true
exit 0
EOF

chmod 755 "${PKG_SCRIPTS}/postinstall"
chmod 755 "${PKG_SCRIPTS}/preinstall"

echo "🏗️  Building package..."
pkgbuild --root "${PKG_ROOT}" \
         --scripts "${PKG_SCRIPTS}" \
         --identifier com.aegis.agent \
         --version "${VERSION}" \
         --install-location / \
         "${DIST_DIR}/${PACKAGE_NAME}.pkg"

echo "✅ Package built successfully!"
echo "📦 Output: ${DIST_DIR}/${PACKAGE_NAME}.pkg"
echo ""
echo "To install:"
echo "  sudo installer -pkg ${DIST_DIR}/${PACKAGE_NAME}.pkg -target /"
echo ""
echo "Note: Requires Python 3.11+ to be installed on macOS"
