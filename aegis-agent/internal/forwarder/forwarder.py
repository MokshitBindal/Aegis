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
    
    def __init__(self, storage, agent_id: str | None = None, metrics_collector=None):
        """
        Initializes the Forwarder.
        
        Args:
            storage (Storage): The Storage instance for DB access.
            agent_id (str): The agent's unique UUID.
            metrics_collector (MetricsCollector): The metrics collector instance.
        """
        self.storage = storage
        # Try to load server URL and agent credentials from secure storage
        # Try to load server URL and agent credentials from secure storage
        try:
            from internal.agent.credentials import load_credentials
            from internal.agent.id import get_agent_id
            creds = load_credentials()
            if not agent_id:
                agent_id = str(get_agent_id())
        except Exception:
            creds = None
        try:
            from internal.agent.credentials import load_credentials
            creds = load_credentials()
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
        """Starts the forwarder thread."""
        print("Forwarder thread starting...")
        self.thread.start()

    def stop(self):
        """Signals the forwarder thread to stop."""
        print("Forwarder thread stopping...")
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