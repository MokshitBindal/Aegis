# aegis-agent/internal/storage/sqlite.py

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Tuple

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
        Creates the 'logs', 'alerts', and 'commands' tables if they don't already exist.
        """
        logs_schema = """
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY,
            timestamp   TEXT NOT NULL,
            hostname    TEXT,
            message     TEXT,
            raw_json    TEXT,
            forwarded   INTEGER DEFAULT 0
        );
        """
        
        alerts_schema = """
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY,
            rule_name   TEXT NOT NULL,
            severity    TEXT NOT NULL,
            details     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            agent_id    TEXT NOT NULL,
            forwarded   INTEGER DEFAULT 0
        );
        """
        
        commands_schema = """
        CREATE TABLE IF NOT EXISTS commands (
            id                  INTEGER PRIMARY KEY,
            command             TEXT NOT NULL,
            user                TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            shell               TEXT,
            source              TEXT,
            working_directory   TEXT,
            exit_code           INTEGER,
            agent_id            TEXT NOT NULL,
            forwarded           INTEGER DEFAULT 0
        );
        """
        
        try:
            with self.lock:
                self.conn.execute(logs_schema)
                self.conn.execute(alerts_schema)
                self.conn.execute(commands_schema)
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
    def get_unforwarded_logs(self, batch_size: int = 100) -> list[dict[str, Any]]:
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
    def mark_logs_as_forwarded(self, log_ids: list[int]):
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

    # --- ALERT STORAGE METHODS ---
    
    def store_alert(self, alert: dict):
        """
        Stores a generated alert in the database.
        
        Args:
            alert (dict): Alert dictionary with rule_name, severity, details, etc.
        """
        sql = """
        INSERT INTO alerts (rule_name, severity, details, timestamp, agent_id)
        VALUES (?, ?, ?, ?, ?)
        """
        
        params = (
            alert.get('rule_name', 'Unknown'),
            alert.get('severity', 'low'),
            json.dumps(alert.get('details', {})),
            alert.get('timestamp', datetime.now().isoformat()),
            alert.get('agent_id', '')
        )
        
        try:
            with self.lock:
                self.conn.execute(sql, params)
                self.conn.commit()
        except Exception as e:
            print(f"Error writing alert to SQLite: {e}")
    
    def get_pending_alerts(self, batch_size: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves alerts that haven't been forwarded to the server yet.
        
        Args:
            batch_size (int): Maximum number of alerts to retrieve.
            
        Returns:
            List[Dict[str, Any]]: List of alert records as dictionaries.
        """
        sql = "SELECT * FROM alerts WHERE forwarded = 0 LIMIT ?"
        
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(sql, (batch_size,))
                rows = [dict(row) for row in cursor.fetchall()]
                # Parse the details JSON string back to dict
                for row in rows:
                    try:
                        row['details'] = json.loads(row['details'])
                    except (json.JSONDecodeError, KeyError):
                        row['details'] = {}
                return rows
        except Exception as e:
            print(f"Error reading pending alerts: {e}")
            return []
    
    def mark_alerts_forwarded(self, alert_ids: list[int]):
        """
        Marks alerts as forwarded to the server.
        
        Args:
            alert_ids (List[int]): List of alert primary keys to mark.
        """
        if not alert_ids:
            return
            
        placeholders = ', '.join('?' * len(alert_ids))
        sql = f"UPDATE alerts SET forwarded = 1 WHERE id IN ({placeholders})"
        
        try:
            with self.lock:
                self.conn.execute(sql, alert_ids)
                self.conn.commit()
        except Exception as e:
            print(f"Error marking alerts as forwarded: {e}")
    
    # --- COMMAND STORAGE METHODS ---
    
    def store_command(self, command: dict):
        """
        Stores a terminal command in the database.
        
        Args:
            command (dict): Command dictionary with user, timestamp, command, etc.
        """
        sql = """
        INSERT INTO commands (command, user, timestamp, shell, source, working_directory, exit_code, agent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            command.get('command', ''),
            command.get('user', ''),
            command.get('timestamp', datetime.now().isoformat()),
            command.get('shell', ''),
            command.get('source', ''),
            command.get('working_directory'),
            command.get('exit_code'),
            command.get('agent_id', '')
        )
        
        try:
            with self.lock:
                self.conn.execute(sql, params)
                self.conn.commit()
        except Exception as e:
            print(f"Error writing command to SQLite: {e}")
    
    def get_pending_commands(self, batch_size: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves commands that haven't been forwarded to the server yet.
        
        Args:
            batch_size (int): Maximum number of commands to retrieve.
            
        Returns:
            List[Dict[str, Any]]: List of command records as dictionaries.
        """
        sql = "SELECT * FROM commands WHERE forwarded = 0 LIMIT ?"
        
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(sql, (batch_size,))
                rows = [dict(row) for row in cursor.fetchall()]
                return rows
        except Exception as e:
            print(f"Error reading pending commands: {e}")
            return []
    
    def mark_commands_forwarded(self, command_ids: list[int]):
        """
        Marks commands as forwarded to the server.
        
        Args:
            command_ids (List[int]): List of command primary keys to mark.
        """
        if not command_ids:
            return
            
        placeholders = ', '.join('?' * len(command_ids))
        sql = f"UPDATE commands SET forwarded = 1 WHERE id IN ({placeholders})"
        
        try:
            with self.lock:
                self.conn.execute(sql, command_ids)
                self.conn.commit()
        except Exception as e:
            print(f"Error marking commands as forwarded: {e}")

    def close(self):
        """
        Closes the database connection.
        """
        if self.conn:
            self.conn.close()
            print("Database connection closed.")