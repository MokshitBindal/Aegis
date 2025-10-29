# aegis-agent/internal/collector/journald_linux.py

import datetime
import json
import time

import systemd.journal

# Define the agent's own service name to ignore
AGENT_SERVICE_NAME = "aegis-agent.service"


class JournaldCollector:
    def __init__(self, storage, analysis_engine=None):
        print("JournaldCollector initialized.")
        self.storage = storage
        self.analysis_engine = analysis_engine
        self.reader = None

    def run(self):
        print("Collector thread started. Opening journal...")
        try:
            self.reader = systemd.journal.Reader()
            print("Seeking to journal tail...")
            self.reader.seek_tail()
            self.reader.get_previous()
            print("Journal opened. Tailing for new log entries...")

            while True:
                event = self.reader.wait()
                if event == systemd.journal.APPEND:
                    for entry in self.reader:
                        self.process_entry(entry)

        except PermissionError:
            print("\nCRITICAL ERROR: Permission denied.")
            print("Could not read system journal. Please run the agent with 'sudo'.")
        except Exception as e:
            print(f"Error in JournaldCollector run loop: {e}")
            time.sleep(10)

    def process_entry(self, entry):
        """
        Processes a single log entry, writes it to storage,
        and checks it against local analysis rules.
        """
        try:
            # --- FIX: Check if the log is from the agent itself ---
            # The '_SYSTEMD_UNIT' field tells us which service generated the log.
            # We must decode it if it's bytes.
            unit = entry.get("_SYSTEMD_UNIT")
            if isinstance(unit, bytes):
                unit = unit.decode('utf-8', 'replace')

            if unit == AGENT_SERVICE_NAME:
                # Skip processing this entry entirely
                return

            # --- If it's not our own log, proceed as before ---
            entry_dict = {}
            for key, val in entry.items():
                if isinstance(val, bytes):
                    val_str = val.decode('utf-8', 'replace')
                else:
                    val_str = str(val)
                entry_dict[key] = val_str

            message = entry_dict.get("MESSAGE", "N/A")
            hostname = entry_dict.get("_HOSTNAME", "N/A")

            if "__REALTIME_TIMESTAMP" in entry:
                timestamp = entry["__REALTIME_TIMESTAMP"]
            else:
                timestamp = datetime.datetime.now(datetime.UTC)

            log_data = {
                "timestamp": timestamp,
                "hostname": hostname,
                "message": message,
                "raw_json": json.dumps(entry_dict, default=str),
                "raw_data": entry_dict,  # Add parsed dict for analysis
            }

            self.storage.write_log(log_data)
            # Shorten the print message to reduce log spam further
            print(f"[Stored] {hostname}: {message[:60]}...")

            # Run analysis engine if available
            if self.analysis_engine:
                alerts = self.analysis_engine.analyze_log(log_data)
                for alert in alerts:
                    print(f"[ALERT GENERATED] {alert['rule_name']}")

        except Exception as e:
            print(f"Error processing entry: {e}")

