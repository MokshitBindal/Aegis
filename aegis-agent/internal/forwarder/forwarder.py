# aegis-agent/internal/forwarder/forwarder.py

import json
import threading
import time
from datetime import UTC
from typing import Any, Dict, List

import requests

BATCH_SIZE = 100
FORWARD_INTERVAL_SECONDS = 30 # How often to check for new logs

# Default server URL (used only if secure credentials are not available)
DEFAULT_SERVER_URL = "http://127.0.0.1:8000/api/ingest"

class Forwarder:
    """
    Runs in a separate thread to forward logs and metrics from the local
    SQLite DB to the central server.
    """
    
    def __init__(self, storage, agent_id: str | None = None, metrics_collector=None, analysis_engine=None, command_collector=None):
        """
        Initializes the Forwarder.
        
        Args:
            storage (Storage): The Storage instance for DB access.
            agent_id (str): The agent's unique UUID.
            metrics_collector (MetricsCollector): The metrics collector instance.
            analysis_engine (AnalysisEngine): The analysis engine instance.
            command_collector (CommandCollector): The command collector instance.
        """
        self.storage = storage
        self.analysis_engine = analysis_engine
        self.command_collector = command_collector
        # Try to load server URL and agent credentials from secure storage
        try:
            from internal.agent.credentials import load_credentials
            from internal.agent.id import get_agent_id
            creds = load_credentials()
            if not agent_id:
                agent_id = str(get_agent_id())
        except Exception:
            creds = None

        if creds:
            # Credentials contain server_url and agent_id
            server_base = creds.get("server_url")
            if server_base:
                # Ensure we point at the ingest path
                if server_base.endswith("/"):
                    self.server_url = server_base.rstrip("/") + "/api/ingest"
                else:
                    self.server_url = server_base + "/api/ingest"
            else:
                self.server_url = DEFAULT_SERVER_URL

            self.agent_id = str(creds.get("agent_id") or agent_id)
        else:
            self.server_url = DEFAULT_SERVER_URL
            self.agent_id = str(agent_id)

        # Base server URL without endpoint
        self.server_base = self.server_url.replace("/api/ingest", "")
        self.ingest_url = f"{self.server_base}/api/ingest"
        self.metrics_url = f"{self.server_base}/api/metrics"
        self.alerts_url = f"{self.server_base}/api/agent-alerts"
        self.commands_url = f"{self.server_base}/api/commands"
        self.status_url = f"{self.server_base}/api/device/status"

        if not self.agent_id:
            raise ValueError(
                "No agent_id available. Please ensure agent is registered."
            )

        self.headers = {
            "Content-Type": "application/json",
            "X-Aegis-Agent-ID": self.agent_id
        }

        # Set up metrics collector with agent_id
        if metrics_collector:
            metrics_collector.set_agent_id(self.agent_id)  # Use the new setter method
            try:
                metrics_collector.start()  # This will validate agent_id before starting
                print("Metrics collector started successfully")
            except ValueError as e:
                print(f"Failed to start metrics collector: {e}")
                metrics_collector = None
        self.metrics_collector = metrics_collector

        # This event is used to signal the thread to stop
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        print("Forwarder initialized.")

    def start(self):
        """Starts the forwarder thread and sends online status."""
        print("Forwarder thread starting...")
        # Send online status to server
        self.send_status("online")
        self.thread.start()

    def stop(self):
        """Signals the forwarder thread to stop and sends offline status."""
        print("Forwarder thread stopping...")
        # Send offline status to server
        self.send_status("offline")
        self.stop_event.set()
        self.thread.join() # Wait for the thread to finish
        print("Forwarder thread stopped.")

    def run(self):
        """
        The main loop for the forwarder thread.
        
        Wakes up every FORWARD_INTERVAL_SECONDS, checks for logs,
        and attempts to forward them.
        """
        print("Forwarder run loop started.")
        while not self.stop_event.is_set():
            try:
                # Forward logs
                self.forward_batch()
                
                # Forward metrics if available
                if self.metrics_collector:
                    self.forward_metrics()
                
                # Forward alerts if analysis engine is available
                if self.analysis_engine:
                    self.forward_alerts()
                
                # Forward commands if available
                self.forward_commands()
                
                # Forward processes
                self.forward_processes()
            except Exception as e:
                print(f"Error in forwarder run loop: {e}")

            # Wait for the next interval, but check self.stop_event
            # frequently so we can shut down quickly.
            self.stop_event.wait(FORWARD_INTERVAL_SECONDS)
        
        print("Forwarder run loop finished.")

    def forward_batch(self):
        """
        Fetches one batch of unforwarded logs and attempts to send them.
        """
        # 1. Get logs from local DB
        logs_to_forward = self.storage.get_unforwarded_logs(BATCH_SIZE)
        
        if not logs_to_forward:
            # print("No logs to forward.")
            return

        print(f"Found {len(logs_to_forward)} logs to forward.")
        
        # 2. Prepare the payload in the format the server expects
        # (List[LogEntry] model)
        payload: list[dict[str, Any]] = []
        log_ids_in_batch: list[int] = []
        
        for log in logs_to_forward:
            payload.append({
                "timestamp": log['timestamp'],
                "hostname": log['hostname'],
                "message": log['message'],
                "raw_json": log['raw_json']
            })
            log_ids_in_batch.append(log['id'])

        # 3. Attempt to send the logs to the server
        try:
            response = requests.post(
                self.ingest_url,
                data=json.dumps(payload),
                headers=self.headers,
                timeout=10 # 10-second timeout
            )
            
            # 4. Handle response
            if response.status_code == 200:
                # SUCCESS!
                print(f"Successfully forwarded batch of {len(log_ids_in_batch)} logs.")
                # Mark them as forwarded in local DB
                self.storage.mark_logs_as_forwarded(log_ids_in_batch)
            else:
                # Server returned an error
                print(f"Server error: {response.status_code}. Failed to forward batch.")
                print(f"Response: {response.text}")

        except requests.exceptions.RequestException as e:
            # Network error (server down, no connection, etc.)
            # We DON'T mark as forwarded. We'll retry on the next loop.
            print(f"Network error while forwarding: {e}")

    def forward_metrics(self):
        """
        Forwards the latest metrics to the server
        """
        if not self.metrics_collector:
            return

        try:
            # Get latest metrics
            metrics = self.metrics_collector._latest_metrics
            if not metrics:
                return

            # Build payload using native Python types so FastAPI/Pydantic
            # receives proper objects (not stringified JSON). Convert the
            # timestamp (epoch float) to ISO8601 so it will be parsed into
            # a datetime on the server side.
            from datetime import datetime, timezone

            ts = metrics.get("timestamp")
            if isinstance(ts, int | float):
                timestamp_iso = datetime.fromtimestamp(ts, tz=UTC).isoformat()
            else:
                # Assume it's already an ISO string or datetime-like object
                timestamp_iso = ts

            payload = {
                "agent_id": str(metrics.get("agent_id")),
                "timestamp": timestamp_iso,
                "cpu": metrics.get("cpu", {}),
                "memory": metrics.get("memory", {}),
                "disk": metrics.get("disk", {}),
                "network": metrics.get("network", {}),
                "process": metrics.get("process", {})
            }

            # Send metrics to server using json= so requests will encode the
            # payload to proper JSON objects (not string values for nested
            # structures).
            response = requests.post(
                self.metrics_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                print("Successfully forwarded metrics")
            else:
                print(
                    f"Failed to forward metrics: "
                    f"{response.status_code} {response.text}"
                )

        except Exception as e:
            print(f"Error forwarding metrics: {e}")

    def forward_alerts(self):
        """
        Forwards agent-generated alerts to the server
        """
        if not self.analysis_engine:
            return

        try:
            # Get pending alerts from storage
            alerts = self.analysis_engine.get_pending_alerts()
            if not alerts:
                return

            print(f"Found {len(alerts)} alerts to forward")

            # Prepare payload - list of alerts
            payload = []
            alert_ids = []

            for alert in alerts:
                payload.append({
                    "rule_name": alert.get("rule_name"),
                    "severity": alert.get("severity"),
                    "details": alert.get("details", {}),
                    "timestamp": alert.get("timestamp"),
                    "agent_id": alert.get("agent_id"),
                })
                alert_ids.append(alert["id"])

            # Send to server
            response = requests.post(
                self.alerts_url, json=payload, headers=self.headers, timeout=10
            )

            if response.status_code == 200:
                print(f"Successfully forwarded {len(alerts)} alerts")
                # Mark as forwarded in local DB
                self.analysis_engine.mark_alerts_forwarded(alert_ids)
            else:
                print(
                    f"Failed to forward alerts: "
                    f"{response.status_code} {response.text}"
                )

        except Exception as e:
            print(f"Error forwarding alerts: {e}")
    
    def forward_commands(self):
        """
        Forwards pending commands to the server.
        """
        try:
            # Get pending commands from storage
            commands = self.storage.get_pending_commands(batch_size=50)
            
            if not commands:
                return
            
            print(f"Found {len(commands)} commands to forward")
            
            # Prepare payload
            payload = []
            command_ids = []
            
            for cmd in commands:
                payload.append({
                    "command": cmd.get("command"),
                    "user": cmd.get("user"),
                    "timestamp": cmd.get("timestamp"),
                    "shell": cmd.get("shell"),
                    "source": cmd.get("source"),
                    "working_directory": cmd.get("working_directory"),
                    "exit_code": cmd.get("exit_code"),
                    "agent_id": cmd.get("agent_id"),
                })
                command_ids.append(cmd["id"])
            
            # Send to server (we'll create this endpoint next)
            commands_url = self.server_url.replace("/ingest", "/commands")
            response = requests.post(
                commands_url, json=payload, headers=self.headers, timeout=10
            )
            
            if response.status_code == 200:
                print(f"Successfully forwarded {len(commands)} commands")
                # Mark as forwarded
                self.storage.mark_commands_forwarded(command_ids)
            else:
                print(
                    f"Failed to forward commands: "
                    f"{response.status_code} {response.text}"
                )
        except Exception as e:
            print(f"Error forwarding commands: {e}")
    def forward_processes(self):
        """
        Forwards pending process data to the server.
        """
        try:
            # Get pending processes from storage
            processes = self.storage.get_pending_processes(batch_size=100)
            
            if not processes:
                return
            
            print(f"Found {len(processes)} processes to forward")
            
            # Prepare payload
            payload = []
            process_ids = []
            
            for proc in processes:
                payload.append({
                    "pid": proc.get("pid"),
                    "name": proc.get("name"),
                    "exe": proc.get("exe"),
                    "cmdline": proc.get("cmdline"),
                    "username": proc.get("username"),
                    "status": proc.get("status"),
                    "create_time": proc.get("create_time"),
                    "ppid": proc.get("ppid"),
                    "cpu_percent": proc.get("cpu_percent"),
                    "memory_percent": proc.get("memory_percent"),
                    "memory_rss": proc.get("memory_rss"),
                    "memory_vms": proc.get("memory_vms"),
                    "num_threads": proc.get("num_threads"),
                    "num_fds": proc.get("num_fds"),
                    "num_connections": proc.get("num_connections"),
                    "connection_details": proc.get("connection_details", []),
                    "agent_id": proc.get("agent_id"),
                    "collected_at": proc.get("collected_at"),
                })
                process_ids.append(proc["id"])
            
            # Send to server
            processes_url = f"{self.server_base}/api/processes"
            response = requests.post(
                processes_url, json=payload, headers=self.headers, timeout=10
            )
            
            if response.status_code == 200:
                print(f"Successfully forwarded {len(processes)} processes")
                # Mark as forwarded
                self.storage.mark_processes_forwarded(process_ids)
            else:
                print(
                    f"Failed to forward processes: "
                    f"{response.status_code} {response.text}"
                )
        except Exception as e:
            print(f"Error forwarding processes: {e}")
    
    def send_status(self, status: str):
        """
        Sends agent status (online/offline) to the server.
        
        Args:
            status: Either "online" or "offline"
        """
        try:
            payload = {
                "agent_id": self.agent_id,
                "status": status
            }
            
            response = requests.post(
                self.status_url,
                json=payload,
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"Agent status updated to: {status}")
            else:
                print(f"Failed to update status: {response.status_code}")
        except Exception as e:
            print(f"Error sending status update: {e}")
