# aegis-agent/internal/forwarder/forwarder.py

import threading
import time
import requests
import json
from typing import List, Dict, Any

# This is the (default) URL of our FastAPI server's endpoint
SERVER_URL = "http://127.0.0.1:8000/api/ingest"
BATCH_SIZE = 100
FORWARD_INTERVAL_SECONDS = 30 # How often to check for new logs

class Forwarder:
    """
    Runs in a separate thread to forward logs from the local
    SQLite DB to the central server.
    """
    
    def __init__(self, storage, agent_id: str):
        """
        Initializes the Forwarder.
        
        Args:
            storage (Storage): The Storage instance for DB access.
            agent_id (str): The agent's unique UUID.
        """
        self.storage = storage
        self.agent_id = agent_id
        self.server_url = SERVER_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-Aegis-Agent-ID": self.agent_id
        }
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
                self.forward_batch()
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
        payload: List[Dict[str, Any]] = []
        log_ids_in_batch: List[int] = []
        
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
                self.server_url,
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