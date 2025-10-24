#!/bin/bash
if [ -f /etc/os-release ]; then
    # Source the os-release file to get variables
    . /etc/os-release
    
    echo "OS detection script:"
    echo "--------------------------"
    echo "Found OS ID: $ID"
    
    if [ "$ID" = "arch" ]; then
        echo "Detected Arch Linux. Guiding with pacman."
    elif [ "$ID" = "ubuntu" ] || [ "$ID" = "debian" ]; then
        echo "Detected Debian/Ubuntu. Guiding with apt."
    else
        echo "Detected '$NAME'. This script will proceed with Arch-specific guidance."
    fi
    echo "--------------------------"
else
    echo "Error: /etc/os-release file not found."
    echo "Cannot auto-detect OS. Please install manually."
fi