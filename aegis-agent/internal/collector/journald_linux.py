# aegis-agent/internal/collector/journald_linux.py

import systemd.journal
import json
import time
import datetime 
# We no longer need to print, so we can remove some of the
# "print()" spam from the process_entry method.

class JournaldCollector:
    
    def __init__(self, storage): # <--- MODIFICATION: Accept storage object
        """
        Initializes the JournaldCollector.
        
        Args:
            storage (Storage): The SQLite storage instance.
        """
        print("JournaldCollector initialized.")
        self.storage = storage # <--- MODIFICATION: Save storage object
        self.reader = None

    def run(self):
        """
        Starts the log collection loop.
        This method is designed to be run in a separate thread.
        """
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
            print("e.g.,: sudo venv/bin/python main.py run\n")
        except Exception as e:
            print(f"Error in JournaldCollector run loop: {e}")
            time.sleep(10)

    def process_entry(self, entry):
        """
        Processes a single log entry and writes it to storage.
        
        Args:
            entry (systemd.journal.Entry): A dict-like journal entry.
        """
        
        entry_dict = {}
        try:
            # Decode all fields into a plain dict
            for key, val in entry.items():
                if isinstance(val, bytes):
                    val_str = val.decode('utf-8', 'replace')
                else:
                    val_str = str(val)
                entry_dict[key] = val_str

            # --- MODIFICATION: Prepare data and write to DB ---
            
            # Get the key fields
            message = entry_dict.get("MESSAGE", "N/A")
            hostname = entry_dict.get("_HOSTNAME", "N/A")
            
            if "__REALTIME_TIMESTAMP" in entry:
                timestamp = entry["__REALTIME_TIMESTAMP"]
            else:
                timestamp = datetime.datetime.now(datetime.timezone.utc)
            
            # This is the data object our storage class expects
            log_data = {
                "timestamp": timestamp,
                "hostname": hostname,
                "message": message,
                "raw_json": json.dumps(entry_dict, default=str)
            }
            
            # Write it to the database!
            self.storage.write_log(log_data)
            
            # We can print a small confirmation
            print(f"[LOG STORED] Host: {hostname}, Msg: {message[:50]}...")

        except Exception as e:
            print(f"Error processing entry: {e}")