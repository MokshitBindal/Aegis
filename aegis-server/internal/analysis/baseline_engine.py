"""
Baseline Learning Engine for Aegis SIEM

This module analyzes historical data (processes, metrics, logs) to learn
device-specific "normal" behavior patterns. These baselines are then used
by the AI model to detect anomalies.

Author: Mokshit Bindal
Date: November 8, 2025
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)


class BaselineLearner:
    """
    Learn normal behavioral patterns for each device.
    
    This class analyzes 2-4 weeks of historical data to establish:
    - Typical process patterns (count, names, resource usage)
    - System metric baselines (CPU, memory, disk, network)
    - Temporal activity patterns (active hours, active days)
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        
    async def learn_device_baseline(
        self,
        device_id: UUID,
        duration_days: int = 28
    ) -> Dict:
        """
        Learn baseline for a single device.
        
        Args:
            device_id: UUID of the device
            duration_days: Number of days to analyze (default: 28)
            
        Returns:
            Dictionary containing all baseline profiles
        """
        logger.info(f"Learning baseline for device {device_id} over {duration_days} days")
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=duration_days)
        
        # Learn different baseline components
        process_baseline = await self._learn_process_baseline(device_id, start_time, end_time)
        metrics_baseline = await self._learn_metrics_baseline(device_id, start_time, end_time)
        activity_baseline = await self._learn_activity_baseline(device_id, start_time, end_time)
        command_baseline = await self._learn_command_baseline(device_id, start_time, end_time)
        
        baseline = {
            "device_id": str(device_id),
            "learned_at": datetime.now(timezone.utc).isoformat(),
            "duration_days": duration_days,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "process_baseline": process_baseline,
            "metrics_baseline": metrics_baseline,
            "activity_baseline": activity_baseline,
            "command_baseline": command_baseline,
        }
        
        logger.info(f"Baseline learning complete for device {device_id}")
        return baseline
    
    async def _learn_process_baseline(
        self,
        device_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Learn normal process patterns.
        
        Returns:
            {
                "typical_count": {"mean": 145, "std": 12, "p95": 165, "p99": 180},
                "common_processes": ["systemd", "sshd", "python3", ...],
                "cpu_usage": {"mean": 15.2, "std": 8.1, "p95": 35.0, "p99": 50.0},
                "memory_usage": {"mean": 2.1, "std": 0.5, "p95": 3.8, "p99": 5.0},
                "typical_cpu_intensive": ["chrome", "mysql", "python3"],
                "snapshots_analyzed": 1440
            }
        """
        logger.info(f"Analyzing process patterns for device {device_id}")
        
        # Get all process snapshots in time range
        async with self.pool.acquire() as conn:
            processes = await conn.fetch(
                """
                SELECT name, cpu_percent, memory_percent, collected_at
                FROM processes
                WHERE agent_id = $1 AND collected_at >= $2 AND collected_at <= $3
                ORDER BY collected_at
                """,
                device_id, start_time, end_time
            )
        
        if not processes:
            logger.warning(f"No process data found for device {device_id}")
            return {}
        
        # Group by snapshot timestamp to count processes per snapshot
        snapshots = {}
        process_names = {}
        cpu_values = []
        memory_values = []
        
        for proc in processes:
            snapshot_time = proc['collected_at'].replace(second=0, microsecond=0)
            
            if snapshot_time not in snapshots:
                snapshots[snapshot_time] = []
            
            snapshots[snapshot_time].append(proc)
            
            # Track process names
            if proc['name']:
                process_names[proc['name']] = process_names.get(proc['name'], 0) + 1
            
            # Collect CPU and memory values
            if proc['cpu_percent'] is not None:
                cpu_values.append(proc['cpu_percent'])
            if proc['memory_percent'] is not None:
                memory_values.append(proc['memory_percent'])
        
        # Calculate process count statistics
        process_counts = [len(snapshot) for snapshot in snapshots.values()]
        
        # Find most common processes (appearing in >80% of snapshots)
        total_snapshots = len(snapshots)
        common_threshold = total_snapshots * 0.8
        common_processes = [
            name for name, count in process_names.items()
            if count > common_threshold
        ]
        
        # Find CPU-intensive processes (mean CPU > 10%)
        cpu_intensive_procs = {}
        for proc in processes:
            if proc['name'] and proc['cpu_percent'] and proc['cpu_percent'] > 10:
                if proc['name'] not in cpu_intensive_procs:
                    cpu_intensive_procs[proc['name']] = []
                cpu_intensive_procs[proc['name']].append(proc['cpu_percent'])
        
        typical_cpu_intensive = [
            name for name, values in cpu_intensive_procs.items()
            if np.mean(values) > 10
        ]
        
        baseline = {
            "typical_count": {
                "mean": float(np.mean(process_counts)),
                "std": float(np.std(process_counts)),
                "p95": float(np.percentile(process_counts, 95)),
                "p99": float(np.percentile(process_counts, 99)),
                "min": int(np.min(process_counts)),
                "max": int(np.max(process_counts)),
            },
            "common_processes": sorted(common_processes)[:50],  # Top 50
            "cpu_usage": {
                "mean": float(np.mean(cpu_values)) if cpu_values else 0.0,
                "std": float(np.std(cpu_values)) if cpu_values else 0.0,
                "p95": float(np.percentile(cpu_values, 95)) if cpu_values else 0.0,
                "p99": float(np.percentile(cpu_values, 99)) if cpu_values else 0.0,
            },
            "memory_usage": {
                "mean": float(np.mean(memory_values)) if memory_values else 0.0,
                "std": float(np.std(memory_values)) if memory_values else 0.0,
                "p95": float(np.percentile(memory_values, 95)) if memory_values else 0.0,
                "p99": float(np.percentile(memory_values, 99)) if memory_values else 0.0,
            },
            "typical_cpu_intensive": sorted(typical_cpu_intensive)[:20],  # Top 20
            "snapshots_analyzed": len(snapshots),
            "unique_processes": len(process_names),
        }
        
        logger.info(f"Process baseline: {baseline['snapshots_analyzed']} snapshots, "
                   f"{baseline['unique_processes']} unique processes")
        
        return baseline
    
    async def _learn_metrics_baseline(
        self,
        device_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Learn normal system metric patterns from system_metrics table.
        
        Data structure in DB:
        - cpu_data: {"percent": 45.2, "count": 8, "per_cpu": [23.1, 67.3, ...]}
        - memory_data: {"percent": 62.5, "available": 8589934592, "total": 17179869184}
        - disk_data: {"percent": 45.0, "total": 500000000000, "used": 225000000000}
        - network_data: {"bytes_sent": 12345678, "bytes_recv": 23456789}
        - process_data: {"total": 145, "running": 2, "sleeping": 143}
        
        Returns:
            Statistical baselines for each metric type for ML model training
        """
        logger.info(f"Analyzing metric patterns for device {device_id}")
        
        # Get all metrics in time range
        async with self.pool.acquire() as conn:
            metrics = await conn.fetch(
                """
                SELECT cpu_data, memory_data, disk_data, network_data, process_data, timestamp
                FROM system_metrics
                WHERE agent_id = $1 AND timestamp >= $2 AND timestamp <= $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
        
        if not metrics:
            logger.warning(f"No metric data found for device {device_id}")
            return {}
        
        # Collect all metric values
        cpu_percent = []
        memory_percent = []
        memory_available = []
        disk_percent = []
        disk_used = []
        network_bytes_sent = []
        network_bytes_recv = []
        process_total = []
        process_running = []
        
        for m in metrics:
            try:
                # Parse JSON strings (JSONB columns are returned as strings by asyncpg)
                import json
                cpu_data = json.loads(m['cpu_data']) if isinstance(m['cpu_data'], str) else m['cpu_data']
                memory_data = json.loads(m['memory_data']) if isinstance(m['memory_data'], str) else m['memory_data']
                disk_data = json.loads(m['disk_data']) if isinstance(m['disk_data'], str) else m['disk_data']
                network_data = json.loads(m['network_data']) if isinstance(m['network_data'], str) else m['network_data']
                process_data = json.loads(m['process_data']) if isinstance(m['process_data'], str) else m['process_data']
                
                # Extract CPU metrics (key is cpu_percent, not percent)
                if 'cpu_percent' in cpu_data:
                    cpu_percent.append(float(cpu_data['cpu_percent']))
                
                # Extract memory metrics
                if 'memory_percent' in memory_data:
                    memory_percent.append(float(memory_data['memory_percent']))
                if 'memory_available' in memory_data:
                    memory_available.append(float(memory_data['memory_available']))
                
                # Extract disk metrics  
                if 'disk_percent' in disk_data:
                    disk_percent.append(float(disk_data['disk_percent']))
                elif 'percent' in disk_data:  # fallback
                    disk_percent.append(float(disk_data['percent']))
                if 'disk_used' in disk_data:
                    disk_used.append(float(disk_data['disk_used']))
                elif 'used' in disk_data:  # fallback
                    disk_used.append(float(disk_data['used']))
                
                # Extract network metrics
                if 'bytes_sent' in network_data:
                    network_bytes_sent.append(float(network_data['bytes_sent']))
                if 'bytes_recv' in network_data:
                    network_bytes_recv.append(float(network_data['bytes_recv']))
                
                # Extract process metrics
                if 'process_count' in process_data:
                    process_total.append(float(process_data['process_count']))
                elif 'total' in process_data:  # fallback
                    process_total.append(float(process_data['total']))
                if 'running' in process_data:
                    process_running.append(float(process_data['running']))
                    
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to parse metric data at {m.get('timestamp')}: {e}")
                continue
        
        def calculate_stats(values: List[float]) -> Dict:
            """Calculate statistical baseline for a metric - used by Isolation Forest"""
            if not values:
                return {"mean": 0.0, "std": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
            return {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "p95": float(np.percentile(values, 95)),
                "p99": float(np.percentile(values, 99)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }
        
        baseline = {
            "cpu_percent": calculate_stats(cpu_percent),
            "memory_percent": calculate_stats(memory_percent),
            "memory_available_gb": calculate_stats([v / (1024**3) for v in memory_available]) if memory_available else {},
            "disk_percent": calculate_stats(disk_percent),
            "disk_used_gb": calculate_stats([v / (1024**3) for v in disk_used]) if disk_used else {},
            "network_bytes_sent": calculate_stats(network_bytes_sent),
            "network_bytes_recv": calculate_stats(network_bytes_recv),
            "process_total": calculate_stats(process_total),
            "process_running": calculate_stats(process_running),
            "samples_analyzed": len(metrics),
        }
        
        logger.info(f"Metrics baseline: {len(metrics)} samples analyzed")
        return baseline
    
    async def _learn_activity_baseline(
        self,
        device_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Learn temporal activity patterns (when is user typically active).
        
        Returns:
            {
                "active_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                "active_days": [0, 1, 2, 3, 4],  # Monday-Friday (0=Monday)
                "hourly_activity": {0: 10, 1: 5, ..., 23: 50},
                "weekday_activity": {0: 150, 1: 180, ..., 6: 20},
                "typical_activity_level": {"weekday": 85, "weekend": 15}
            }
        """
        logger.info(f"Analyzing activity patterns for device {device_id}")
        
        # Use commands as proxy for user activity
        async with self.pool.acquire() as conn:
            commands = await conn.fetch(
                """
                SELECT timestamp
                FROM commands
                WHERE agent_id = $1 AND timestamp >= $2 AND timestamp <= $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
        
        if not commands:
            logger.warning(f"No command data found for device {device_id}")
            return {}
        
        # Analyze by hour and day
        hourly_activity = {h: 0 for h in range(24)}
        weekday_activity = {d: 0 for d in range(7)}
        
        for cmd in commands:
            hour = cmd['timestamp'].hour
            weekday = cmd['timestamp'].weekday()
            
            hourly_activity[hour] += 1
            weekday_activity[weekday] += 1
        
        # Determine active hours (>10% of max activity)
        max_hourly = max(hourly_activity.values()) if hourly_activity else 1
        threshold = max_hourly * 0.1
        active_hours = [h for h, count in hourly_activity.items() if count > threshold]
        
        # Determine active days (>10% of max activity)
        max_daily = max(weekday_activity.values()) if weekday_activity else 1
        threshold = max_daily * 0.1
        active_days = [d for d, count in weekday_activity.items() if count > threshold]
        
        # Calculate weekday vs weekend activity
        weekday_total = sum(weekday_activity[d] for d in range(5))  # Mon-Fri
        weekend_total = sum(weekday_activity[d] for d in range(5, 7))  # Sat-Sun
        total_activity = weekday_total + weekend_total
        
        baseline = {
            "active_hours": sorted(active_hours),
            "active_days": sorted(active_days),
            "hourly_activity": hourly_activity,
            "weekday_activity": weekday_activity,
            "typical_activity_level": {
                "weekday": round(weekday_total / total_activity * 100, 1) if total_activity > 0 else 50,
                "weekend": round(weekend_total / total_activity * 100, 1) if total_activity > 0 else 50,
            },
            "total_commands": len(commands),
            "most_active_hour": max(hourly_activity, key=hourly_activity.get),
            "most_active_day": max(weekday_activity, key=weekday_activity.get),
        }
        
        logger.info(f"Activity baseline: {len(commands)} commands analyzed")
        
        return baseline
    
    async def _learn_command_baseline(
        self,
        device_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Learn command execution patterns.
        
        Returns:
            {
                "common_commands": ["ls", "cd", "git", "vim", ...],
                "sudo_frequency": 15,  # per day
                "typical_command_count": {"mean": 150, "std": 50},
                "unique_commands": 87
            }
        """
        logger.info(f"Analyzing command patterns for device {device_id}")
        
        async with self.pool.acquire() as conn:
            commands = await conn.fetch(
                """
                SELECT command, timestamp
                FROM commands
                WHERE agent_id = $1 AND timestamp >= $2 AND timestamp <= $3
                ORDER BY timestamp
                """,
                device_id, start_time, end_time
            )
        
        if not commands:
            return {}
        
        # Extract command names (first word of command)
        command_names = {}
        sudo_count = 0
        daily_counts = {}
        
        for cmd in commands:
            if cmd['command']:
                # Extract first word as command name
                parts = cmd['command'].strip().split()
                if parts:
                    cmd_name = parts[0]
                    command_names[cmd_name] = command_names.get(cmd_name, 0) + 1
                    
                    if cmd['command'].startswith('sudo'):
                        sudo_count += 1
                
                # Count commands per day
                day = cmd['timestamp'].date()
                daily_counts[day] = daily_counts.get(day, 0) + 1
        
        # Find most common commands
        common_commands = sorted(
            command_names.items(),
            key=lambda x: x[1],
            reverse=True
        )[:30]  # Top 30 commands
        
        # Calculate daily command stats
        daily_values = list(daily_counts.values())
        days_analyzed = (end_time - start_time).days or 1
        
        baseline = {
            "common_commands": [cmd[0] for cmd in common_commands],
            "sudo_frequency": round(sudo_count / days_analyzed, 1),
            "typical_command_count": {
                "mean": float(np.mean(daily_values)) if daily_values else 0,
                "std": float(np.std(daily_values)) if daily_values else 0,
            },
            "unique_commands": len(command_names),
            "total_commands": len(commands),
        }
        
        return baseline
