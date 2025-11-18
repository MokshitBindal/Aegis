#!/usr/bin/env python3
"""
Simulate Attack Scenarios and Test Model Detection

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import json
from datetime import datetime, timedelta

# Add src to path
import sys
sys.path.append(str(Path(__file__).parent / 'src'))

from feature_extractor import FeatureExtractor


def load_model():
    """Load trained model"""
    model = joblib.load("models/latest_model.pkl")
    scaler = joblib.load("models/latest_scaler.pkl")
    return model, scaler


def create_attack_scenario(scenario_name: str, baseline_features: dict):
    """
    Create synthetic attack scenarios based on normal baseline
    
    Args:
        scenario_name: Type of attack to simulate
        baseline_features: Normal feature values as baseline
    """
    # Start with baseline (normal behavior)
    attack_features = baseline_features.copy()
    
    if scenario_name == "fork_bomb":
        # Fork bomb: massive process creation
        attack_features['process_count'] = baseline_features['process_count'] * 10
        attack_features['max_process_cpu'] = 400.0
        attack_features['max_process_memory'] = 30.0
        attack_features['error_count'] = baseline_features['error_count'] * 5
        
    elif scenario_name == "cryptominer":
        # Cryptominer: sustained high CPU
        attack_features['max_process_cpu'] = 800.0  # Multiple cores maxed
        attack_features['cpu_percent'] = 95.0
        attack_features['process_count'] = baseline_features['process_count'] * 1.5
        
    elif scenario_name == "data_exfiltration":
        # Data exfiltration: high network traffic
        attack_features['network_mb_sent'] = baseline_features['network_mb_sent'] * 50
        attack_features['network_mb_recv'] = baseline_features['network_mb_recv'] * 10
        attack_features['command_count'] = baseline_features['command_count'] * 3
        
    elif scenario_name == "brute_force":
        # Brute force: many failed login attempts
        attack_features['log_count'] = baseline_features['log_count'] * 20
        attack_features['error_count'] = baseline_features['error_count'] * 30
        attack_features['command_count'] = baseline_features['command_count'] * 5
        attack_features['sudo_count'] = baseline_features['sudo_count'] * 10
        
    elif scenario_name == "privilege_escalation":
        # Privilege escalation: unusual sudo activity
        attack_features['sudo_count'] = baseline_features['sudo_count'] * 20
        attack_features['command_count'] = baseline_features['command_count'] * 8
        attack_features['error_count'] = baseline_features['error_count'] * 3
        
    elif scenario_name == "ddos":
        # DDoS: network and process flood
        attack_features['process_count'] = baseline_features['process_count'] * 15
        attack_features['network_mb_sent'] = baseline_features['network_mb_sent'] * 100
        attack_features['network_mb_recv'] = baseline_features['network_mb_recv'] * 100
        attack_features['log_count'] = baseline_features['log_count'] * 50
        
    elif scenario_name == "ransomware":
        # Ransomware: high disk activity + encryption
        attack_features['disk_percent'] = 95.0
        attack_features['process_count'] = baseline_features['process_count'] * 3
        attack_features['max_process_cpu'] = 600.0
        attack_features['error_count'] = baseline_features['error_count'] * 10
        
    elif scenario_name == "backdoor":
        # Backdoor: unusual process + network
        attack_features['process_count'] = baseline_features['process_count'] * 2
        attack_features['network_mb_sent'] = baseline_features['network_mb_sent'] * 10
        attack_features['command_count'] = baseline_features['command_count'] * 6
        attack_features['hour'] = 3  # 3 AM - unusual time
        
    return attack_features


def test_attacks():
    """Test model against various attack scenarios"""
    print("\n" + "="*70)
    print("🎯 ATTACK SCENARIO TESTING")
    print("="*70)
    
    # Load model
    print("\n📦 Loading model...")
    model, scaler = load_model()
    
    # Load baseline (calculate from predictions)
    print("📊 Loading baseline features...")
    predictions = pd.read_csv("predictions.csv")
    normal_samples = predictions[predictions['is_anomaly'] == 0]
    
    # Calculate baseline (mean of normal behavior)
    feature_cols = ['hour', 'day_of_week', 'is_weekend', 'cpu_percent', 
                   'memory_percent', 'disk_percent', 'network_mb_sent',
                   'network_mb_recv', 'process_count', 'max_process_cpu',
                   'max_process_memory', 'command_count', 'sudo_count',
                   'log_count', 'error_count']
    
    baseline = {}
    for col in feature_cols:
        if col in normal_samples.columns:
            baseline[col] = normal_samples[col].mean()
        else:
            baseline[col] = 0
    
    print(f"\n✅ Baseline calculated from {len(normal_samples)} normal samples")
    
    # Define attack scenarios
    attacks = [
        ("fork_bomb", "Fork Bomb - Process Explosion"),
        ("cryptominer", "Cryptominer - CPU Hijacking"),
        ("data_exfiltration", "Data Exfiltration - Network Spike"),
        ("brute_force", "Brute Force - Login Attacks"),
        ("privilege_escalation", "Privilege Escalation - Sudo Abuse"),
        ("ddos", "DDoS Attack - Resource Flood"),
        ("ransomware", "Ransomware - Encryption Activity"),
        ("backdoor", "Backdoor - Suspicious Persistence")
    ]
    
    results = []
    
    print("\n" + "="*70)
    print("🧪 TESTING ATTACK SCENARIOS")
    print("="*70)
    
    for attack_type, attack_name in attacks:
        # Create attack features
        attack_features = create_attack_scenario(attack_type, baseline)
        
        # Convert to DataFrame for prediction
        X = pd.DataFrame([attack_features])[feature_cols]
        X_scaled = scaler.transform(X)
        
        # Predict
        prediction = model.predict(X_scaled)[0]
        score = model.score_samples(X_scaled)[0]
        
        is_detected = (prediction == -1)
        
        # Store result
        results.append({
            'attack': attack_name,
            'detected': is_detected,
            'score': score,
            'severity': 'HIGH' if score < -0.6 else 'MEDIUM' if score < -0.5 else 'LOW'
        })
        
        # Print result
        status = "✅ DETECTED" if is_detected else "❌ MISSED"
        severity = results[-1]['severity']
        
        print(f"\n{'─'*70}")
        print(f"🎯 {attack_name}")
        print(f"{'─'*70}")
        print(f"Status: {status}")
        print(f"Anomaly Score: {score:.3f}")
        print(f"Severity: {severity}")
        
        # Show key indicators
        print(f"\nKey Indicators:")
        changed_features = []
        for feat, val in attack_features.items():
            if abs(val - baseline[feat]) > baseline[feat] * 0.5:  # 50% change
                change = ((val - baseline[feat]) / baseline[feat] * 100) if baseline[feat] > 0 else 0
                changed_features.append((feat, baseline[feat], val, change))
        
        # Sort by change magnitude
        changed_features.sort(key=lambda x: abs(x[3]), reverse=True)
        for feat, base_val, attack_val, change in changed_features[:5]:
            print(f"   • {feat}: {base_val:.1f} → {attack_val:.1f} ({change:+.0f}%)")
    
    # Summary
    print("\n" + "="*70)
    print("📊 DETECTION SUMMARY")
    print("="*70)
    
    detected = sum(1 for r in results if r['detected'])
    total = len(results)
    
    print(f"\n✅ Detection Rate: {detected}/{total} ({detected/total*100:.1f}%)")
    print(f"\nSeverity Breakdown:")
    
    for severity in ['HIGH', 'MEDIUM', 'LOW']:
        count = sum(1 for r in results if r['severity'] == severity)
        severity_detected = sum(1 for r in results if r['severity'] == severity and r['detected'])
        if count > 0:
            print(f"   {severity}: {severity_detected}/{count} detected ({severity_detected/count*100:.0f}%)")
    
    print(f"\n📋 Detailed Results:")
    print(f"\n{'Attack':<40} {'Detected':<10} {'Score':<10} {'Severity'}")
    print("─"*70)
    for r in results:
        detected_str = "✅ Yes" if r['detected'] else "❌ No"
        print(f"{r['attack']:<40} {detected_str:<10} {r['score']:<10.3f} {r['severity']}")
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv("attack_test_results.csv", index=False)
    print(f"\n💾 Results saved to: attack_test_results.csv")
    
    print("\n" + "="*70)
    print("✅ ATTACK TESTING COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_attacks()
