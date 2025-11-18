"""
Feature Extractor - Extract features from raw data for ML training

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List


class FeatureExtractor:
    """Extract features from system data for anomaly detection"""
    
    def __init__(self):
        """Initialize feature extractor"""
        self.feature_names = []
    
    def extract_temporal_features(self, timestamp: pd.Series) -> pd.DataFrame:
        """
        Extract time-based features
        
        Args:
            timestamp: Series of timestamps
            
        Returns:
            DataFrame with temporal features
        """
        features = pd.DataFrame()
        
        features['hour'] = timestamp.dt.hour
        features['day_of_week'] = timestamp.dt.dayofweek
        features['is_weekend'] = (timestamp.dt.dayofweek >= 5).astype(int)
        
        return features
    
    def extract_metrics_features(self, metrics: pd.DataFrame) -> pd.DataFrame:
        """
        Extract metrics-based features
        
        Args:
            metrics: Metrics DataFrame with aggregated values
            
        Returns:
            DataFrame with metrics features
        """
        features = pd.DataFrame(index=metrics.index)
        
        # CPU features
        if 'cpu_percent' in metrics.columns:
            features['cpu_percent'] = metrics['cpu_percent'].fillna(0)
        else:
            features['cpu_percent'] = 0
        
        # Memory features
        if 'memory_percent' in metrics.columns:
            features['memory_percent'] = metrics['memory_percent'].fillna(0)
        else:
            features['memory_percent'] = 0
        
        # Disk features
        if 'disk_percent' in metrics.columns:
            features['disk_percent'] = metrics['disk_percent'].fillna(0)
        else:
            features['disk_percent'] = 0
        
        # Network features (convert to MB)
        if 'network_bytes_sent' in metrics.columns:
            features['network_mb_sent'] = (metrics['network_bytes_sent'].fillna(0) / 1024 / 1024)
        else:
            features['network_mb_sent'] = 0
        
        if 'network_bytes_recv' in metrics.columns:
            features['network_mb_recv'] = (metrics['network_bytes_recv'].fillna(0) / 1024 / 1024)
        else:
            features['network_mb_recv'] = 0
        
        return features
    
    def extract_process_features(self, processes: pd.DataFrame) -> pd.DataFrame:
        """
        Extract process-based features (aggregated per time window)
        
        Args:
            processes: Processes DataFrame
            
        Returns:
            DataFrame with process features
        """
        features = pd.DataFrame(index=processes.index)
        
        # Process count
        features['process_count'] = processes['process_count'].fillna(0)
        
        # Max CPU usage across processes
        features['max_process_cpu'] = processes['max_cpu'].fillna(0)
        
        # Max memory usage across processes
        features['max_process_memory'] = processes['max_memory'].fillna(0)
        
        return features
    
    def extract_command_features(self, commands: pd.DataFrame) -> pd.DataFrame:
        """
        Extract command-based features (aggregated per time window)
        
        Args:
            commands: Commands DataFrame
            
        Returns:
            DataFrame with command features
        """
        features = pd.DataFrame(index=commands.index)
        
        # Command count
        features['command_count'] = commands['command_count'].fillna(0)
        
        # Sudo command count
        features['sudo_count'] = commands['sudo_count'].fillna(0)
        
        return features
    
    def extract_log_features(self, logs: pd.DataFrame) -> pd.DataFrame:
        """
        Extract log-based features (aggregated per time window)
        
        Args:
            logs: Logs DataFrame
            
        Returns:
            DataFrame with log features
        """
        features = pd.DataFrame(index=logs.index)
        
        # Log count
        features['log_count'] = logs['log_count'].fillna(0)
        
        # Error/warning rate
        features['error_count'] = logs['error_count'].fillna(0)
        
        return features
    
    def aggregate_by_hour(self, logs: pd.DataFrame, metrics: pd.DataFrame, 
                          processes: pd.DataFrame, commands: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate all data by hour for feature extraction
        
        Args:
            logs: Raw logs DataFrame
            metrics: Raw metrics DataFrame
            processes: Raw processes DataFrame
            commands: Raw commands DataFrame
            
        Returns:
            Aggregated DataFrame with hourly time windows
        """
        print("\n📊 Aggregating data by hour...")
        
        aggregated_data = []
        
        # Get time range
        all_times = []
        if not metrics.empty:
            all_times.extend(metrics['timestamp'].tolist())
        if not logs.empty:
            all_times.extend(logs['timestamp'].tolist())
        
        if not all_times:
            raise ValueError("No data with timestamps found")
        
        min_time = min(all_times)
        max_time = max(all_times)
        
        # Create hourly time windows
        time_range = pd.date_range(start=min_time.floor('H'), 
                                   end=max_time.ceil('H'), 
                                   freq='H')
        
        print(f"   Time range: {min_time} to {max_time}")
        print(f"   Total hours: {len(time_range)}")
        
        for current_time in time_range:
            next_time = current_time + pd.Timedelta(hours=1)
            
            window_data = {'timestamp': current_time}
            
            # Aggregate metrics (average within hour)
            if not metrics.empty:
                hour_metrics = metrics[
                    (metrics['timestamp'] >= current_time) & 
                    (metrics['timestamp'] < next_time)
                ]
                
                if not hour_metrics.empty:
                    window_data['cpu_percent'] = hour_metrics['cpu_percent'].mean()
                    window_data['memory_percent'] = hour_metrics['memory_percent'].mean()
                    window_data['disk_percent'] = hour_metrics['disk_percent'].mean()
                    window_data['network_bytes_sent'] = hour_metrics['network_bytes_sent'].sum()
                    window_data['network_bytes_recv'] = hour_metrics['network_bytes_recv'].sum()
            
            # Aggregate processes (count and max resource usage)
            if not processes.empty:
                hour_processes = processes[
                    (processes['collected_at'] >= current_time) & 
                    (processes['collected_at'] < next_time)
                ]
                
                if not hour_processes.empty:
                    window_data['process_count'] = len(hour_processes)
                    window_data['max_cpu'] = hour_processes['cpu_percent'].max()
                    window_data['max_memory'] = hour_processes['memory_percent'].max()
            
            # Aggregate commands (count and sudo usage)
            if not commands.empty:
                hour_commands = commands[
                    (commands['timestamp'] >= current_time) & 
                    (commands['timestamp'] < next_time)
                ]
                
                if not hour_commands.empty:
                    window_data['command_count'] = len(hour_commands)
                    # Count sudo commands
                    sudo_commands = hour_commands[
                        hour_commands['command'].str.contains('sudo', case=False, na=False)
                    ]
                    window_data['sudo_count'] = len(sudo_commands)
            
            # Aggregate logs (count and error rate)
            if not logs.empty:
                hour_logs = logs[
                    (logs['timestamp'] >= current_time) & 
                    (logs['timestamp'] < next_time)
                ]
                
                if not hour_logs.empty:
                    window_data['log_count'] = len(hour_logs)
                    # Count error/warning logs (check both raw_data and raw_json columns)
                    log_column = 'raw_data' if 'raw_data' in hour_logs.columns else 'raw_json'
                    if log_column in hour_logs.columns:
                        error_logs = hour_logs[
                            hour_logs[log_column].str.contains(
                                'error|warning|critical|fail', 
                                case=False, 
                                na=False
                            )
                        ]
                        window_data['error_count'] = len(error_logs)
                    else:
                        window_data['error_count'] = 0
            
            aggregated_data.append(window_data)
        
        df = pd.DataFrame(aggregated_data)
        print(f"   ✅ Created {len(df)} hourly windows")
        
        return df
    
    def extract_all_features(self, logs: pd.DataFrame, metrics: pd.DataFrame,
                            processes: pd.DataFrame, commands: pd.DataFrame) -> pd.DataFrame:
        """
        Extract all features from raw data
        
        Args:
            logs: Raw logs DataFrame
            metrics: Raw metrics DataFrame
            processes: Raw processes DataFrame  
            commands: Raw commands DataFrame
            
        Returns:
            DataFrame with all features
        """
        print("\n" + "="*60)
        print("🔧 Extracting Features")
        print("="*60)
        
        # Aggregate data by hour
        hourly_data = self.aggregate_by_hour(logs, metrics, processes, commands)
        
        # Extract temporal features
        print("\n⏰ Extracting temporal features...")
        temporal_features = self.extract_temporal_features(hourly_data['timestamp'])
        
        # Extract metrics features
        print("📊 Extracting metrics features...")
        metrics_features = self.extract_metrics_features(hourly_data)
        
        # Extract process features
        print("⚙️  Extracting process features...")
        process_features = self.extract_process_features(hourly_data)
        
        # Extract command features
        print("💻 Extracting command features...")
        command_features = self.extract_command_features(hourly_data)
        
        # Extract log features
        print("📝 Extracting log features...")
        log_features = self.extract_log_features(hourly_data)
        
        # Combine all features
        features = pd.concat([
            hourly_data[['timestamp']],
            temporal_features,
            metrics_features,
            process_features,
            command_features,
            log_features
        ], axis=1)
        
        # Store feature names
        self.feature_names = [col for col in features.columns if col != 'timestamp']
        
        print(f"\n✅ Extracted {len(self.feature_names)} features:")
        for i, name in enumerate(self.feature_names, 1):
            print(f"   {i:2d}. {name}")
        
        print(f"\n✅ Total samples: {len(features)}")
        
        return features
