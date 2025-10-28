"""
System metrics collector for the Aegis agent.
Collects CPU, Memory, Disk, and Network metrics.
"""

import threading
import time
from typing import Any

import psutil


class MetricsCollector:
    def __init__(self, interval: int = 60, agent_id: str | None = None):
        """
        Initialize the metrics collector.
        
        Args:
            interval: Collection interval in seconds (default: 60)
            agent_id: The agent's unique identifier
        """
        self.interval = interval
        self.agent_id = str(agent_id) if agent_id else None
        self._stop_event = threading.Event()
        self._latest_metrics = {}
        self._collection_thread = None  # Thread reference for better control
        
    def collect_cpu_metrics(self) -> dict[str, Any]:
        """Collect CPU-related metrics"""
        # Convert tuple to list for JSON serialization
        load_avg = list(psutil.getloadavg())
        return {
            "cpu_percent": float(psutil.cpu_percent(interval=1)),
            "cpu_count": int(psutil.cpu_count()),
            "load_avg": load_avg
        }
    
    def collect_memory_metrics(self) -> dict[str, Any]:
        """Collect memory-related metrics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "memory_total": int(mem.total),
            "memory_available": int(mem.available),
            "memory_percent": float(mem.percent),
            "swap_total": int(swap.total),
            "swap_used": int(swap.used),
            "swap_percent": float(swap.percent)
        }
    
    def collect_disk_metrics(self) -> dict[str, Any]:
        """Collect disk-related metrics"""
        disk = psutil.disk_usage('/')
        io = psutil.disk_io_counters()
        return {
            "disk_total": int(disk.total),
            "disk_used": int(disk.used),
            "disk_free": int(disk.free),
            "disk_percent": float(disk.percent),
            "disk_read_bytes": int(io.read_bytes if io else 0),
            "disk_write_bytes": int(io.write_bytes if io else 0)
        }
    
    def collect_network_metrics(self) -> dict[str, Any]:
        """Collect network-related metrics"""
        net = psutil.net_io_counters()
        return {
            "net_bytes_sent": int(net.bytes_sent),
            "net_bytes_recv": int(net.bytes_recv),
            "net_packets_sent": int(net.packets_sent),
            "net_packets_recv": int(net.packets_recv)
        }

    def collect_process_metrics(self) -> dict[str, Any]:
        """Collect process-related metrics"""
        return {
            "process_count": int(len(psutil.pids())),
            "thread_count": int(threading.active_count())
        }

    def collect_all_metrics(self) -> dict[str, Any]:
        """Collect all system metrics"""
        if not self.agent_id:
            raise ValueError("agent_id not set in MetricsCollector")

        try:
            # Collect all metrics first to ensure we have everything
            cpu_metrics = self.collect_cpu_metrics()
            memory_metrics = self.collect_memory_metrics()
            disk_metrics = self.collect_disk_metrics()
            network_metrics = self.collect_network_metrics()
            process_metrics = self.collect_process_metrics()

            # Only update _latest_metrics if all collections succeeded
            metrics = {
                "timestamp": time.time(),
                "agent_id": str(self.agent_id),
                "cpu": cpu_metrics,
                "memory": memory_metrics,
                "disk": disk_metrics,
                "network": network_metrics,
                "process": process_metrics
            }
            
            self._latest_metrics = metrics
            return metrics
        except Exception as e:
            print(f"Error collecting metrics: {e}")
            if not self._latest_metrics:
                # Initialize with empty data if we have no previous metrics
                self._latest_metrics = {
                    "timestamp": time.time(),
                    "agent_id": str(self.agent_id),
                    "cpu": {
                        "cpu_percent": 0,
                        "cpu_count": 0,
                        "load_avg": [0, 0, 0],
                    },
                    "memory": {
                        "memory_total": 0,
                        "memory_available": 0,
                        "memory_percent": 0,
                    },
                    "disk": {
                        "disk_total": 0,
                        "disk_free": 0,
                        "disk_percent": 0,
                    },
                    "network": {"net_bytes_sent": 0, "net_bytes_recv": 0},
                    "process": {"process_count": 0, "thread_count": 0},
                }
            return self._latest_metrics

    def run(self):
        """Run the metrics collection loop"""
        print(f"Starting metrics collection for agent {self.agent_id}...")
        while not self._stop_event.is_set():
            try:
                metrics = self.collect_all_metrics()
                if metrics and 'cpu' in metrics:
                    print(f"Collected metrics: CPU {metrics['cpu']['cpu_percent']}%, "
                          f"Memory {metrics['memory']['memory_percent']}%, "
                          f"Disk {metrics['disk']['disk_percent']}%")
                else:
                    print("Failed to collect complete metrics")
            except Exception as e:
                print(f"Error in metrics collection loop: {e}")
            self._stop_event.wait(self.interval)

    def set_agent_id(self, agent_id: str):
        """Set or update the agent ID"""
        self.agent_id = str(agent_id) if agent_id else None

    def start(self):
        """Start the metrics collection thread"""
        if not self.agent_id:
            raise ValueError("Cannot start metrics collection without an agent_id")
            
        if self._collection_thread and self._collection_thread.is_alive():
            print("Metrics collector already running")
            return self._collection_thread
            
        self._collection_thread = threading.Thread(target=self.run, daemon=True)
        self._collection_thread.start()
        return self._collection_thread

    def stop(self):
        """Stop the metrics collection"""
        self._stop_event.set()