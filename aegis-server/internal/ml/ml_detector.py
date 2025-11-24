"""
ML-based anomaly detection service for Aegis SIEM.

This module runs the trained ML model periodically to detect anomalies
in system behavior and generates alerts for suspicious activity.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional

from internal.ml.anomaly_detector import AnomalyDetector


class MLDetectionService:
    """Service to run ML anomaly detection and generate alerts"""
    
    def __init__(self, db_pool, model_dir: str = "models"):
        self.db_pool = db_pool
        self.model_dir = model_dir
        self.detector: Optional[AnomalyDetector] = None
        self.last_detection_time: Dict[str, datetime] = {}
        
    async def initialize(self):
        """Initialize the ML detector by loading the model"""
        try:
            self.detector = AnomalyDetector(model_dir=self.model_dir)
            self.detector.load_model()
            print("✅ ML Detector initialized successfully")
            model_info = self.detector.get_model_info()
            print(f"   Algorithm: {model_info.get('algorithm', 'IsolationForest')}")
            print(f"   Features: {len(model_info.get('features', []))}")
            print(f"   Trained: {model_info.get('trained_at', 'Unknown')[:19]}")
        except Exception as e:
            print(f"❌ Failed to initialize ML detector: {e}")
            self.detector = None
    
    async def extract_features_from_db(self, agent_id: uuid.UUID, 
                                       start_time: datetime, 
                                       end_time: datetime) -> Optional[Dict]:
        """
        Extract features from database for a given time window.
        
        This mirrors the feature extraction from the ML training pipeline.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Extract features matching the training pipeline
                features = {}
                
                # 1. Temporal features
                features['hour'] = end_time.hour
                features['day_of_week'] = end_time.weekday()
                features['is_weekend'] = 1 if end_time.weekday() >= 5 else 0
                
                # 2. System metrics features
                # Extract from JSONB columns in system_metrics table
                metrics = await conn.fetchrow("""
                    SELECT 
                        AVG((cpu_data->>'cpu_percent')::float) as avg_cpu,
                        AVG((memory_data->>'memory_percent')::float) as avg_memory,
                        AVG(COALESCE((disk_data->>'disk_percent')::float, (disk_data->>'percent')::float)) as avg_disk,
                        SUM((network_data->>'bytes_sent')::bigint) / 1024.0 / 1024.0 as avg_net_sent,
                        SUM((network_data->>'bytes_recv')::bigint) / 1024.0 / 1024.0 as avg_net_recv
                    FROM system_metrics
                    WHERE agent_id = $1 
                    AND timestamp >= $2 
                    AND timestamp < $3
                """, agent_id, start_time, end_time)
                
                if metrics:
                    features['cpu_percent'] = float(metrics['avg_cpu'] or 0)
                    features['memory_percent'] = float(metrics['avg_memory'] or 0)
                    features['disk_percent'] = float(metrics['avg_disk'] or 0)
                    features['network_mb_sent'] = float(metrics['avg_net_sent'] or 0)
                    features['network_mb_recv'] = float(metrics['avg_net_recv'] or 0)
                else:
                    # No metrics found, use defaults
                    features.update({
                        'cpu_percent': 0.0,
                        'memory_percent': 0.0,
                        'disk_percent': 0.0,
                        'network_mb_sent': 0.0,
                        'network_mb_recv': 0.0
                    })
                
                # 3. Process features
                processes = await conn.fetchrow("""
                    SELECT 
                        COUNT(DISTINCT name) as process_count,
                        MAX(cpu_percent) as max_cpu,
                        MAX(memory_percent) as max_memory
                    FROM processes
                    WHERE agent_id = $1 
                    AND timestamp >= $2 
                    AND timestamp < $3
                """, agent_id, start_time, end_time)
                
                if processes:
                    features['process_count'] = int(processes['process_count'] or 0)
                    features['max_process_cpu'] = float(processes['max_cpu'] or 0)
                    features['max_process_memory'] = float(processes['max_memory'] or 0)
                else:
                    features.update({
                        'process_count': 0,
                        'max_process_cpu': 0.0,
                        'max_process_memory': 0.0
                    })
                
                # 4. Command features
                commands = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as command_count,
                        SUM(CASE WHEN command LIKE 'sudo %' THEN 1 ELSE 0 END) as sudo_count
                    FROM commands
                    WHERE agent_id = $1 
                    AND timestamp >= $2 
                    AND timestamp < $3
                """, agent_id, start_time, end_time)
                
                if commands:
                    features['command_count'] = int(commands['command_count'] or 0)
                    features['sudo_count'] = int(commands['sudo_count'] or 0)
                else:
                    features.update({
                        'command_count': 0,
                        'sudo_count': 0
                    })
                
                # 5. Log features
                logs = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as log_count,
                        SUM(CASE WHEN severity IN ('error', 'critical') THEN 1 ELSE 0 END) as error_count
                    FROM logs
                    WHERE agent_id = $1 
                    AND timestamp >= $2 
                    AND timestamp < $3
                """, agent_id, start_time, end_time)
                
                if logs:
                    features['log_count'] = int(logs['log_count'] or 0)
                    features['error_count'] = int(logs['error_count'] or 0)
                else:
                    features.update({
                        'log_count': 0,
                        'error_count': 0
                    })
                
                return features
                
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    async def generate_alert(self, agent_id: uuid.UUID, 
                           anomaly_score: float, 
                           severity: str,
                           features: Dict,
                           contributions: Dict):
        """Generate an alert in the database for detected anomaly"""
        try:
            async with self.db_pool.acquire() as conn:
                # Create detailed alert message
                rule_name = f"ML Anomaly Detection - {severity.upper()}"
                
                # Deduplication: Check for similar alert in last 30 minutes
                # This prevents spam from repeated alerts (e.g., vscode high CPU usage)
                dedup_window = datetime.now(UTC) - timedelta(minutes=30)
                existing_alert = await conn.fetchrow("""
                    SELECT id FROM alerts
                    WHERE rule_name = $1 
                    AND severity = $2 
                    AND agent_id = $3
                    AND created_at >= $4
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, rule_name, severity, agent_id, dedup_window)
                
                if existing_alert:
                    print(f"⚠️  Suppressed duplicate ML alert for device {agent_id}")
                    print(f"   Rule: {rule_name}, Severity: {severity}")
                    print(f"   (Similar alert exists: ID {existing_alert['id']})")
                    return None
                
                # Build details with top contributing features
                top_features = sorted(
                    contributions.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:5]
                
                details = {
                    "type": "ml_anomaly",
                    "anomaly_score": round(anomaly_score, 3),
                    "severity": severity,
                    "detection_time": datetime.now(UTC).isoformat(),
                    "top_features": [
                        {
                            "feature": feat,
                            "value": round(features.get(feat, 0), 2),
                            "contribution": round(contrib, 3)
                        }
                        for feat, contrib in top_features
                    ],
                    "all_features": {k: round(v, 2) if isinstance(v, float) else v 
                                   for k, v in features.items()}
                }
                
                # Insert alert
                sql = """
                INSERT INTO alerts (rule_name, severity, details, agent_id, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """
                
                result = await conn.fetchrow(
                    sql,
                    rule_name,
                    severity,
                    json.dumps(details),
                    agent_id,
                    datetime.now(UTC)
                )
                
                if result:
                    print(f"✅ Generated ML alert (ID: {result['id']}) for device {agent_id}")
                    print(f"   Score: {anomaly_score:.3f}, Severity: {severity}")
                    print(f"   Top feature: {top_features[0][0]} (contribution: {top_features[0][1]:.3f})")
                    return result['id']
                
        except Exception as e:
            print(f"Error generating alert: {e}")
            return None
    
    async def detect_anomalies_for_device(self, agent_id: uuid.UUID) -> bool:
        """Run anomaly detection for a specific device"""
        if not self.detector:
            return False
        
        try:
            # Get last detection time for this device
            last_time = self.last_detection_time.get(str(agent_id))
            now = datetime.now(UTC)
            
            # Use last hour as detection window
            end_time = now
            start_time = end_time - timedelta(hours=1)
            
            # If we've already checked this hour, skip
            if last_time and last_time >= start_time:
                return False
            
            # Extract features
            features = await self.extract_features_from_db(agent_id, start_time, end_time)
            if not features:
                return False
            
            # Check if there's any activity (to avoid alerting on idle systems)
            total_activity = (
                features.get('log_count', 0) + 
                features.get('command_count', 0) + 
                features.get('process_count', 0)
            )
            
            if total_activity < 5:  # Very low activity threshold
                # Update last detection time but don't alert
                self.last_detection_time[str(agent_id)] = now
                return False
            
            # Run prediction
            is_anomaly, score, severity = self.detector.predict(features)
            
            if is_anomaly:
                # Get feature contributions for explainability
                contributions = self.detector.get_feature_contributions(features)
                
                # Generate alert
                alert_id = await self.generate_alert(
                    agent_id, score, severity, features, contributions
                )
                
                if alert_id:
                    self.last_detection_time[str(agent_id)] = now
                    return True
            else:
                # Update last detection time even if no anomaly
                self.last_detection_time[str(agent_id)] = now
            
            return False
            
        except Exception as e:
            print(f"Error detecting anomalies for device {agent_id}: {e}")
            return False
    
    async def run_detection_cycle(self):
        """Run detection for all active devices"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get all active devices (seen in last 2 hours)
                two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
                
                devices = await conn.fetch("""
                    SELECT agent_id, hostname 
                    FROM devices 
                    WHERE last_seen >= $1 
                    AND status = 'online'
                    ORDER BY last_seen DESC
                """, two_hours_ago)
                
                if not devices:
                    print("No active devices found for ML detection")
                    return
                
                print(f"\n🔍 Running ML detection for {len(devices)} active device(s)...")
                
                alerts_generated = 0
                for device in devices:
                    agent_id = device['agent_id']
                    hostname = device['hostname']
                    
                    detected = await self.detect_anomalies_for_device(agent_id)
                    if detected:
                        alerts_generated += 1
                        print(f"   ⚠️  Anomaly detected on {hostname}")
                
                if alerts_generated > 0:
                    print(f"✅ Generated {alerts_generated} ML alert(s)")
                else:
                    print("✅ No anomalies detected")
                    
        except Exception as e:
            print(f"Error in detection cycle: {e}")


# Global instance
_ml_service: Optional[MLDetectionService] = None


def init_ml_service(db_pool, model_dir: str = "models"):
    """Initialize the ML detection service"""
    global _ml_service
    _ml_service = MLDetectionService(db_pool, model_dir)
    return _ml_service


def get_ml_service() -> Optional[MLDetectionService]:
    """Get the ML detection service instance"""
    return _ml_service


async def run_ml_detection_loop():
    """
    Background task to run ML anomaly detection periodically.
    
    Runs every 10 minutes to check for anomalies in recent system behavior.
    """
    print("Starting ML anomaly detection loop...")
    
    # Wait for server to be fully ready
    await asyncio.sleep(60)
    
    service = get_ml_service()
    if not service:
        print("ML service not initialized, skipping ML detection loop")
        return
    
    # Initialize the ML detector
    await service.initialize()
    
    if not service.detector:
        print("ML detector failed to initialize, exiting detection loop")
        return
    
    # Run detection every 10 minutes
    while True:
        try:
            await service.run_detection_cycle()
            await asyncio.sleep(600)  # 10 minutes
            
        except asyncio.CancelledError:
            print("ML detection loop cancelled")
            raise
        except Exception as e:
            print(f"Error in ML detection loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
