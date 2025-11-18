"""
Real-Time Anomaly Detection API

Integrates with aegis-server for live detection

Author: Mokshit Bindal
Date: November 18, 2025
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime


class AnomalyDetector:
    """Real-time anomaly detection using trained Isolation Forest"""
    
    def __init__(self, model_dir: str = "models"):
        """
        Initialize detector with trained model
        
        Args:
            model_dir: Directory containing model files
        """
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.config = None
        self.feature_names = []
        self.load_model()
    
    def load_model(self):
        """Load trained model and configuration"""
        model_path = self.model_dir / "latest_model.pkl"
        scaler_path = self.model_dir / "latest_scaler.pkl"
        config_path = self.model_dir / "latest_config.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        import json
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.feature_names = self.config['features']
    
    def predict(self, features: Dict[str, float]) -> Tuple[bool, float, str]:
        """
        Predict if features represent anomalous behavior
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of (is_anomaly, anomaly_score, severity)
        """
        # Ensure all features present
        feature_values = []
        for feat_name in self.feature_names:
            feature_values.append(features.get(feat_name, 0))
        
        # Convert to DataFrame for prediction
        X = pd.DataFrame([feature_values], columns=self.feature_names)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]
        score = self.model.score_samples(X_scaled)[0]
        
        is_anomaly = (prediction == -1)
        
        # Determine severity
        if score < -0.6:
            severity = "HIGH"
        elif score < -0.5:
            severity = "MEDIUM"
        elif score < -0.4:
            severity = "LOW"
        else:
            severity = "NORMAL"
        
        return is_anomaly, float(score), severity
    
    def get_feature_contributions(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Get feature contributions to anomaly score
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Dictionary of feature contributions (normalized)
        """
        feature_values = []
        for feat_name in self.feature_names:
            feature_values.append(features.get(feat_name, 0))
        
        # Simple contribution: feature value relative to baseline
        contributions = {}
        for feat_name, feat_value in zip(self.feature_names, feature_values):
            # Normalize by feature scale
            if feat_value > 0:
                contributions[feat_name] = abs(feat_value)
        
        # Sort by contribution
        contributions = dict(sorted(contributions.items(), 
                                   key=lambda x: x[1], 
                                   reverse=True))
        
        return contributions
    
    def batch_predict(self, features_list: list) -> list:
        """
        Predict on batch of samples
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of (is_anomaly, score, severity) tuples
        """
        results = []
        for features in features_list:
            results.append(self.predict(features))
        return results
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        return {
            'algorithm': self.config['model_config']['algorithm'],
            'trained_at': self.config['trained_at'],
            'duration_days': self.config['duration_days'],
            'features': self.feature_names,
            'performance': self.config['performance']
        }


# Example usage for aegis-server integration
if __name__ == "__main__":
    # Initialize detector
    detector = AnomalyDetector()
    
    print("🤖 Anomaly Detector Loaded")
    print(f"   Model: {detector.config['model_config']['algorithm']}")
    print(f"   Trained: {detector.config['trained_at'][:10]}")
    print(f"   Features: {len(detector.feature_names)}")
    
    # Example: Detect on sample features
    sample_features = {
        'hour': 14,
        'day_of_week': 3,
        'is_weekend': 0,
        'cpu_percent': 45.2,
        'memory_percent': 62.1,
        'disk_percent': 35.8,
        'network_mb_sent': 125.3,
        'network_mb_recv': 89.7,
        'process_count': 8500,
        'max_process_cpu': 78.4,
        'max_process_memory': 12.3,
        'command_count': 15,
        'sudo_count': 2,
        'log_count': 120,
        'error_count': 8
    }
    
    print("\n📊 Testing detection on sample features...")
    is_anomaly, score, severity = detector.predict(sample_features)
    
    print(f"\n{'='*50}")
    print(f"Result: {'🔴 ANOMALY' if is_anomaly else '✅ NORMAL'}")
    print(f"Score: {score:.3f}")
    print(f"Severity: {severity}")
    
    if is_anomaly:
        print(f"\nTop Contributing Features:")
        contributions = detector.get_feature_contributions(sample_features)
        for feat, value in list(contributions.items())[:5]:
            print(f"   • {feat}: {value:.2f}")
    
    print("="*50)
