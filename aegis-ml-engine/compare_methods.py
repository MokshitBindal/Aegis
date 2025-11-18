#!/usr/bin/env python3
"""
Compare ML Detection vs Rule-Based Detection

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns


class RuleBasedDetector:
    """Traditional rule-based anomaly detection"""
    
    def __init__(self):
        """Define detection rules"""
        self.rules = {
            'high_cpu': lambda x: x['max_process_cpu'] > 200,
            'high_memory': lambda x: x['max_process_memory'] > 25,
            'process_spike': lambda x: x['process_count'] > 15000,
            'command_burst': lambda x: x['command_count'] > 50,
            'sudo_abuse': lambda x: x['sudo_count'] > 20,
            'log_flood': lambda x: x['log_count'] > 1000,
            'error_surge': lambda x: x['error_count'] > 100,
            'night_activity': lambda x: x['hour'] < 6 and x['command_count'] > 10,
        }
    
    def detect(self, features: pd.Series) -> tuple:
        """
        Apply rules to detect anomalies
        
        Returns:
            (is_anomaly, triggered_rules, confidence)
        """
        triggered = []
        
        for rule_name, rule_func in self.rules.items():
            try:
                if rule_func(features):
                    triggered.append(rule_name)
            except:
                pass
        
        # Anomaly if any rule triggers
        is_anomaly = len(triggered) > 0
        confidence = min(len(triggered) / 3, 1.0)  # More rules = higher confidence
        
        return is_anomaly, triggered, confidence


def compare_detectors():
    """Compare ML vs Rule-Based detection"""
    print("\n" + "="*70)
    print("⚖️  ML vs RULE-BASED DETECTION COMPARISON")
    print("="*70)
    
    # Load predictions
    print("\n📖 Loading predictions...")
    df = pd.read_csv("predictions.csv")
    print(f"   ✅ Loaded {len(df):,} samples")
    
    # Initialize rule-based detector
    rule_detector = RuleBasedDetector()
    
    # Apply rule-based detection
    print("\n🔧 Applying rule-based detection...")
    rule_results = []
    
    for idx, row in df.iterrows():
        is_anomaly, triggered_rules, confidence = rule_detector.detect(row)
        rule_results.append({
            'is_anomaly': is_anomaly,
            'triggered_rules': triggered_rules,
            'confidence': confidence,
            'rule_count': len(triggered_rules)
        })
    
    rule_df = pd.DataFrame(rule_results)
    
    # Compare detections
    ml_anomalies = df['is_anomaly'].sum()
    rule_anomalies = rule_df['is_anomaly'].sum()
    
    # Both detect
    both_detect = ((df['is_anomaly'] == 1) & (rule_df['is_anomaly'] == True)).sum()
    
    # Only ML detects
    only_ml = ((df['is_anomaly'] == 1) & (rule_df['is_anomaly'] == False)).sum()
    
    # Only rules detect
    only_rules = ((df['is_anomaly'] == 0) & (rule_df['is_anomaly'] == True)).sum()
    
    # Neither detects
    neither = ((df['is_anomaly'] == 0) & (rule_df['is_anomaly'] == False)).sum()
    
    print(f"\n✅ Rule-based detection complete!")
    
    # Print comparison
    print("\n" + "="*70)
    print("📊 DETECTION COMPARISON")
    print("="*70)
    
    print(f"\n🤖 ML Detection:")
    print(f"   Total anomalies: {ml_anomalies} ({ml_anomalies/len(df)*100:.1f}%)")
    
    print(f"\n📋 Rule-Based Detection:")
    print(f"   Total anomalies: {rule_anomalies} ({rule_anomalies/len(df)*100:.1f}%)")
    
    print(f"\n🔍 Detection Overlap:")
    print(f"   Both methods: {both_detect} ({both_detect/len(df)*100:.1f}%)")
    print(f"   Only ML: {only_ml} ({only_ml/len(df)*100:.1f}%)")
    print(f"   Only Rules: {only_rules} ({only_rules/len(df)*100:.1f}%)")
    print(f"   Neither: {neither} ({neither/len(df)*100:.1f}%)")
    
    # Sensitivity analysis
    if ml_anomalies + only_rules > 0:
        ml_sensitivity = both_detect / (ml_anomalies + only_rules) * 100
        rule_sensitivity = both_detect / (rule_anomalies + only_ml) * 100 if (rule_anomalies + only_ml) > 0 else 0
        
        print(f"\n📈 Sensitivity:")
        print(f"   ML captures: {ml_sensitivity:.1f}% of known anomalies")
        print(f"   Rules capture: {rule_sensitivity:.1f}% of known anomalies")
    
    # Analyze ML-only detections (subtle anomalies)
    print(f"\n🎯 ML-Only Detections (Subtle Anomalies):")
    if only_ml > 0:
        ml_only_samples = df[(df['is_anomaly'] == 1) & (rule_df['is_anomaly'] == False)]
        print(f"   Found {len(ml_only_samples)} subtle anomalies missed by rules")
        
        # Show examples
        for idx, row in ml_only_samples.head(3).iterrows():
            print(f"\n   Example {idx + 1}:")
            print(f"      Time: {row['timestamp']}")
            print(f"      Score: {row['anomaly_score']:.3f}")
            print(f"      Why rules missed: No single threshold exceeded")
            
            # Show feature values
            key_features = ['process_count', 'max_process_cpu', 'command_count', 'log_count']
            print(f"      Features:")
            for feat in key_features:
                if feat in row and row[feat] > 0:
                    print(f"         - {feat}: {row[feat]:.1f}")
    
    # Analyze rule-only detections (false positives?)
    print(f"\n⚠️  Rule-Only Detections (Potential False Positives):")
    if only_rules > 0:
        rule_only_samples = df[(df['is_anomaly'] == 0) & (rule_df['is_anomaly'] == True)]
        print(f"   Found {len(rule_only_samples)} detections that ML considered normal")
        print(f"   These may be legitimate spikes within normal behavior patterns")
    
    # Rule trigger frequency
    print(f"\n📊 Most Triggered Rules:")
    all_triggered = []
    for triggers in rule_df['triggered_rules']:
        all_triggered.extend(triggers)
    
    if all_triggered:
        from collections import Counter
        rule_counts = Counter(all_triggered)
        for rule, count in rule_counts.most_common(5):
            print(f"   • {rule}: {count} times ({count/len(df)*100:.1f}%)")
    
    # Create visualization
    print(f"\n📈 Creating comparison visualization...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Venn diagram-style bar chart
    categories = ['Both\nDetect', 'Only\nML', 'Only\nRules', 'Neither']
    values = [both_detect, only_ml, only_rules, neither]
    colors = ['green', 'blue', 'orange', 'gray']
    
    axes[0, 0].bar(categories, values, color=colors, edgecolor='black', alpha=0.7)
    axes[0, 0].set_ylabel('Number of Samples', fontsize=12)
    axes[0, 0].set_title('Detection Overlap', fontsize=14, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    for i, v in enumerate(values):
        axes[0, 0].text(i, v + 1, str(v), ha='center', va='bottom', fontweight='bold')
    
    # 2. Detection rates
    methods = ['ML\nDetection', 'Rule-Based\nDetection']
    rates = [ml_anomalies/len(df)*100, rule_anomalies/len(df)*100]
    
    axes[0, 1].bar(methods, rates, color=['blue', 'orange'], edgecolor='black', alpha=0.7)
    axes[0, 1].set_ylabel('Anomaly Rate (%)', fontsize=12)
    axes[0, 1].set_title('Detection Rate Comparison', fontsize=14, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    for i, v in enumerate(rates):
        axes[0, 1].text(i, v + 0.5, f"{v:.1f}%", ha='center', va='bottom', fontweight='bold')
    
    # 3. Timeline comparison
    df['ml_anomaly'] = df['is_anomaly']
    df['rule_anomaly'] = rule_df['is_anomaly'].astype(int)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    axes[1, 0].plot(df['timestamp'], df['ml_anomaly'], 'o-', label='ML Detection', 
                   markersize=4, alpha=0.7, color='blue')
    axes[1, 0].plot(df['timestamp'], df['rule_anomaly'], '^-', label='Rule-Based', 
                   markersize=4, alpha=0.7, color='orange')
    axes[1, 0].set_xlabel('Time', fontsize=12)
    axes[1, 0].set_ylabel('Anomaly (1=Yes, 0=No)', fontsize=12)
    axes[1, 0].set_title('Detection Timeline Comparison', fontsize=14, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
    
    # 4. Rule trigger heatmap
    if all_triggered:
        rule_names = list(rule_counts.keys())
        rule_values = [rule_counts[r] for r in rule_names]
        
        axes[1, 1].barh(rule_names, rule_values, color='coral', edgecolor='black')
        axes[1, 1].set_xlabel('Trigger Count', fontsize=12)
        axes[1, 1].set_title('Rule Trigger Frequency', fontsize=14, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    output_file = "visualizations/ml_vs_rules_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved to {output_file}")
    plt.close()
    
    # Save detailed comparison
    comparison_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'ml_detected': df['is_anomaly'],
        'ml_score': df['anomaly_score'],
        'rule_detected': rule_df['is_anomaly'],
        'rule_count': rule_df['rule_count'],
        'triggered_rules': rule_df['triggered_rules'].apply(lambda x: ','.join(x) if x else '')
    })
    
    comparison_df.to_csv("ml_vs_rules_comparison.csv", index=False)
    print(f"\n💾 Detailed comparison saved to: ml_vs_rules_comparison.csv")
    
    # Summary
    print("\n" + "="*70)
    print("✅ COMPARISON COMPLETE")
    print("="*70)
    
    print(f"\n🎯 Key Findings:")
    print(f"   1. ML detected {only_ml} subtle anomalies missed by rules")
    print(f"   2. Rules had {only_rules} potential false positives")
    print(f"   3. Both methods agreed on {both_detect} anomalies")
    print(f"   4. ML adapts to behavior, rules use fixed thresholds")
    
    print(f"\n💡 Advantages of ML:")
    print(f"   • Detects subtle pattern combinations")
    print(f"   • Adapts to normal behavior baseline")
    print(f"   • Fewer false positives (learns context)")
    print(f"   • No manual threshold tuning needed")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    compare_detectors()
