#!/usr/bin/env python3

import sqlite3
import os
import sys

def check_sudo():
    """Check if script is running with sudo"""
    if os.geteuid() != 0:
        print("This script must be run with sudo privileges")
        print("Please run: sudo ./venv/bin/python scripts/cleanup.py")
        sys.exit(1)

def cleanup_local_logs():
    """Cleans up the local SQLite database"""
    # Ensure we have sudo privileges
    check_sudo()
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect("agent.db")
        cursor = conn.cursor()
        
        # Delete all logs
        cursor.execute("DELETE FROM logs")
        conn.commit()
        
        # Vacuum to reclaim space
        cursor.execute("VACUUM")
        conn.commit()
        
        # Close connection
        conn.close()
        print("Successfully cleared local logs database.")
    except Exception as e:
        print(f"Error clearing local logs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure we're in the right directory
    agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(agent_dir)
    
    print("Starting cleanup process...")
    cleanup_local_logs()
    print("Cleanup complete!")