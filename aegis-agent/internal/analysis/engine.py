# aegis-agent/internal/analysis/engine.py

import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

from internal.analysis.rules import check_failed_ssh
from internal.analysis.command_rules import analyze_command


class AnalysisEngine:
    """
    Agent-side analysis engine that applies local rules to logs and metrics.
    Generates alerts for suspicious patterns detected locally.
    """

    def __init__(self, storage, agent_id: str):
        """
        Initialize the analysis engine.

        Args:
            storage: SQLite storage instance for persisting alerts
            agent_id: Agent identifier
        """
        self.storage = storage
        self.agent_id = agent_id

        # Track failed SSH attempts per source IP
        # Format: {source_ip: deque([(timestamp, message), ...])}
        self.ssh_attempts = defaultdict(lambda: deque(maxlen=10))

        # Track CPU usage history for spike detection
        # Format: deque([(timestamp, cpu_percent), ...])
        self.cpu_history = deque(maxlen=20)

        # Alert thresholds
        self.ssh_failure_threshold = 3  # Number of failures
        self.ssh_failure_window = 300  # 5 minutes in seconds
        self.cpu_spike_threshold = 90.0  # Percentage
        self.cpu_spike_duration = 120  # 2 minutes in seconds

        # Keep track of recently fired alerts to avoid duplicates
        # Format: {(rule_name, key): last_alert_timestamp}
        self.alert_cooldown = {}
        self.cooldown_period = 300  # 5 minutes

        print("Analysis engine initialized")

    def analyze_log(self, log_entry: dict) -> list[dict]:
        """
        Analyze a single log entry and return any generated alerts.

        Args:
            log_entry: Log entry dictionary with 'timestamp', 'raw_data', etc.

        Returns:
            List of alert dictionaries (empty if no alerts)
        """
        alerts = []

        # Extract message from log entry
        try:
            if isinstance(log_entry.get("raw_data"), str):
                raw_data = json.loads(log_entry["raw_data"])
            else:
                raw_data = log_entry.get("raw_data", {})

            message = raw_data.get("MESSAGE", "")
            timestamp = log_entry.get("timestamp")

        except (json.JSONDecodeError, KeyError, TypeError):
            # Skip malformed log entries
            return alerts

        # Check for failed SSH login
        if check_failed_ssh(message):
            alert = self._check_ssh_brute_force(message, timestamp, raw_data)
            if alert:
                alerts.append(alert)

        return alerts

    def analyze_metrics(self, metrics: dict) -> list[dict]:
        """
        Analyze system metrics and return any generated alerts.

        Args:
            metrics: Metrics dictionary with 'cpu_percent', 'timestamp', etc.

        Returns:
            List of alert dictionaries (empty if no alerts)
        """
        alerts = []

        try:
            cpu_percent = metrics.get("cpu_percent")
            timestamp = metrics.get("timestamp")

            if cpu_percent is not None and timestamp:
                alert = self._check_cpu_spike(cpu_percent, timestamp)
                if alert:
                    alerts.append(alert)

        except (KeyError, TypeError, ValueError):
            # Skip malformed metrics
            pass

        return alerts

    def _check_ssh_brute_force(
        self, message: str, timestamp: str, raw_data: dict
    ) -> dict | None:
        """
        Check for SSH brute force attempts from the same source IP.

        Args:
            message: Log message string
            timestamp: Log timestamp
            raw_data: Full log data

        Returns:
            Alert dictionary if threshold exceeded, None otherwise
        """
        # Extract source IP from message
        # Pattern: "Failed password for ... from IP port ..."
        source_ip = None
        if "from " in message and " port " in message:
            try:
                parts = message.split("from ")[1].split(" port ")
                source_ip = parts[0].strip()
            except (IndexError, AttributeError):
                pass

        if not source_ip:
            return None

        # Convert timestamp to float for comparison
        try:
            if isinstance(timestamp, str):
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_float = ts.timestamp()
            else:
                ts_float = float(timestamp)
        except (ValueError, TypeError):
            ts_float = time.time()

        # Add to tracking
        self.ssh_attempts[source_ip].append((ts_float, message))

        # Remove old attempts outside the window
        cutoff_time = ts_float - self.ssh_failure_window
        while (
            self.ssh_attempts[source_ip]
            and self.ssh_attempts[source_ip][0][0] < cutoff_time
        ):
            self.ssh_attempts[source_ip].popleft()

        # Check if threshold exceeded
        attempt_count = len(self.ssh_attempts[source_ip])
        if attempt_count >= self.ssh_failure_threshold:
            # Check cooldown to avoid duplicate alerts
            alert_key = ("ssh_brute_force", source_ip)
            if self._is_in_cooldown(alert_key, ts_float):
                return None

            # Generate alert
            alert = {
                "rule_name": "Agent: SSH Brute Force Detected",
                "severity": "high",
                "details": {
                    "source_ip": source_ip,
                    "attempt_count": attempt_count,
                    "window_seconds": self.ssh_failure_window,
                    "sample_message": message,
                    "hostname": raw_data.get("_HOSTNAME", "unknown"),
                },
                "timestamp": timestamp or datetime.now().isoformat(),
                "agent_id": self.agent_id,
            }

            # Update cooldown
            self.alert_cooldown[alert_key] = ts_float

            # Store alert in SQLite
            self._store_alert(alert)

            print(f"[ALERT] SSH brute force detected from {source_ip}")
            return alert

        return None

    def _check_cpu_spike(self, cpu_percent: float, timestamp: str) -> dict | None:
        """
        Check for sustained high CPU usage.

        Args:
            cpu_percent: Current CPU usage percentage
            timestamp: Metric timestamp

        Returns:
            Alert dictionary if spike detected, None otherwise
        """
        try:
            if isinstance(timestamp, str):
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_float = ts.timestamp()
            else:
                ts_float = float(timestamp)
        except (ValueError, TypeError):
            ts_float = time.time()

        # Add to history
        self.cpu_history.append((ts_float, cpu_percent))

        # Remove old data points outside the spike duration window
        cutoff_time = ts_float - self.cpu_spike_duration
        while self.cpu_history and self.cpu_history[0][0] < cutoff_time:
            self.cpu_history.popleft()

        # Check if all recent samples exceed threshold
        if len(self.cpu_history) < 3:  # Need at least 3 samples
            return None

        high_cpu_count = sum(
            1 for _, cpu in self.cpu_history if cpu >= self.cpu_spike_threshold
        )

        # All samples in the window should be above threshold
        if high_cpu_count == len(self.cpu_history):
            # Check cooldown
            alert_key = ("cpu_spike", "system")
            if self._is_in_cooldown(alert_key, ts_float):
                return None

            # Calculate average CPU
            avg_cpu = sum(cpu for _, cpu in self.cpu_history) / len(self.cpu_history)

            # Generate alert
            alert = {
                "rule_name": "Agent: Sustained High CPU Usage",
                "severity": "medium",
                "details": {
                    "average_cpu": round(avg_cpu, 2),
                    "threshold": self.cpu_spike_threshold,
                    "duration_seconds": int(ts_float - self.cpu_history[0][0]),
                    "sample_count": len(self.cpu_history),
                },
                "timestamp": timestamp or datetime.now().isoformat(),
                "agent_id": self.agent_id,
            }

            # Update cooldown
            self.alert_cooldown[alert_key] = ts_float

            # Store alert in SQLite
            self._store_alert(alert)

            print(f"[ALERT] CPU spike detected: {avg_cpu:.1f}% average")
            return alert

        return None

    def _is_in_cooldown(self, alert_key: tuple, current_time: float) -> bool:
        """
        Check if an alert is still in cooldown period.

        Args:
            alert_key: Tuple identifying the alert type and target
            current_time: Current timestamp

        Returns:
            True if in cooldown, False otherwise
        """
        if alert_key not in self.alert_cooldown:
            return False

        last_alert_time = self.alert_cooldown[alert_key]
        return (current_time - last_alert_time) < self.cooldown_period

    def _should_skip_alert(self, alert_key: tuple) -> bool:
        """
        Check if an alert should be skipped due to cooldown.
        
        Args:
            alert_key: Tuple identifying the alert type and target
            
        Returns:
            True if should skip (in cooldown), False otherwise
        """
        current_time = time.time()
        
        if alert_key not in self.alert_cooldown:
            # Not in cooldown, update timestamp and allow alert
            self.alert_cooldown[alert_key] = current_time
            return False
        
        last_alert_time = self.alert_cooldown[alert_key]
        if (current_time - last_alert_time) < self.cooldown_period:
            # Still in cooldown, skip alert
            return True
        
        # Cooldown expired, update timestamp and allow alert
        self.alert_cooldown[alert_key] = current_time
        return False

    def _store_alert(self, alert: dict):
        """
        Store alert in SQLite database.

        Args:
            alert: Alert dictionary
        """
        try:
            self.storage.store_alert(alert)
        except Exception as e:
            print(f"Failed to store alert in SQLite: {e}")

    def get_pending_alerts(self) -> list[dict]:
        """
        Retrieve alerts that haven't been forwarded to the server yet.

        Returns:
            List of alert dictionaries
        """
        try:
            return self.storage.get_pending_alerts()
        except Exception as e:
            print(f"Failed to retrieve pending alerts: {e}")
            return []

    def mark_alerts_forwarded(self, alert_ids: list[int]):
        """
        Mark alerts as forwarded to the server.

        Args:
            alert_ids: List of alert IDs to mark
        """
        try:
            self.storage.mark_alerts_forwarded(alert_ids)
        except Exception as e:
            print(f"Failed to mark alerts as forwarded: {e}")
    
    def analyze_command(self, command_data: dict):
        """
        Analyze a terminal command for suspicious patterns.
        
        Args:
            command_data: Command dictionary from CommandCollector
        """
        # Run command analysis rules
        alert = analyze_command(command_data)
        
        if alert:
            # Check cooldown to avoid duplicate alerts for same command
            command = command_data.get('command', '')
            alert_key = (alert['rule_name'], command[:50])  # Use first 50 chars as key
            
            if not self._should_skip_alert(alert_key):
                # Add agent_id and timestamp
                alert['timestamp'] = datetime.now().isoformat()
                alert['agent_id'] = self.agent_id
                
                # Store the alert
                self.storage.store_alert(alert)
                
                # Print concise alert (not full banner)
                severity_emoji = "🔴" if alert['severity'] == 'critical' else "🟠" if alert['severity'] == 'high' else "🟡"
                print(f"{severity_emoji} [{alert['severity'].upper()}] {alert['rule_name']}: {command[:60]}")
                
                # Update cooldown
                self.alert_cooldown[alert_key] = time.time()

