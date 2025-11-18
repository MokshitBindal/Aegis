#!/usr/bin/env python3
"""
Evaluate and Predict with Trained Model

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
import argparse
from datetime import datetime

# Add src to path
import sys
sys.path.append(str(Path(__file__).parent / 'src'))

from data_loader import DataLoader
from feature_extractor import FeatureExtractor


def load_model(model_dir: str = "models"):
    """Load the latest trained model"""
    model_dir = Path(model_dir)
    
    model_path = model_dir / "latest_model.pkl"
    scaler_path = model_dir / "latest_scaler.pkl"
    config_path = model_dir / "latest_config.json"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    print(f"📦 Loading model from {model_path}...")
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"✅ Model loaded successfully!")
    print(f"   Trained: {config['trained_at']}")
    print(f"   Duration: {config['duration_days']:.1f} days")
    print(f"   Features: {len(config['features'])}")
    
    return model, scaler, config


def predict(data_dir: str = "../aegis-server/ml_data/cleaned", 
           model_dir: str = "models",
           output_file: str = None):
    """
    Make predictions on data
    
    Args:
        data_dir: Directory with cleaned CSV files
        model_dir: Directory with trained model
        output_file: Optional CSV file to save predictions
    """
    print("\n" + "="*70)
    print("🔮 ANOMALY DETECTION - PREDICTION")
    print("="*70)
    
    # Load model
    model, scaler, config = load_model(model_dir)
    
    # Load data
    print("\n" + "="*70)
    print("📊 Loading Data")
    print("="*70)
    
    loader = DataLoader(data_dir)
    logs, metrics, processes, commands = loader.load_all()
    
    # Extract features
    print("\n" + "="*70)
    print("🔧 Extracting Features")
    print("="*70)
    
    extractor = FeatureExtractor()
    features_df = extractor.extract_all_features(logs, metrics, processes, commands)
    
    timestamps = features_df['timestamp']
    X = features_df.drop('timestamp', axis=1)
    X = X.fillna(0)
    
    # Scale features
    X_scaled = scaler.transform(X)
    
    # Make predictions
    print("\n" + "="*70)
    print("🔮 Making Predictions")
    print("="*70)
    
    predictions = model.predict(X_scaled)
    scores = model.score_samples(X_scaled)
    
    # Add predictions to dataframe
    results = pd.DataFrame({
        'timestamp': timestamps,
        'is_anomaly': (predictions == -1).astype(int),
        'anomaly_score': scores
    })
    
    # Merge with features
    results = pd.concat([results, X.reset_index(drop=True)], axis=1)
    
    # Statistics
    anomaly_count = (predictions == -1).sum()
    anomaly_rate = anomaly_count / len(predictions) * 100
    
    print(f"\n📊 Prediction Results:")
    print(f"   Total samples: {len(predictions):,}")
    print(f"   Normal: {(predictions == 1).sum():,} ({(predictions == 1).sum()/len(predictions)*100:.1f}%)")
    print(f"   Anomalies: {anomaly_count:,} ({anomaly_rate:.1f}%)")
    print(f"   Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    print(f"   Score mean: {scores.mean():.3f}")
    
    # Show anomalies
    if anomaly_count > 0:
        print(f"\n🚨 Detected Anomalies:")
        anomalies = results[results['is_anomaly'] == 1].sort_values('anomaly_score')
        
        for idx, row in anomalies.head(10).iterrows():
            print(f"\n   🔴 {row['timestamp']}")
            print(f"      Score: {row['anomaly_score']:.3f}")
            
            # Show top contributing features (non-zero)
            features = {k: v for k, v in row.items() 
                       if k not in ['timestamp', 'is_anomaly', 'anomaly_score'] and v > 0}
            if features:
                print(f"      Top features:")
                sorted_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                for feat_name, feat_val in sorted_features:
                    print(f"         - {feat_name}: {feat_val:.2f}")
    
    # Save results
    if output_file:
        output_path = Path(output_file)
        results.to_csv(output_path, index=False)
        print(f"\n💾 Predictions saved to: {output_path}")
    
    print("\n" + "="*70)
    print("✅ Prediction Complete")
    print("="*70 + "\n")
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Make predictions with trained anomaly detection model"
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../aegis-server/ml_data/cleaned',
        help='Directory containing cleaned CSV files'
    )
    parser.add_argument(
        '--model-dir',
        type=str,
        default='models',
        help='Directory containing trained model'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='predictions.csv',
        help='Output CSV file for predictions'
    )
    
    args = parser.parse_args()
    
    try:
        predict(
            data_dir=args.data_dir,
            model_dir=args.model_dir,
            output_file=args.output
        )
    except Exception as e:
        print(f"\n❌ Error during prediction: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
