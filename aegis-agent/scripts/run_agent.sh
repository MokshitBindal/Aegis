#!/bin/bash

# Find the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Go up one level to the main agent directory
AGENT_DIR="$(dirname "$SCRIPT_DIR")"

# Define paths using variables (quotes are safe in shell scripts)
# IMPORTANT: Ensure these paths correctly point to your venv python and main.py
VENV_PYTHON="$AGENT_DIR/venv/bin/python"
MAIN_SCRIPT="$AGENT_DIR/main.py"

echo "Wrapper: Starting Aegis Agent..."
echo "Wrapper: Changing directory to: $AGENT_DIR"

# --- Change to the agent directory ---
# This replaces the need for WorkingDirectory in the service file
cd "$AGENT_DIR" || { echo "Wrapper: Failed to cd into $AGENT_DIR"; exit 1; }

echo "Wrapper: Executing: $VENV_PYTHON $MAIN_SCRIPT run"

# Execute the main script using the virtual environment's Python
# Use 'exec' so the Python process replaces the shell script process
exec "$VENV_PYTHON" "$MAIN_SCRIPT" run