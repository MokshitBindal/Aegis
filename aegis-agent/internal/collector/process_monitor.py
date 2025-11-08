"""
Process Monitoring Collector for Aegis Agent

This module collects detailed process information including:
- Running process inventory
- Process lifecycle events (creation/termination)
- Resource usage per process (CPU, memory)
- Network connections per process
- Parent-child process relationships

Data is used for AI/ML behavioral anomaly detection.
"""

import psutil
import time
from datetime import datetime
from typing import List, Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ProcessMonitor:
    """
    Monitors system processes and collects detailed information for security analysis.
    """

    def __init__(self):
        """Initialize the process monitor."""
        self.previous_pids: Set[int] = set()
        self.process_cache: Dict[int, Dict] = {}
        self.collection_interval = 60  # seconds
        logger.info("Process monitor initialized")

    def get_process_info(self, proc: psutil.Process) -> Optional[Dict]:
        """
        Extract detailed information from a process.

        Args:
            proc: psutil.Process object

        Returns:
            Dictionary with process information or None if access denied
        """
        try:
            with proc.oneshot():
                # Get process info
                pinfo = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'exe': proc.exe() if proc.exe() else None,
                    'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else '',
                    'username': proc.username(),
                    'status': proc.status(),
                    'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                    'ppid': proc.ppid(),
                    
                    # Resource usage
                    'cpu_percent': proc.cpu_percent(interval=0.1),
                    'memory_percent': proc.memory_percent(),
                    'memory_rss': proc.memory_info().rss,
                    'memory_vms': proc.memory_info().vms,
                    
                    # Process details
                    'num_threads': proc.num_threads(),
                    'num_fds': proc.num_fds() if hasattr(proc, 'num_fds') else 0,
                    
                    # Connection count
                    'num_connections': 0,
                    'connection_details': []
                }

                # Get network connections
                try:
                    connections = proc.net_connections(kind='inet')
                    pinfo['num_connections'] = len(connections)
                    
                    # Store connection details (limit to 10 to avoid huge payloads)
                    pinfo['connection_details'] = [
                        {
                            'family': conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                            'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                            'laddr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                            'raddr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                            'status': conn.status
                        }
                        for conn in connections[:10]  # Limit to first 10 connections
                    ]
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                return pinfo

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.debug(f"Could not access process {proc.pid}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error collecting process info for PID {proc.pid}: {e}")
            return None

    def collect_running_processes(self) -> List[Dict]:
        """
        Collect information about all currently running processes.

        Returns:
            List of dictionaries containing process information
        """
        processes = []
        current_pids = set()
        
        logger.info("Starting process collection...")
        start_time = time.time()

        for proc in psutil.process_iter(['pid']):
            try:
                pid = proc.pid
                current_pids.add(pid)
                
                # Get detailed process info
                pinfo = self.get_process_info(proc)
                if pinfo:
                    processes.append(pinfo)
                    self.process_cache[pid] = pinfo

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.warning(f"Error processing PID {proc.pid}: {e}")
                continue

        # Detect new and terminated processes
        new_pids = current_pids - self.previous_pids
        terminated_pids = self.previous_pids - current_pids

        if new_pids:
            logger.info(f"Detected {len(new_pids)} new processes: {list(new_pids)[:10]}")
        if terminated_pids:
            logger.info(f"Detected {len(terminated_pids)} terminated processes: {list(terminated_pids)[:10]}")

        # Update previous PIDs
        self.previous_pids = current_pids

        elapsed = time.time() - start_time
        logger.info(f"Collected {len(processes)} processes in {elapsed:.2f}s")

        return processes

    def get_process_tree(self) -> Dict:
        """
        Build a process tree showing parent-child relationships.

        Returns:
            Dictionary representing the process tree
        """
        tree = {}
        orphans = []

        for pid, pinfo in self.process_cache.items():
            ppid = pinfo.get('ppid', 0)
            
            if ppid == 0:
                # Root process (init/systemd)
                if 'children' not in tree:
                    tree['root'] = {'pid': pid, 'name': pinfo.get('name'), 'children': []}
                continue
            
            # Add to parent's children list
            parent = self.process_cache.get(ppid)
            if parent:
                if 'children' not in tree.get(ppid, {}):
                    tree[ppid] = {'pid': ppid, 'name': parent.get('name'), 'children': []}
                tree[ppid]['children'].append({
                    'pid': pid,
                    'name': pinfo.get('name'),
                    'username': pinfo.get('username')
                })
            else:
                orphans.append(pid)

        if orphans:
            logger.debug(f"Found {len(orphans)} orphan processes")

        return tree

    def detect_anomalies(self, processes: List[Dict]) -> List[Dict]:
        """
        Detect suspicious process patterns.

        Args:
            processes: List of process information dictionaries

        Returns:
            List of detected anomalies
        """
        anomalies = []

        for proc in processes:
            # High CPU usage (>80% sustained)
            if proc.get('cpu_percent', 0) > 80:
                anomalies.append({
                    'type': 'high_cpu',
                    'pid': proc['pid'],
                    'name': proc['name'],
                    'cpu_percent': proc['cpu_percent'],
                    'severity': 'medium'
                })

            # High memory usage (>80%)
            if proc.get('memory_percent', 0) > 80:
                anomalies.append({
                    'type': 'high_memory',
                    'pid': proc['pid'],
                    'name': proc['name'],
                    'memory_percent': proc['memory_percent'],
                    'severity': 'medium'
                })

            # Suspicious process names (common malware patterns)
            suspicious_names = ['xmrig', 'minerd', 'cpuminer', 'ethminer']
            if proc.get('name', '').lower() in suspicious_names:
                anomalies.append({
                    'type': 'suspicious_process_name',
                    'pid': proc['pid'],
                    'name': proc['name'],
                    'cmdline': proc.get('cmdline', ''),
                    'severity': 'high'
                })

            # Process with many network connections (>50)
            if proc.get('num_connections', 0) > 50:
                anomalies.append({
                    'type': 'high_network_activity',
                    'pid': proc['pid'],
                    'name': proc['name'],
                    'num_connections': proc['num_connections'],
                    'severity': 'medium'
                })

        if anomalies:
            logger.warning(f"Detected {len(anomalies)} process anomalies")

        return anomalies

    def get_system_process_summary(self) -> Dict:
        """
        Get a summary of system-wide process metrics.

        Returns:
            Dictionary with aggregated process statistics
        """
        total_processes = len(self.process_cache)
        total_threads = sum(p.get('num_threads', 0) for p in self.process_cache.values())
        total_connections = sum(p.get('num_connections', 0) for p in self.process_cache.values())
        
        # Group by user
        user_process_count = {}
        for proc in self.process_cache.values():
            user = proc.get('username', 'unknown')
            user_process_count[user] = user_process_count.get(user, 0) + 1

        return {
            'total_processes': total_processes,
            'total_threads': total_threads,
            'total_connections': total_connections,
            'processes_by_user': user_process_count,
            'timestamp': datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()
        }


def main():
    """Test the process monitor."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    monitor = ProcessMonitor()
    
    # Collect processes
    processes = monitor.collect_running_processes()
    print(f"\n✅ Collected {len(processes)} processes")
    
    # Show sample processes
    print("\n📊 Sample processes:")
    for proc in processes[:5]:
        print(f"  - {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']:.1f}%, MEM: {proc['memory_percent']:.1f}%)")
    
    # Detect anomalies
    anomalies = monitor.detect_anomalies(processes)
    if anomalies:
        print(f"\n⚠️  Detected {len(anomalies)} anomalies:")
        for anomaly in anomalies:
            print(f"  - {anomaly['type']}: {anomaly.get('name')} (PID: {anomaly.get('pid')})")
    else:
        print("\n✅ No anomalies detected")
    
    # System summary
    summary = monitor.get_system_process_summary()
    print(f"\n📈 System Summary:")
    print(f"  - Total processes: {summary['total_processes']}")
    print(f"  - Total threads: {summary['total_threads']}")
    print(f"  - Total connections: {summary['total_connections']}")
    print(f"  - Top users: {dict(list(summary['processes_by_user'].items())[:5])}")


if __name__ == '__main__':
    main()
