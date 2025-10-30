# aegis-agent/internal/collector/command_collector.py

"""
Terminal Command Collector for Linux/macOS systems.
Captures shell commands executed by users for security monitoring.
"""

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import pwd
import requests


class CommandCollector:
    """
    Collects terminal commands from various sources:
    - Shell history files (bash, zsh)
    - Process auditing (via auditd or process monitoring)
    - Real-time command execution tracking
    """
    
    def __init__(self, storage=None, analysis_engine=None, agent_id=None, server_base=None):
        """
        Initialize the command collector.
        
        Args:
            storage: Storage instance for persisting commands
            analysis_engine: Analysis engine for real-time detection
            agent_id: Agent identifier
            server_base: Base server URL (e.g., http://localhost:8000)
        """
        self.storage = storage
        self.analysis_engine = analysis_engine
        self.agent_id = agent_id or ""
        self.server_base = server_base or "http://127.0.0.1:8000"
        self.last_positions = {}  # Track file positions for tail-like behavior
        self.seen_commands = set()  # Track command hashes to prevent duplicates
        self.platform = self._detect_platform()
        self.initialized = False  # Track if we've done initial setup
        self.last_sync_timestamp = None  # Last command sync timestamp from server
        
        print(f"[CommandCollector] Initialized for platform: {self.platform}")
    
    def _detect_platform(self) -> str:
        """Detect the operating system platform."""
        if os.path.exists('/proc'):
            return 'linux'
        elif os.path.exists('/Library'):
            return 'macos'
        else:
            return 'unknown'
    
    def _fetch_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Fetch the last command sync timestamp from the server.
        This tells us the timestamp of the most recent command already stored on the server.
        
        Returns:
            datetime object of last sync, or None if no commands exist yet
        """
        try:
            url = f"{self.server_base}/api/commands/last-sync/{self.agent_id}"
            headers = {"X-Aegis-Agent-ID": self.agent_id}
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                timestamp_str = data.get("timestamp")
                
                if timestamp_str:
                    # Parse ISO format timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    print(f"[CommandCollector] Last sync timestamp from server: {timestamp}")
                    return timestamp
                else:
                    print("[CommandCollector] No previous commands on server, collecting all")
                    return None
            else:
                print(f"[CommandCollector] Failed to fetch last sync timestamp: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[CommandCollector] Error fetching last sync timestamp: {e}")
            return None
        except Exception as e:
            print(f"[CommandCollector] Unexpected error fetching last sync: {e}")
            return None
    
    def _initialize_file_positions(self):
        """
        Initialize file positions to end of all history files.
        This prevents reading thousands of old commands on startup.
        """
        users = self._get_system_users()
        
        for user_info in users:
            home_dir = user_info['home']
            
            history_files = [
                os.path.join(home_dir, '.bash_history'),
                os.path.join(home_dir, '.zsh_history'),
                os.path.join(home_dir, '.sh_history'),
            ]
            
            for history_file in history_files:
                if os.path.exists(history_file):
                    try:
                        # Set position to end of file
                        file_size = os.path.getsize(history_file)
                        self.last_positions[history_file] = file_size
                        print(f"[CommandCollector] Initialized {history_file} at position {file_size}")
                    except Exception as e:
                        print(f"[CommandCollector] Error initializing {history_file}: {e}")
    
    def collect_commands(self) -> List[Dict]:
        """
        Main collection method - gathers commands from all available sources.
        
        Returns:
            List of command dictionaries with metadata
        """
        commands = []
        
        # On first run, fetch last sync timestamp from server and initialize file positions
        if not self.initialized:
            self.last_sync_timestamp = self._fetch_last_sync_timestamp()
            
            # If no previous sync, set to 6 months ago (retention policy)
            if self.last_sync_timestamp is None:
                from datetime import timedelta
                six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
                self.last_sync_timestamp = six_months_ago
                print(f"[CommandCollector] No previous sync, using 6-month retention: {six_months_ago}")
            
            self._initialize_file_positions()
            self.initialized = True
            print("[CommandCollector] First run initialized, will collect commands newer than last sync")
        
        # Collect from shell history files
        commands.extend(self._collect_from_history_files())
        
        # Note: Process monitoring disabled to prevent spam
        # commands.extend(self._collect_from_processes())
        
        # Store and analyze
        if commands:
            self._process_commands(commands)
        
        return commands
    
    def _collect_from_history_files(self) -> List[Dict]:
        """
        Collect commands from shell history files (bash_history, zsh_history).
        Uses tail-like behavior to only read new commands.
        """
        commands = []
        
        # Get all user home directories
        users = self._get_system_users()
        
        for user_info in users:
            username = user_info['username']
            home_dir = user_info['home']
            
            # Check common shell history files
            history_files = [
                os.path.join(home_dir, '.bash_history'),
                os.path.join(home_dir, '.zsh_history'),
                os.path.join(home_dir, '.sh_history'),
            ]
            
            for history_file in history_files:
                if os.path.exists(history_file):
                    try:
                        new_commands = self._read_new_lines(history_file, username)
                        commands.extend(new_commands)
                    except PermissionError:
                        # Can't read this file (need sudo for other users' files)
                        continue
                    except Exception as e:
                        print(f"[CommandCollector] Error reading {history_file}: {e}")
        
        return commands
    
    def _read_new_lines(self, filepath: str, username: str) -> List[Dict]:
        """
        Read only new lines from a file since last read (tail -f behavior).
        
        Args:
            filepath: Path to history file
            username: User who owns the file
            
        Returns:
            List of command dictionaries
        """
        commands = []
        
        # Get current file size and last known position
        current_size = os.path.getsize(filepath)
        last_pos = self.last_positions.get(filepath, 0)
        
        # If file was truncated or this is first read, start from beginning
        if current_size < last_pos:
            last_pos = 0
        
        # Read new content
        with open(filepath, 'r', errors='ignore') as f:
            f.seek(last_pos)
            new_lines = f.readlines()
            self.last_positions[filepath] = f.tell()
        
        # Parse commands
        shell_type = self._detect_shell_type(filepath)
        
        for line in new_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse based on shell type
            if shell_type == 'zsh' and ':' in line[:20]:
                # ZSH extended history format: `: timestamp:elapsed;command`
                command_data = self._parse_zsh_history_line(line, username, filepath)
            else:
                # Standard bash format
                command_data = self._parse_bash_history_line(line, username, filepath)
            
            if command_data:
                commands.append(command_data)
        
        return commands
    
    def _detect_shell_type(self, filepath: str) -> str:
        """Detect shell type from history file path."""
        if 'zsh' in filepath:
            return 'zsh'
        elif 'bash' in filepath:
            return 'bash'
        else:
            return 'sh'
    
    def _parse_zsh_history_line(self, line: str, username: str, source: str) -> Optional[Dict]:
        """
        Parse ZSH extended history format.
        Format: `: timestamp:elapsed;command`
        """
        # ZSH extended history: `: 1698765432:0;ls -la`
        match = re.match(r'^:\s*(\d+):(\d+);(.+)$', line)
        
        if match:
            timestamp_str, elapsed, command = match.groups()
            timestamp = datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
        else:
            # Fallback: plain command without timestamp
            timestamp = datetime.now(timezone.utc)
            command = line
        
        # Filter: only collect commands newer than last sync
        if self.last_sync_timestamp and timestamp <= self.last_sync_timestamp:
            return None
        
        return {
            'command': command.strip(),
            'user': username,
            'timestamp': timestamp.isoformat(),
            'shell': 'zsh',
            'source': source,
            'working_directory': None,  # Not available from history
            'exit_code': None,
        }
    
    def _parse_bash_history_line(self, line: str, username: str, source: str) -> Optional[Dict]:
        """
        Parse standard bash history line (plain command).
        Note: Bash doesn't store timestamps by default, so we use current time.
        This means bash commands will always be collected.
        """
        # For bash without timestamps, we can't filter by time, so collect all new ones
        # Consider using HISTTIMEFORMAT in .bashrc to enable timestamp tracking
        return {
            'command': line.strip(),
            'user': username,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'shell': 'bash',
            'source': source,
            'working_directory': None,
            'exit_code': None,
        }
    
    def _collect_from_processes(self) -> List[Dict]:
        """
        Collect currently running shell commands from process list.
        This captures commands in real-time as they're being executed.
        """
        commands = []
        
        try:
            # Use ps to get all shell processes with full command line
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                
                for line in lines:
                    parts = line.split(None, 10)  # Split into max 11 parts
                    if len(parts) >= 11:
                        user = parts[0]
                        pid = parts[1]
                        command = parts[10]
                        
                        # Filter for shell commands (exclude daemons, system processes)
                        if self._is_shell_command(command):
                            commands.append({
                                'command': command,
                                'user': user,
                                'timestamp': datetime.now().isoformat(),
                                'shell': 'process',
                                'source': f'pid:{pid}',
                                'working_directory': self._get_process_cwd(pid),
                                'exit_code': None,  # Still running
                            })
        
        except subprocess.TimeoutExpired:
            print("[CommandCollector] Process collection timed out")
        except Exception as e:
            print(f"[CommandCollector] Error collecting from processes: {e}")
        
        return commands
    
    def _is_shell_command(self, command: str) -> bool:
        """
        Determine if a command is a user shell command vs system process.
        
        Args:
            command: Command string from ps output
            
        Returns:
            True if this looks like a user command
        """
        # Exclude common system processes
        exclude_patterns = [
            '/usr/sbin/', '/usr/libexec/', '/System/Library/',
            'systemd', 'dbus', 'networkd', 'kworker',
            'python', 'node', 'uvicorn',  # Don't log our own processes
        ]
        
        for pattern in exclude_patterns:
            if pattern in command:
                return False
        
        # Include common shells and user commands
        include_patterns = [
            'bash', 'zsh', 'sh', 'fish', 'tcsh',
            'ssh', 'scp', 'rsync', 'curl', 'wget',
            'sudo', 'su', 'git', 'docker',
        ]
        
        for pattern in include_patterns:
            if pattern in command:
                return True
        
        return False
    
    def _get_process_cwd(self, pid: str) -> Optional[str]:
        """Get the current working directory of a process."""
        try:
            cwd_link = f'/proc/{pid}/cwd'
            if os.path.exists(cwd_link):
                return os.readlink(cwd_link)
        except (OSError, FileNotFoundError):
            pass
        return None
    
    def _get_system_users(self) -> List[Dict]:
        """
        Get list of system users with home directories.
        
        Returns:
            List of user info dictionaries
        """
        users = []
        
        try:
            # Get all users from /etc/passwd
            for user_entry in pwd.getpwall():
                username = user_entry.pw_name
                home_dir = user_entry.pw_dir
                uid = user_entry.pw_uid
                
                # Filter out system users (UID < 1000 on Linux)
                # Include root (UID 0) for security monitoring
                if uid == 0 or uid >= 1000:
                    if os.path.isdir(home_dir):
                        users.append({
                            'username': username,
                            'home': home_dir,
                            'uid': uid,
                        })
        except Exception as e:
            print(f"[CommandCollector] Error getting system users: {e}")
        
        return users
    
    def _process_commands(self, commands: List[Dict]):
        """
        Process collected commands: store and analyze.
        
        Args:
            commands: List of command dictionaries
        """
        import hashlib
        
        processed_count = 0
        
        for cmd in commands:
            # Create unique hash for deduplication
            cmd_hash = hashlib.md5(
                f"{cmd['user']}:{cmd['timestamp']}:{cmd['command']}".encode()
            ).hexdigest()
            
            # Skip if we've seen this exact command before
            if cmd_hash in self.seen_commands:
                continue
            
            self.seen_commands.add(cmd_hash)
            processed_count += 1
            
            # Limit seen_commands set size to prevent memory growth
            if len(self.seen_commands) > 10000:
                # Keep only the most recent 5000
                self.seen_commands = set(list(self.seen_commands)[-5000:])
            
            # Add agent_id to command
            cmd['agent_id'] = self.agent_id
            
            # Store in database
            if self.storage:
                self.storage.store_command(cmd)
            
            # Analyze for suspicious patterns
            if self.analysis_engine:
                self.analysis_engine.analyze_command(cmd)
        
        # Summary log instead of per-command logging
        if processed_count > 0:
            print(f"[CommandCollector] Processed {processed_count} new commands")
    
    def start(self):
        """Start the command collector (called from main loop)."""
        print("[CommandCollector] Starting command collection...")
        self.collect_commands()
    
    def stop(self):
        """Stop the command collector and cleanup."""
        print("[CommandCollector] Stopping command collection...")
        self.last_positions.clear()
