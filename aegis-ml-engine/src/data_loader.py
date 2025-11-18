"""
Data Loader - Load and prepare cleaned ML data for training

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


class DataLoader:
    """Load and prepare cleaned CSV data for ML training"""
    
    def __init__(self, data_dir: str = "../aegis-server/ml_data/cleaned"):
        """
        Initialize data loader
        
        Args:
            data_dir: Directory containing cleaned CSV files
        """
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
    
    def load_logs(self) -> pd.DataFrame:
        """Load cleaned logs"""
        file_path = self.data_dir / "logs_clean.csv"
        if not file_path.exists():
            print(f"⚠️  Warning: {file_path} not found")
            return pd.DataFrame()
        
        print(f"📖 Loading logs from {file_path}...")
        df = pd.read_csv(file_path)
        
        # Parse timestamp (ISO8601 format with timezone)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
        
        print(f"   ✅ Loaded {len(df):,} log entries")
        return df
    
    def load_metrics(self) -> pd.DataFrame:
        """Load cleaned metrics"""
        file_path = self.data_dir / "metrics_clean.csv"
        if not file_path.exists():
            print(f"⚠️  Warning: {file_path} not found")
            return pd.DataFrame()
        
        print(f"📖 Loading metrics from {file_path}...")
        df = pd.read_csv(file_path)
        
        # Parse timestamp (ISO8601 format with timezone)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
        
        print(f"   ✅ Loaded {len(df):,} metric samples")
        return df
    
    def load_processes(self) -> pd.DataFrame:
        """Load cleaned processes"""
        file_path = self.data_dir / "processes_clean.csv"
        if not file_path.exists():
            print(f"⚠️  Warning: {file_path} not found")
            return pd.DataFrame()
        
        print(f"📖 Loading processes from {file_path}...")
        df = pd.read_csv(file_path)
        
        # Parse timestamp (ISO8601 format with timezone)
        df['collected_at'] = pd.to_datetime(df['collected_at'], format='ISO8601')
        
        print(f"   ✅ Loaded {len(df):,} process records")
        return df
    
    def load_commands(self) -> pd.DataFrame:
        """Load cleaned commands"""
        file_path = self.data_dir / "commands_clean.csv"
        if not file_path.exists():
            print(f"⚠️  Warning: {file_path} not found")
            return pd.DataFrame()
        
        print(f"📖 Loading commands from {file_path}...")
        df = pd.read_csv(file_path)
        
        # Parse timestamp (ISO8601 format with timezone)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
        
        print(f"   ✅ Loaded {len(df):,} commands")
        return df
    
    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load all data files
        
        Returns:
            Tuple of (logs, metrics, processes, commands) DataFrames
        """
        print("\n" + "="*60)
        print("📦 Loading All Data Files")
        print("="*60)
        
        logs = self.load_logs()
        metrics = self.load_metrics()
        processes = self.load_processes()
        commands = self.load_commands()
        
        print("\n" + "="*60)
        print("✅ Data Loading Complete")
        print("="*60)
        
        return logs, metrics, processes, commands
    
    def get_time_range(self, logs: pd.DataFrame, metrics: pd.DataFrame) -> Tuple[datetime, datetime]:
        """
        Get overall time range of data
        
        Args:
            logs: Logs DataFrame
            metrics: Metrics DataFrame
            
        Returns:
            Tuple of (start_time, end_time)
        """
        times = []
        
        if not logs.empty:
            times.extend([logs['timestamp'].min(), logs['timestamp'].max()])
        
        if not metrics.empty:
            times.extend([metrics['timestamp'].min(), metrics['timestamp'].max()])
        
        if not times:
            return None, None
        
        return min(times), max(times)
