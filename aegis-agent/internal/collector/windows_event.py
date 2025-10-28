import time
import platform
from datetime import datetime


class WindowsEventCollector:
    """
    Collects Windows Event Log entries using pywin32 (win32evtlog).

    This implementation only runs on Windows and expects the package
    `pywin32` to be installed. It's safe to import this module only
    on Windows systems (the agent imports collectors conditionally).
    """

    def __init__(self, storage):
        print("WindowsEventCollector initialized.")
        self.storage = storage
        self.hostname = platform.node()

    def run(self):
        print("WindowsEventCollector run loop started.")
        try:
            import win32evtlog
        except Exception as e:
            print(f"pywin32 not available or import failed: {e}")
            return

        server = 'localhost'
        logtype = 'System'  # Can also be 'Application' or 'Security'

        while True:
            try:
                hand = win32evtlog.OpenEventLog(server, logtype)
                flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

                events = True
                while events:
                    events = win32evtlog.ReadEventLog(hand, flags, 0)
                    if not events:
                        break
                    for ev_obj in events:
                        try:
                            time_gen = ev_obj.TimeGenerated
                            timestamp = datetime.fromtimestamp(time.mktime(time_gen.timetuple()))
                        except Exception:
                            timestamp = datetime.utcnow()

                        source = getattr(ev_obj, 'SourceName', 'WindowsEvent')
                        strings = ev_obj.StringInserts
                        if strings:
                            message = ' '.join([str(s) for s in strings])
                        else:
                            message = f"EventID={getattr(ev_obj, 'EventID', 'N/A')}"

                        log_data = {
                            'timestamp': timestamp,
                            'hostname': self.hostname,
                            'message': f"[{source}] {message}",
                            'raw_json': str({
                                'EventID': getattr(ev_obj, 'EventID', None),
                                'Source': source,
                                'RecordNumber': getattr(ev_obj, 'RecordNumber', None)
                            })
                        }

                        try:
                            self.storage.write_log(log_data)
                        except Exception as e:
                            print(f"Failed to write Windows event to storage: {e}")

                win32evtlog.CloseEventLog(hand)

            except Exception as e:
                print(f"Error reading Windows Event Log: {e}")
                time.sleep(5)

            # Prevent tight loop if there are no new events
            time.sleep(2)