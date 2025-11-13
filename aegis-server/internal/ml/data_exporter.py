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
        
        When ANY threshold is exceeded, ALL data types are exported together.
        
        Args:
            force: If True, export regardless of thresholds
        
        Returns:
            Dict with counts of exported items
        """
        try:
            # Check if any threshold is exceeded
            should_export = force
            
            if not force:
                async with self.pool.acquire() as conn:
                    # Check each data type against its threshold
                    logs_count = await conn.fetchval("SELECT COUNT(*) FROM logs")
                    new_logs = logs_count - self.last_export_counts['logs']
                    
                    metrics_count = await conn.fetchval("SELECT COUNT(*) FROM system_metrics")
                    new_metrics = metrics_count - self.last_export_counts['metrics']
                    
                    # Check if ANY threshold is exceeded
                    if (new_logs >= self.thresholds['logs'] or 
                        new_metrics >= self.thresholds['metrics']):
                        should_export = True
                        logger.info(f"Export triggered: logs={new_logs}/{self.thresholds['logs']}, metrics={new_metrics}/{self.thresholds['metrics']}")
            
            result = {}
            if should_export:
                # Export ALL data types when triggered
                result['logs'] = await self._check_and_export_logs(force=True)
                result['metrics'] = await self._check_and_export_metrics(force=True)
                result['processes'] = await self._check_and_export_processes(force=True)
                result['commands'] = await self._check_and_export_commands(force=True)
                
                # Update last export time
                self.last_export_time = datetime.now(timezone.utc)
            else:
                result = {'logs': 0, 'metrics': 0, 'processes': 0, 'commands': 0}
            
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
                logger.info(f"Exporting ALL logs from database (total: {total_count}, new: {new_logs})")
                
                # Fetch ALL logs (export everything in the database)
                # Note: logs table is a TimescaleDB hypertable with NO id column
                # Columns: timestamp, agent_id, hostname, raw_data
                logs = await conn.fetch(
                    """
                    SELECT timestamp, agent_id, hostname, raw_data
                    FROM logs
                    ORDER BY timestamp ASC
                    """
                )
                
                if logs:
                    # Export to file
                    export_path = await self._export_logs_to_file(logs)
                    
                    # Update last export count BEFORE cleanup
                    # This represents the total we've exported, not what remains after cleanup
                    self.last_export_counts['logs'] = total_count
                    
                    # Auto-cleanup: Keep only the most recent min_live_records logs
                    if self.auto_cleanup and total_count > self.min_live_records['logs']:
                        # Delete all but the most recent min_live_records logs
                        # Get the timestamp of the Nth most recent log (where N = min_live_records)
                        cutoff_timestamp = await conn.fetchval(
                            """
                            SELECT timestamp FROM logs
                            ORDER BY timestamp DESC
                            LIMIT 1 OFFSET $1
                            """,
                            self.min_live_records['logs'] - 1
                        )
                        
                        if cutoff_timestamp:
                            # Delete all logs older than cutoff
                            result = await conn.execute(
                                "DELETE FROM logs WHERE timestamp < $1",
                                cutoff_timestamp
                            )
                            # Extract count from "DELETE X" string
                            deleted_count = int(result.split()[-1]) if result and result.startswith('DELETE') else 0
                            logger.info(f"Cleaned up {deleted_count} old logs (keeping {self.min_live_records['logs']} most recent)")
                    
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
                logger.info(f"Exporting ALL metrics from database (total: {total_count}, new: {new_metrics})")
                
                # Fetch ALL metrics (export everything in the database)
                metrics = await conn.fetch(
                    """
                    SELECT id, agent_id, timestamp, cpu_data, memory_data, 
                           disk_data, network_data, process_data
                    FROM system_metrics
                    ORDER BY id
                    """
                )
                
                if metrics:
                    export_path = await self._export_metrics_to_file(metrics)
                    
                    # Update last export count BEFORE cleanup
                    self.last_export_counts['metrics'] = total_count
                    
                    # Auto-cleanup: Keep only the most recent min_live_records metrics
                    if self.auto_cleanup and total_count > self.min_live_records['metrics']:
                        # Get the ID of the Nth most recent metric (where N = min_live_records)
                        cutoff_id = await conn.fetchval(
                            "SELECT id FROM system_metrics ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['metrics'] - 1
                        )
                        
                        if cutoff_id:
                            # Delete all metrics older than cutoff
                            result = await conn.execute(
                                "DELETE FROM system_metrics WHERE id < $1",
                                cutoff_id
                            )
                            deleted_count = int(result.split()[-1]) if result and result.startswith('DELETE') else 0
                            logger.info(f"Cleaned up {deleted_count} old metrics (keeping {self.min_live_records['metrics']} most recent)")
                    
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
        try:
            async with self.pool.acquire() as conn:
                # Export from processes_history table (all snapshots for ML)
                result = await conn.fetchrow("SELECT COUNT(*) as count FROM processes_history")
                total_count = result['count']
        except asyncpg.exceptions.UndefinedTableError:
            logger.debug("Processes history table does not exist yet, skipping export")
            return 0
        
        async with self.pool.acquire() as conn:
            
            new_processes = total_count - self.last_export_counts['processes']
            
            if force or new_processes >= self.thresholds['processes']:
                logger.info(f"Exporting ALL process snapshots from history (total: {total_count}, new: {new_processes})")
                
                # Fetch ALL process snapshots from history table
                processes = await conn.fetch(
                    """
                    SELECT id, agent_id, name, pid, cpu_percent, memory_percent, 
                           status, cmdline, username, collected_at
                    FROM processes_history
                    ORDER BY id
                    """
                )
                
                if processes:
                    export_path = await self._export_processes_to_file(processes)
                    
                    # Update last export count BEFORE cleanup
                    self.last_export_counts['processes'] = total_count
                    
                    # Auto-cleanup: Keep only the most recent min_live_records process snapshots
                    if self.auto_cleanup and total_count > self.min_live_records['processes']:
                        cutoff_id = await conn.fetchval(
                            "SELECT id FROM processes_history ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['processes'] - 1
                        )
                        
                        if cutoff_id:
                            result = await conn.execute(
                                "DELETE FROM processes_history WHERE id < $1",
                                cutoff_id
                            )
                            deleted_count = int(result.split()[-1]) if result and result.startswith('DELETE') else 0
                            logger.info(f"Cleaned up {deleted_count} old process snapshots (keeping {self.min_live_records['processes']} most recent)")
                    
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
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("SELECT COUNT(*) as count FROM commands")
                total_count = result['count']
        except asyncpg.exceptions.UndefinedTableError:
            logger.debug("Commands table does not exist yet, skipping export")
            return 0
        
        async with self.pool.acquire() as conn:
            
            new_commands = total_count - self.last_export_counts['commands']
            
            if force or new_commands >= self.thresholds['commands']:
                logger.info(f"Exporting ALL commands from database (total: {total_count}, new: {new_commands})")
                
                # Fetch ALL commands (export everything in the database)
                commands = await conn.fetch(
                    """
                    SELECT id, agent_id, command, user_name, timestamp, 
                           shell, working_directory, exit_code
                    FROM commands
                    ORDER BY id
                    """
                )
                
                if commands:
                    export_path = await self._export_commands_to_file(commands)
                    
                    # Update last export count BEFORE cleanup
                    self.last_export_counts['commands'] = total_count
                    
                    # Auto-cleanup: Keep only the most recent min_live_records commands
                    if self.auto_cleanup and total_count > self.min_live_records['commands']:
                        cutoff_id = await conn.fetchval(
                            "SELECT id FROM commands ORDER BY id DESC LIMIT 1 OFFSET $1",
                            self.min_live_records['commands'] - 1
                        )
                        
                        if cutoff_id:
                            result = await conn.execute(
                                "DELETE FROM commands WHERE id < $1",
                                cutoff_id
                            )
                            deleted_count = int(result.split()[-1]) if result and result.startswith('DELETE') else 0
                            logger.info(f"Cleaned up {deleted_count} old commands (keeping {self.min_live_records['commands']} most recent)")
                    
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
                'timestamp': log['timestamp'].isoformat() if log['timestamp'] else None,
                'agent_id': str(log['agent_id']),
                'hostname': log['hostname'],
                'raw_data': log['raw_data'],  # JSONB column
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
                # Extract JSONB columns (already parsed as dicts by asyncpg)
                cpu_data = m['cpu_data'] if isinstance(m['cpu_data'], dict) else {}
                memory_data = m['memory_data'] if isinstance(m['memory_data'], dict) else {}
                disk_data = m['disk_data'] if isinstance(m['disk_data'], dict) else {}
                network_data = m['network_data'] if isinstance(m['network_data'], dict) else {}
                process_data = m['process_data'] if isinstance(m['process_data'], dict) else {}
                
                metrics_data.append({
                    'id': m['id'],
                    'agent_id': str(m['agent_id']),
                    'timestamp': m['timestamp'].isoformat() if m.get('timestamp') else None,
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
