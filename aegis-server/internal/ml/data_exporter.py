"""
Data Exporter for ML Training

Automatically exports data to files when thresholds are reached.
This helps collect training datasets for the Isolation Forest model.

Default export directory: ./ml_data (relative to server directory)
For production: Use /var/lib/aegis/ml_data with proper permissions

Author: Mokshit Bindal
Date: November 13, 2025
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Export system data to files for ML training.
    
    Monitors data ingestion and automatically exports when thresholds are reached:
    - Logs: 5,000 entries
    - Metrics: 1,000 samples
    - Processes: 500 snapshots
    - Commands: 1,000 commands
    """
    
    def __init__(self, pool: asyncpg.Pool, export_dir: str = "./ml_data"):
        self.pool = pool
        self.export_dir = Path(export_dir).resolve()
        try:
            self.export_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to local directory if we can't write to /var/lib/aegis
            logger.warning(f"Permission denied for {export_dir}, using ./ml_data instead")
            self.export_dir = Path("./ml_data").resolve()
            self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Thresholds for export
        self.thresholds = {
            "logs": 5000,
            "metrics": 1000,
            "processes": 500,
            "commands": 1000,
        }
        
        # Track last export counts
        self.last_export_counts = {
            "logs": 0,
            "metrics": 0,
            "processes": 0,
            "commands": 0,
        }
        
        # Track last export time
        self.last_export_time = None
        
        # Auto-delete from live view after export (keeps in files for admin download)
        self.auto_cleanup = True
        
        # Keep minimum records in live view
        self.min_live_records = {
            "logs": 1000,
            "metrics": 200,
            "processes": 100,
            "commands": 200,
        }
        
        logger.info(f"Data exporter initialized. Export directory: {self.export_dir}")
    
    async def check_and_export(self, force: bool = False):
        """
        Check all data types and export if thresholds are exceeded.
        This should be called periodically (e.g., every 5 minutes).
        
        Args:
            force: If True, export regardless of thresholds
        
        Returns:
            Dict with counts of exported items
        """
        try:
            result = {}
            result['logs'] = await self._check_and_export_logs(force)
            result['metrics'] = await self._check_and_export_metrics(force)
            result['processes'] = await self._check_and_export_processes(force)
            result['commands'] = await self._check_and_export_commands(force)
            
            # Update last export time
            self.last_export_time = datetime.now(timezone.utc)
            
            return result
        except Exception as e:
            logger.error(f"Error in data export check: {e}")
            raise
    
    async def _check_and_export_logs(self, force: bool = False):
        """
        Export logs if threshold exceeded
        
        Args:
            force: If True, export regardless of threshold
            
        Returns:
            Number of logs exported
        """
        async with self.pool.acquire() as conn:
            # Get total log count
            result = await conn.fetchrow("SELECT COUNT(*) as count FROM logs")
            total_count = result['count']
            
            new_logs = total_count - self.last_export_counts['logs']
            
            if force or new_logs >= self.thresholds['logs']:
                logger.info(f"Exporting {new_logs} new logs (threshold: {self.thresholds['logs']}, force: {force})")
                
                # Fetch logs (get the oldest ones first)
                logs = await conn.fetch(
                    """
                    SELECT id, timestamp, agent_id, hostname, raw_json
                    FROM logs
                    ORDER BY id
                    LIMIT $1
                    """,
                    max(new_logs, self.thresholds['logs']) if force else self.thresholds['logs']
                )
                
                if logs:
                    # Export to file
                    export_path = await self._export_logs_to_file(logs)
                    self.last_export_counts['logs'] = total_count
                    
                    # Auto-cleanup: Delete exported logs from live view (keep minimum)
                    if self.auto_cleanup and total_count > self.min_live_records['logs']:
                        max_id_to_delete = logs[-1]['id']
                        # Keep at least min_live_records recent logs
                        min_id_to_keep = await conn.fetchval(
                            """
                            SELECT id FROM logs
                            ORDER BY id DESC
                            LIMIT 1 OFFSET $1
                            """,
                            self.min_live_records['logs'] - 1
                        )
                        
                        if min_id_to_keep and max_id_to_delete < min_id_to_keep:
                            deleted = await conn.execute(
                                "DELETE FROM logs WHERE id <= $1",
                                max_id_to_delete
                            )
                            logger.info(f"Cleaned up {deleted} old logs from live view (exported to {export_path})")
                    
                    return len(logs)
            
            return 0
    
    async def _check_and_export_metrics(self, force: bool = False):
        """
        Export system metrics if threshold exceeded or forced
        
        Args:
            force: Force export regardless of threshold
        
        Returns:
            Number of metrics exported
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT COUNT(*) as count FROM system_metrics")
            total_count = result['count']
            
            new_metrics = total_count - self.last_export_counts['metrics']
            
            if force or new_metrics >= self.thresholds['metrics']:
                logger.info(f"Exporting {new_metrics} new metrics (threshold: {self.thresholds['metrics']}, force={force})")
                
                metrics = await conn.fetch(
                    """
                    SELECT id, agent_id, data, collected_at
                    FROM system_metrics
                    WHERE id > (
                        SELECT COALESCE(MAX(last_exported_id), 0)
                        FROM export_tracking
                        WHERE data_type = 'metrics'
                    )
                    ORDER BY id
                    LIMIT $1
                    """,
                    self.thresholds['metrics'] if not force else 999999
                )
                
                if metrics:
                    export_path = await self._export_metrics_to_file(metrics)
                    self.last_export_counts['metrics'] = total_count
                    await self._update_export_tracking('metrics', metrics[-1]['id'], len(metrics))
                    
                    # Auto-cleanup: Delete exported metrics from live view (keep minimum)
                    if self.auto_cleanup and total_count > self.min_live_records['metrics']:
                        # Get ID of the record at position min_live_records from the end
                        min_id_to_keep = await conn.fetchval(
                            "SELECT id FROM system_metrics ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['metrics'] - 1
                        )
                        
                        if min_id_to_keep:
                            # Delete older records that were exported
                            max_id_to_delete = min(metrics[-1]['id'], min_id_to_keep)
                            deleted = await conn.execute(
                                "DELETE FROM system_metrics WHERE id <= $1",
                                max_id_to_delete
                            )
                            logger.info(f"Cleaned up {deleted} old metrics from live view (exported to {export_path})")
                    
                    return len(metrics)
            
            return 0
    
    async def _check_and_export_processes(self, force: bool = False):
        """
        Export process snapshots if threshold exceeded or forced
        
        Args:
            force: Force export regardless of threshold
        
        Returns:
            Number of processes exported
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT COUNT(*) as count FROM processes")
            total_count = result['count']
            
            new_processes = total_count - self.last_export_counts['processes']
            
            if force or new_processes >= self.thresholds['processes']:
                logger.info(f"Exporting {new_processes} new process snapshots (threshold: {self.thresholds['processes']}, force={force})")
                
                processes = await conn.fetch(
                    """
                    SELECT id, agent_id, name, pid, cpu_percent, memory_percent, 
                           status, cmdline, username, collected_at
                    FROM processes
                    WHERE id > (
                        SELECT COALESCE(MAX(last_exported_id), 0)
                        FROM export_tracking
                        WHERE data_type = 'processes'
                    )
                    ORDER BY id
                    LIMIT $1
                    """,
                    self.thresholds['processes'] if not force else 999999
                )
                
                if processes:
                    export_path = await self._export_processes_to_file(processes)
                    self.last_export_counts['processes'] = total_count
                    await self._update_export_tracking('processes', processes[-1]['id'], len(processes))
                    
                    # Auto-cleanup: Delete exported processes from live view (keep minimum)
                    if self.auto_cleanup and total_count > self.min_live_records['processes']:
                        # Get ID of the record at position min_live_records from the end
                        min_id_to_keep = await conn.fetchval(
                            "SELECT id FROM processes ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['processes'] - 1
                        )
                        
                        if min_id_to_keep:
                            # Delete older records that were exported
                            max_id_to_delete = min(processes[-1]['id'], min_id_to_keep)
                            deleted = await conn.execute(
                                "DELETE FROM processes WHERE id <= $1",
                                max_id_to_delete
                            )
                            logger.info(f"Cleaned up {deleted} old process snapshots from live view (exported to {export_path})")
                    
                    return len(processes)
            
            return 0
    
    async def _check_and_export_commands(self, force: bool = False):
        """
        Export commands if threshold exceeded or forced
        
        Args:
            force: Force export regardless of threshold
        
        Returns:
            Number of commands exported
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT COUNT(*) as count FROM commands")
            total_count = result['count']
            
            new_commands = total_count - self.last_export_counts['commands']
            
            if force or new_commands >= self.thresholds['commands']:
                logger.info(f"Exporting {new_commands} new commands (threshold: {self.thresholds['commands']}, force={force})")
                
                commands = await conn.fetch(
                    """
                    SELECT id, agent_id, command, user_name, timestamp, 
                           shell, working_directory, exit_code
                    FROM commands
                    WHERE id > (
                        SELECT COALESCE(MAX(last_exported_id), 0)
                        FROM export_tracking
                        WHERE data_type = 'commands'
                    )
                    ORDER BY id
                    LIMIT $1
                    """,
                    self.thresholds['commands'] if not force else 999999
                )
                
                if commands:
                    export_path = await self._export_commands_to_file(commands)
                    self.last_export_counts['commands'] = total_count
                    await self._update_export_tracking('commands', commands[-1]['id'], len(commands))
                    
                    # Auto-cleanup: Delete exported commands from live view (keep minimum)
                    if self.auto_cleanup and total_count > self.min_live_records['commands']:
                        # Get ID of the record at position min_live_records from the end
                        min_id_to_keep = await conn.fetchval(
                            "SELECT id FROM commands ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['commands'] - 1
                        )
                        
                        if min_id_to_keep:
                            # Delete older records that were exported
                            max_id_to_delete = min(commands[-1]['id'], min_id_to_keep)
                            deleted = await conn.execute(
                                "DELETE FROM commands WHERE id <= $1",
                                max_id_to_delete
                            )
                            logger.info(f"Cleaned up {deleted} old commands from live view (exported to {export_path})")
                    
                    return len(commands)
            
            return 0
    
    async def _export_logs_to_file(self, logs: List[asyncpg.Record]):
        """
        Export logs to a single persistent CSV file (append mode)
        
        Returns:
            Path to the logs CSV file
        """
        # Single persistent file for all logs
        csv_file = self.export_dir / "logs.csv"
        
        # Convert to list of dicts
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log['id'],
                'timestamp': log['timestamp'].isoformat() if log['timestamp'] else None,
                'agent_id': str(log['agent_id']),
                'hostname': log['hostname'],
                'raw_json': log['raw_json'],
                'exported_at': datetime.now(timezone.utc).isoformat(),
            })
        
        # Create DataFrame
        df = pd.DataFrame(logs_data)
        
        # Append to existing file (or create new with header)
        file_exists = csv_file.exists()
        df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        
        logger.info(f"Appended {len(logs)} logs to {csv_file} (total file size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return csv_file
    
    async def _export_metrics_to_file(self, metrics: List[asyncpg.Record]):
        """
        Export metrics to a single persistent CSV file (append mode)
        
        Returns:
            Path to the metrics CSV file
        """
        # Single persistent file for all metrics
        csv_file = self.export_dir / "metrics.csv"
        
        # Parse JSON fields and flatten
        metrics_data = []
        for m in metrics:
            try:
                data = m['data'] if isinstance(m['data'], dict) else json.loads(m['data'])
                cpu_data = data.get('cpu_data', {})
                memory_data = data.get('memory_data', {})
                disk_data = data.get('disk_data', {})
                network_data = data.get('network_data', {})
                process_data = data.get('process_data', {})
                
                metrics_data.append({
                    'id': m['id'],
                    'agent_id': str(m['agent_id']),
                    'timestamp': m['collected_at'].isoformat() if m.get('collected_at') else None,
                    'cpu_percent': cpu_data.get('cpu_percent'),
                    'cpu_count': cpu_data.get('cpu_count'),
                    'memory_percent': memory_data.get('memory_percent'),
                    'memory_available': memory_data.get('memory_available'),
                    'memory_total': memory_data.get('memory_total'),
                    'disk_percent': disk_data.get('disk_percent') or disk_data.get('percent'),
                    'disk_used': disk_data.get('disk_used') or disk_data.get('used'),
                    'disk_total': disk_data.get('disk_total') or disk_data.get('total'),
                    'network_bytes_sent': network_data.get('bytes_sent'),
                    'network_bytes_recv': network_data.get('bytes_recv'),
                    'process_count': process_data.get('process_count') or process_data.get('total'),
                    'process_running': process_data.get('running'),
                    'exported_at': datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"Failed to parse metric {m['id']}: {e}")
                continue
        
        # Create DataFrame
        df = pd.DataFrame(metrics_data)
        
        # Append to existing file (or create new with header)
        file_exists = csv_file.exists()
        df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        
        logger.info(f"Appended {len(metrics)} metrics to {csv_file} (total file size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return csv_file
    
    async def _export_processes_to_file(self, processes: List[asyncpg.Record]):
        """
        Export process data to a single persistent CSV file (append mode)
        
        Returns:
            Path to the processes CSV file
        """
        # Single persistent file for all processes
        csv_file = self.export_dir / "processes.csv"
        
        processes_data = []
        for p in processes:
            processes_data.append({
                'id': p['id'],
                'agent_id': str(p['agent_id']),
                'name': p['name'],
                'pid': p['pid'],
                'cpu_percent': p['cpu_percent'],
                'memory_percent': p['memory_percent'],
                'status': p['status'],
                'cmdline': p['cmdline'],
                'username': p['username'],
                'collected_at': p['collected_at'].isoformat() if p['collected_at'] else None,
                'exported_at': datetime.now(timezone.utc).isoformat(),
            })
        
        # Create DataFrame
        df = pd.DataFrame(processes_data)
        
        # Append to existing file (or create new with header)
        file_exists = csv_file.exists()
        df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        
        logger.info(f"Appended {len(processes)} processes to {csv_file} (total file size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return csv_file
    
    async def _export_commands_to_file(self, commands: List[asyncpg.Record]):
        """
        Export commands to a single persistent CSV file (append mode)
        
        Returns:
            Path to the commands CSV file
        """
        # Single persistent file for all commands
        csv_file = self.export_dir / "commands.csv"
        
        commands_data = []
        for c in commands:
            commands_data.append({
                'id': c['id'],
                'agent_id': str(c['agent_id']),
                'command': c['command'],
                'user_name': c['user_name'],
                'timestamp': c['timestamp'].isoformat() if c['timestamp'] else None,
                'shell': c['shell'],
                'working_directory': c['working_directory'],
                'exit_code': c['exit_code'],
                'exported_at': datetime.now(timezone.utc).isoformat(),
            })
        
        # Create DataFrame
        df = pd.DataFrame(commands_data)
        
        # Append to existing file (or create new with header)
        file_exists = csv_file.exists()
        df.to_csv(csv_file, mode='a', header=not file_exists, index=False)
        
        logger.info(f"Appended {len(commands)} commands to {csv_file} (total file size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB)")
        return csv_file
    
    async def _update_export_tracking(self, data_type: str, last_id: int, count: int):
        """Update export tracking table"""
        async with self.pool.acquire() as conn:
            # Create tracking table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS export_tracking (
                    data_type VARCHAR(50) PRIMARY KEY,
                    last_exported_id BIGINT NOT NULL,
                    last_export_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    total_exported BIGINT DEFAULT 0
                )
            """)
            
            # Update tracking
            await conn.execute("""
                INSERT INTO export_tracking (data_type, last_exported_id, total_exported)
                VALUES ($1, $2, $3)
                ON CONFLICT (data_type)
                DO UPDATE SET
                    last_exported_id = $2,
                    last_export_time = CURRENT_TIMESTAMP,
                    total_exported = export_tracking.total_exported + $3
            """, data_type, last_id, count)
    
    async def export_labeled_dataset(
        self,
        device_id: UUID,
        label: str,
        description: str,
        start_time: datetime,
        end_time: datetime
    ):
        """
        Export a labeled dataset for specific time range.
        
        Use this to export data during known attack scenarios or normal behavior
        for supervised learning.
        
        Args:
            device_id: Device to export data for
            label: Label for the dataset (e.g., "normal", "brute_force", "privilege_escalation")
            description: Description of the scenario
            start_time: Start time of the scenario
            end_time: End time of the scenario
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        label_dir = self.export_dir / "labeled" / label
        label_dir.mkdir(parents=True, exist_ok=True)
        
        async with self.pool.acquire() as conn:
            # Export logs
            logs = await conn.fetch(
                """
                SELECT * FROM logs
                WHERE agent_id = $1 AND timestamp BETWEEN $2 AND $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
            
            # Export metrics
            metrics = await conn.fetch(
                """
                SELECT * FROM system_metrics
                WHERE agent_id = $1 AND timestamp BETWEEN $2 AND $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
            
            # Export commands
            commands = await conn.fetch(
                """
                SELECT * FROM commands
                WHERE agent_id = $1 AND timestamp BETWEEN $2 AND $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
            
            # Export processes
            processes = await conn.fetch(
                """
                SELECT * FROM processes
                WHERE agent_id = $1 AND collected_at BETWEEN $2 AND $3
                ORDER BY collected_at
                """,
                device_id, start_time, end_time
            )
        
        # Save metadata
        metadata = {
            "label": label,
            "description": description,
            "device_id": str(device_id),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "logs": len(logs),
                "metrics": len(metrics),
                "commands": len(commands),
                "processes": len(processes),
            }
        }
        
        metadata_file = label_dir / f"{label}_{timestamp}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Export data files
        if logs:
            df = pd.DataFrame([dict(r) for r in logs])
            df.to_csv(label_dir / f"{label}_{timestamp}_logs.csv", index=False)
        
        if metrics:
            df = pd.DataFrame([dict(r) for r in metrics])
            df.to_csv(label_dir / f"{label}_{timestamp}_metrics.csv", index=False)
        
        if commands:
            df = pd.DataFrame([dict(r) for r in commands])
            df.to_csv(label_dir / f"{label}_{timestamp}_commands.csv", index=False)
        
        if processes:
            df = pd.DataFrame([dict(r) for r in processes])
            df.to_csv(label_dir / f"{label}_{timestamp}_processes.csv", index=False)
        
        logger.info(f"Exported labeled dataset '{label}' to {label_dir}")
        logger.info(f"  Logs: {len(logs)}, Metrics: {len(metrics)}, Commands: {len(commands)}, Processes: {len(processes)}")
        
        return metadata_file


# Global exporter instance
_exporter: Optional[DataExporter] = None


def get_data_exporter() -> Optional[DataExporter]:
    """Get the global data exporter instance"""
    return _exporter


def init_data_exporter(pool: asyncpg.Pool, export_dir: str = "./ml_data"):
    """Initialize the global data exporter"""
    global _exporter
    _exporter = DataExporter(pool, export_dir)
    return _exporter
