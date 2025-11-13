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
        
        # Track last synced timestamp for commands
        sync_state_schema = """
        CREATE TABLE IF NOT EXISTS sync_state (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
        
        # Process monitoring data
        processes_schema = """
        CREATE TABLE IF NOT EXISTS processes (
            id                  INTEGER PRIMARY KEY,
            pid                 INTEGER NOT NULL,
            name                TEXT NOT NULL,
            exe                 TEXT,
            cmdline             TEXT,
            username            TEXT,
            status              TEXT,
            create_time         TEXT,
            ppid                INTEGER,
            cpu_percent         REAL,
            memory_percent      REAL,
            memory_rss          INTEGER,
            memory_vms          INTEGER,
            num_threads         INTEGER,
            num_fds             INTEGER,
            num_connections     INTEGER,
            connection_details  TEXT,
            agent_id            TEXT NOT NULL,
            collected_at        TEXT NOT NULL,
            forwarded           INTEGER DEFAULT 0
        );
        """
        
        try:
            with self.lock:
                self.conn.execute(logs_schema)
                self.conn.execute(alerts_schema)
                self.conn.execute(commands_schema)
                self.conn.execute(sync_state_schema)
                self.conn.execute(processes_schema)
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
    def get_last_command_sync_timestamp(self) -> str | None:
        """
        Gets the timestamp of the last command successfully synced to the server.
        
        Returns:
            str | None: ISO format timestamp string, or None if never synced
        """
        sql = "SELECT value FROM sync_state WHERE key = 'last_command_sync'"
        
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(sql)
                row = cursor.fetchone()
                return row['value'] if row else None
        except Exception as e:
            print(f"Error getting last command sync timestamp: {e}")
            return None
    
    def set_last_command_sync_timestamp(self, timestamp: str):
        """
        Updates the timestamp of the last command successfully synced to the server.
        
        Args:
            timestamp (str): ISO format timestamp string
        """
        sql = """
        INSERT OR REPLACE INTO sync_state (key, value, updated_at)
        VALUES ('last_command_sync', ?, ?)
        """
        
        try:
            with self.lock:
                self.conn.execute(sql, (timestamp, datetime.now().isoformat()))
                self.conn.commit()
        except Exception as e:
            print(f"Error setting last command sync timestamp: {e}")
    
    # --- PROCESS STORAGE METHODS ---
    
    def store_processes(self, processes: list[dict], agent_id: str):
        """
        Stores a batch of process data in the database.
        
        Args:
            processes (List[dict]): List of process information dictionaries
            agent_id (str): Agent ID for tracking
        """
        sql = """
        INSERT INTO processes (
            pid, name, exe, cmdline, username, status, create_time, ppid,
            cpu_percent, memory_percent, memory_rss, memory_vms,
            num_threads, num_fds, num_connections, connection_details,
            agent_id, collected_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        collected_at = datetime.now().isoformat()
        
        try:
            with self.lock:
                for proc in processes:
                    params = (
                        proc.get('pid'),
                        proc.get('name'),
                        proc.get('exe'),
                        proc.get('cmdline'),
                        proc.get('username'),
                        proc.get('status'),
                        proc.get('create_time'),
                        proc.get('ppid'),
                        proc.get('cpu_percent'),
                        proc.get('memory_percent'),
                        proc.get('memory_rss'),
                        proc.get('memory_vms'),
                        proc.get('num_threads'),
                        proc.get('num_fds'),
                        proc.get('num_connections'),
                        json.dumps(proc.get('connection_details', [])),
                        agent_id,
                        collected_at
                    )
                    self.conn.execute(sql, params)
                self.conn.commit()
        except Exception as e:
            print(f"Error writing processes to SQLite: {e}")
    
    def get_pending_processes(self, batch_size: int = None) -> list[dict[str, Any]]:
        """
        Retrieves ALL processes that haven't been forwarded to the server yet.
        
        Process snapshots should be sent as complete sets, not partial batches.
        This ensures the server receives the full process list from each collection cycle.
        
        Args:
            batch_size (int): DEPRECATED - Not used. Kept for backward compatibility.
            
        Returns:
            List[Dict[str, Any]]: List of ALL unforwarded process records.
        """
        # Get ALL unforwarded processes (no LIMIT)
        sql = "SELECT * FROM processes WHERE forwarded = 0"
        
        try:
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute(sql)
                rows = [dict(row) for row in cursor.fetchall()]
                # Parse the connection_details JSON string back to list
                for row in rows:
                    try:
                        row['connection_details'] = json.loads(row['connection_details'])
                    except (json.JSONDecodeError, KeyError):
                        row['connection_details'] = []
                return rows
        except Exception as e:
            print(f"Error reading pending processes: {e}")
            return []
    
    def mark_processes_forwarded(self, process_ids: list[int]):
        """
        Marks processes as forwarded to the server and cleans up old forwarded records.
        
        Args:
            process_ids (List[int]): List of process primary keys to mark.
        """
        if not process_ids:
            return
            
        placeholders = ', '.join('?' * len(process_ids))
        sql = f"UPDATE processes SET forwarded = 1 WHERE id IN ({placeholders})"
        
        try:
            with self.lock:
                self.conn.execute(sql, process_ids)
                
                # Clean up old forwarded processes to prevent database bloat
                # Keep only last 1000 forwarded processes for reference
                cleanup_sql = """
                    DELETE FROM processes 
                    WHERE forwarded = 1 
                    AND id NOT IN (
                        SELECT id FROM processes 
                        WHERE forwarded = 1 
                        ORDER BY id DESC 
                        LIMIT 1000
                    )
                """
                self.conn.execute(cleanup_sql)
                self.conn.commit()
        except Exception as e:
            print(f"Error marking processes as forwarded: {e}")
