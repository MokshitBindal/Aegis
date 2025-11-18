#!/bin/bash
# Master build script for all Aegis SIEM packages

set -e

VERSION="1.0.0"
DIST_DIR="$(pwd)/dist"

echo "🚀 Building all Aegis SIEM packages v${VERSION}"
echo "================================================"

# Clean dist directory
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Build Server Package (Ubuntu/Debian)
echo ""
echo "📦 Building Server Package (.deb)..."
bash packages/build-server-deb.sh

# Build Agent Package (Ubuntu/Debian)
echo ""
echo "📦 Building Agent Package (.deb)..."
bash packages/build-agent-deb.sh

# Build Agent Package (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "📦 Building Agent Package (.pkg for macOS)..."
    bash packages/build-agent-macos.sh
else
    echo ""
    echo "⏭️  Skipping macOS package (not on macOS)"
fi

# Windows build note
echo ""
echo "ℹ️  Windows Installer:"
echo "   Run build-agent-windows.ps1 on Windows with NSIS installed"

echo ""
echo "✅ Build complete!"
echo "📦 Packages available in: ${DIST_DIR}/"
echo ""
ls -lh "${DIST_DIR}/" 2>/dev/null || echo "No packages built yet"
