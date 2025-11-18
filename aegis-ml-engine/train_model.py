#!/usr/bin/env python3
"""
Train Isolation Forest Model for Anomaly Detection

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import argparse
import json

# Add src to path
import sys
sys.path.append(str(Path(__file__).parent / 'src'))

from data_loader import DataLoader
from feature_extractor import FeatureExtractor


def train_model(data_dir: str = "../aegis-server/ml_data/cleaned", 
                contamination: float = 0.1,
                test_size: float = 0.2):
    """
    Train Isolation Forest model
    
    Args:
        data_dir: Directory with cleaned CSV files
        contamination: Expected proportion of anomalies (0.05 = 5%)
        test_size: Proportion of data for testing
    """
    print("\n" + "="*70)
    print("🤖 AEGIS SIEM - ANOMALY DETECTION MODEL TRAINING")
    print("="*70)
    print(f"\n📅 Training started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Load data
    print("\n" + "="*70)
    print("STEP 1: LOAD DATA")
    print("="*70)
    
    loader = DataLoader(data_dir)
    logs, metrics, processes, commands = loader.load_all()
    
    # Check data availability
    if metrics.empty:
        print("❌ Error: No metrics data available")
        return
    
    # Get time range
    start_time, end_time = loader.get_time_range(logs, metrics)
    duration = (end_time - start_time).total_seconds() / 86400  # days
    
    print(f"\n📊 Data Summary:")
    print(f"   Time range: {start_time} to {end_time}")
    print(f"   Duration: {duration:.1f} days")
    print(f"   Logs: {len(logs):,}")
    print(f"   Metrics: {len(metrics):,}")
    print(f"   Processes: {len(processes):,}")
    print(f"   Commands: {len(commands):,}")
    
    # 2. Extract features
    print("\n" + "="*70)
    print("STEP 2: FEATURE EXTRACTION")
    print("="*70)
    
    extractor = FeatureExtractor()
    features_df = extractor.extract_all_features(logs, metrics, processes, commands)
    
    # Separate timestamp from features
    timestamps = features_df['timestamp']
    X = features_df.drop('timestamp', axis=1)
    
    print(f"\n📊 Feature Matrix Shape: {X.shape}")
    print(f"   Samples: {X.shape[0]}")
    print(f"   Features: {X.shape[1]}")
    
    # Check for missing values
    missing = X.isnull().sum()
    if missing.any():
        print(f"\n⚠️  Missing values detected:")
        for col, count in missing[missing > 0].items():
            print(f"   - {col}: {count} ({count/len(X)*100:.1f}%)")
        print(f"\n   Filling missing values with 0...")
        X = X.fillna(0)
    
    # 3. Split data
    print("\n" + "="*70)
    print("STEP 3: TRAIN/TEST SPLIT")
    print("="*70)
    
    X_train, X_test, ts_train, ts_test = train_test_split(
        X, timestamps, test_size=test_size, shuffle=False  # Don't shuffle to preserve temporal order
    )
    
    print(f"\n📊 Data Split:")
    print(f"   Training samples: {len(X_train):,} ({(1-test_size)*100:.0f}%)")
    print(f"   Testing samples:  {len(X_test):,} ({test_size*100:.0f}%)")
    print(f"   Training period: {ts_train.min()} to {ts_train.max()}")
    print(f"   Testing period:  {ts_test.min()} to {ts_test.max()}")
    
    # 4. Scale features
    print("\n" + "="*70)
    print("STEP 4: FEATURE SCALING")
    print("="*70)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"\n✅ Features scaled using StandardScaler")
    print(f"   Mean: ~0.0, Std: ~1.0")
    
    # 5. Train model
    print("\n" + "="*70)
    print("STEP 5: TRAIN ISOLATION FOREST")
    print("="*70)
    
    print(f"\n🔧 Model Configuration:")
    print(f"   Algorithm: Isolation Forest")
    print(f"   Contamination: {contamination} ({contamination*100:.0f}% expected anomalies)")
    print(f"   Random state: 42")
    print(f"   n_estimators: 100")
    
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
        max_samples='auto',
        n_jobs=-1,
        verbose=0
    )
    
    print(f"\n🚀 Training model...")
    model.fit(X_train_scaled)
    print(f"✅ Model training complete!")
    
    # 6. Evaluate on test set
    print("\n" + "="*70)
    print("STEP 6: EVALUATE MODEL")
    print("="*70)
    
    # Predictions (-1 for anomaly, 1 for normal)
    train_pred = model.predict(X_train_scaled)
    test_pred = model.predict(X_test_scaled)
    
    # Anomaly scores (lower = more anomalous)
    train_scores = model.score_samples(X_train_scaled)
    test_scores = model.score_samples(X_test_scaled)
    
    # Count anomalies
    train_anomalies = (train_pred == -1).sum()
    test_anomalies = (test_pred == -1).sum()
    
    print(f"\n📊 Training Set Results:")
    print(f"   Normal samples: {(train_pred == 1).sum():,} ({(train_pred == 1).sum()/len(train_pred)*100:.1f}%)")
    print(f"   Anomalies: {train_anomalies:,} ({train_anomalies/len(train_pred)*100:.1f}%)")
    print(f"   Anomaly score range: [{train_scores.min():.3f}, {train_scores.max():.3f}]")
    print(f"   Anomaly score mean: {train_scores.mean():.3f}")
    
    print(f"\n📊 Test Set Results:")
    print(f"   Normal samples: {(test_pred == 1).sum():,} ({(test_pred == 1).sum()/len(test_pred)*100:.1f}%)")
    print(f"   Anomalies: {test_anomalies:,} ({test_anomalies/len(test_pred)*100:.1f}%)")
    print(f"   Anomaly score range: [{test_scores.min():.3f}, {test_scores.max():.3f}]")
    print(f"   Anomaly score mean: {test_scores.mean():.3f}")
    
    # Show some detected anomalies
    if test_anomalies > 0:
        print(f"\n🔍 Sample Anomalies Detected in Test Set:")
        anomaly_indices = np.where(test_pred == -1)[0][:5]  # First 5
        for idx in anomaly_indices:
            print(f"\n   Anomaly #{idx + 1}:")
            print(f"      Time: {ts_test.iloc[idx]}")
            print(f"      Score: {test_scores[idx]:.3f}")
            print(f"      Features:")
            for feat_name, feat_val in X_test.iloc[idx].items():
                if feat_val > 0:  # Only show non-zero features
                    print(f"         - {feat_name}: {feat_val:.2f}")
    
    # 7. Save model
    print("\n" + "="*70)
    print("STEP 7: SAVE MODEL")
    print("="*70)
    
    models_dir = Path(__file__).parent / 'models'
    models_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = models_dir / f'isolation_forest_{timestamp}.pkl'
    scaler_path = models_dir / f'scaler_{timestamp}.pkl'
    config_path = models_dir / f'config_{timestamp}.json'
    
    # Save model and scaler
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"\n💾 Model saved to: {model_path}")
    print(f"💾 Scaler saved to: {scaler_path}")
    
    # Save configuration
    config = {
        'trained_at': datetime.now().isoformat(),
        'data_dir': data_dir,
        'duration_days': duration,
        'samples': {
            'total': len(X),
            'train': len(X_train),
            'test': len(X_test)
        },
        'features': extractor.feature_names,
        'model_config': {
            'algorithm': 'IsolationForest',
            'contamination': contamination,
            'n_estimators': 100,
            'random_state': 42
        },
        'performance': {
            'train_anomalies': int(train_anomalies),
            'train_anomaly_rate': float(train_anomalies / len(train_pred)),
            'test_anomalies': int(test_anomalies),
            'test_anomaly_rate': float(test_anomalies / len(test_pred)),
            'train_score_mean': float(train_scores.mean()),
            'test_score_mean': float(test_scores.mean())
        },
        'file_paths': {
            'model': str(model_path),
            'scaler': str(scaler_path),
            'config': str(config_path)
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"💾 Config saved to: {config_path}")
    
    # Create symlinks to latest
    latest_model = models_dir / 'latest_model.pkl'
    latest_scaler = models_dir / 'latest_scaler.pkl'
    latest_config = models_dir / 'latest_config.json'
    
    for link, target in [(latest_model, model_path), 
                         (latest_scaler, scaler_path),
                         (latest_config, config_path)]:
        if link.exists():
            link.unlink()
        link.symlink_to(target.name)
    
    print(f"\n🔗 Created symlinks to latest model")
    
    # 8. Summary
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE")
    print("="*70)
    
    print(f"\n📊 Training Summary:")
    print(f"   Duration: {duration:.1f} days of data")
    print(f"   Samples: {len(X):,} hourly windows")
    print(f"   Features: {len(extractor.feature_names)}")
    print(f"   Model: Isolation Forest (100 trees)")
    print(f"   Test accuracy: {(test_pred == 1).sum()/len(test_pred)*100:.1f}% normal")
    
    print(f"\n🚀 Model ready for deployment!")
    print(f"   Use: models/latest_model.pkl")
    print(f"   Use: models/latest_scaler.pkl")
    
    print(f"\n📅 Training completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Train Isolation Forest model for anomaly detection"
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../aegis-server/ml_data/cleaned',
        help='Directory containing cleaned CSV files'
    )
    parser.add_argument(
        '--contamination',
        type=float,
        default=0.1,
        help='Expected proportion of anomalies (default: 0.1 = 10%%)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Proportion of data for testing (default: 0.2 = 20%%)'
    )
    
    args = parser.parse_args()
    
    try:
        train_model(
            data_dir=args.data_dir,
            contamination=args.contamination,
            test_size=args.test_size
        )
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
