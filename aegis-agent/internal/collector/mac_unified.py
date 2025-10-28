import subprocess
import shlex
import time
import platform
from datetime import datetime


class MacUnifiedLogCollector:
    """
    Basic macOS Unified Logging collector using the `log stream` command.

    This is a simple implementation that spawns `log stream --style syslog`
    and reads lines from stdout. It's best-effort and intended as a
    cross-platform-stub that works when run on macOS.
    """

    def __init__(self, storage):
        print("MacUnifiedLogCollector initialized.")
        self.storage = storage
        self.hostname = platform.node()

    def run(self):
        print("MacUnifiedLogCollector run loop started.")

        cmd = ['log', 'stream', '--style', 'syslog']
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            print("macOS 'log' command not found. Ensure running on macOS 10.12+.")
            return
        except Exception as e:
            print(f"Failed to start 'log stream': {e}")
            return

        try:
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if not line:
                    continue

                # Very simple parsing: split timestamp and message when possible
                # Example syslog style: "Oct 28 10:00:00 hostname process[pid]: message..."
                try:
                    parts = line.split(' ', 4)
                    # If we have a recognizable timestamp-like prefix, try to build one
                    if len(parts) >= 5:
                        timestamp_str = ' '.join(parts[0:3])
                        message = parts[4]
                        timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()
                        message = line
                except Exception:
                    timestamp = datetime.utcnow()
                    message = line

                log_data = {
                    'timestamp': timestamp,
                    'hostname': self.hostname,
                    'message': message,
                    'raw_json': line
                }

                try:
                    self.storage.write_log(log_data)
                except Exception as e:
                    print(f"Failed to write macOS log to storage: {e}")

        except Exception as e:
            print(f"Error reading from 'log stream': {e}")
        finally:
            try:
                proc.terminate()
            except Exception:
                pass