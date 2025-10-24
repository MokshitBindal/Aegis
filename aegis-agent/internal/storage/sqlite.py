# aegis-agent/internal/storage/sqlite.py

import sqlite3
import threading
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Define the database file name
DB_FILE = "agent.db"

class Storage:
    """
    Handles all SQLite database operations for the agent.
    
    This class is designed to be thread-safe, as it will be accessed
    from the collector thread (writing) and the forwarder thread (reading).
    """
    
    def __init__(self):
        """
        Initializes the database connection and creates the logs table.
        """
        self.lock = threading.RLock()
        
        # 'check_same_thread=False' is important for multi-threaded access
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        # Use Row factory to get dict-like results
        self.conn.row_factory = sqlite3.Row 
        
        print(f"Database connection established to {DB_FILE}")
        self._create_schema()

    def _create_schema(self):
        """
        Creates the 'logs' table if it doesn't already exist.
        """
        schema = """
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY,
            timestamp   TEXT NOT NULL,
            hostname    TEXT,
            message     TEXT,
            raw_json    TEXT,
            forwarded   INTEGER DEFAULT 0
        );
        """
        try:
            with self.lock:
                self.conn.execute(schema)
                self.conn.commit()
            print("Database schema verified.")
        except Exception as e:
            print(f"Error creating database schema: {e}")

    def write_log(self, log_data: dict):
        """
        Writes a single processed log entry to the database.
        
        Args:
            log_data (dict): A dictionary containing the processed log.
        """
        sql = """
        INSERT INTO logs (timestamp, hostname, message, raw_json)
        VALUES (?, ?, ?, ?)
        """
        
        if isinstance(log_data['timestamp'], datetime):
            ts_str = log_data['timestamp'].isoformat()
        else:
            ts_str = str(log_data['timestamp'])

        params = (
            ts_str,
            log_data.get('hostname', 'N/A'),
            log_data.get('message', 'N/A'),
            log_data.get('raw_json', '{}')
        )
        
        try:
            with self.lock:
                self.conn.execute(sql, params)
                self.conn.commit()
        except Exception as e:
            print(f"Error writing log to SQLite: {e}")

    # --- NEW METHOD ---
    def get_unforwarded_logs(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves a batch of logs that have not yet been forwarded.
        
        Args:
            batch_size (int): The maximum number of logs to retrieve.
            
        Returns:
            List[Dict[str, Any]]: A list of log records as dictionaries.
        """
        sql = "SELECT * FROM logs WHERE forwarded = 0 LIMIT ?"
        
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(sql, (batch_size,))
                # Convert rows to standard dicts
                rows = [dict(row) for row in cursor.fetchall()]
                return rows
        except Exception as e:
            print(f"Error reading unforwarded logs: {e}")
            return []

    # --- NEW METHOD ---
    def mark_logs_as_forwarded(self, log_ids: List[int]):
        """
        Updates a list of logs to set their 'forwarded' status to 1.
        
        Args:
            log_ids (List[int]): The list of log primary keys (id) to update.
        """
        if not log_ids:
            return
            
        # We need to create a string of placeholders: (?, ?, ?)
        placeholders = ', '.join('?' * len(log_ids))
        sql = f"UPDATE logs SET forwarded = 1 WHERE id IN ({placeholders})"
        
        try:
            with self.lock:
                self.conn.execute(sql, log_ids)
                self.conn.commit()
        except Exception as e:
            print(f"Error marking logs as forwarded: {e}")

    def close(self):
        """
        Closes the database connection.
        """
        if self.conn:
            self.conn.close()
            print("Database connection closed.")