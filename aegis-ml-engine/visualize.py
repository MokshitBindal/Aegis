#!/usr/bin/env python3
"""
Visualize Anomaly Detection Results

Author: Mokshit Bindal
Date: November 18, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def visualize_results(predictions_file: str = "predictions.csv",
                     output_dir: str = "visualizations"):
    """
    Create visualizations of anomaly detection results
    
    Args:
        predictions_file: CSV file with predictions
        output_dir: Directory to save visualizations
    """
    print("\n" + "="*70)
    print("📊 VISUALIZING ANOMALY DETECTION RESULTS")
    print("="*70)
    
    # Load predictions
    print(f"\n📖 Loading predictions from {predictions_file}...")
    df = pd.read_csv(predictions_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"   ✅ Loaded {len(df):,} predictions")
    print(f"   Anomalies: {df['is_anomaly'].sum():,} ({df['is_anomaly'].mean()*100:.1f}%)")
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 1. Anomaly Score Timeline
    print("\n📈 Creating anomaly score timeline...")
    fig, ax = plt.subplots(figsize=(15, 6))
    
    # Plot all scores
    ax.plot(df['timestamp'], df['anomaly_score'], 
            linewidth=1, alpha=0.7, label='Anomaly Score')
    
    # Highlight anomalies
    anomalies = df[df['is_anomaly'] == 1]
    ax.scatter(anomalies['timestamp'], anomalies['anomaly_score'],
              color='red', s=100, alpha=0.6, label='Detected Anomalies', zorder=5)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Anomaly Score', fontsize=12)
    ax.set_title('Anomaly Detection Timeline', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    timeline_file = output_dir / "anomaly_timeline.png"
    plt.savefig(timeline_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved to {timeline_file}")
    plt.close()
    
    # 2. Anomaly Score Distribution
    print("\n📊 Creating score distribution...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Histogram
    normal_scores = df[df['is_anomaly'] == 0]['anomaly_score']
    anomaly_scores = df[df['is_anomaly'] == 1]['anomaly_score']
    
    ax1.hist(normal_scores, bins=30, alpha=0.6, label='Normal', color='green', edgecolor='black')
    ax1.hist(anomaly_scores, bins=15, alpha=0.6, label='Anomalies', color='red', edgecolor='black')
    ax1.set_xlabel('Anomaly Score', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Anomaly Score Distribution', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Box plot
    box_data = [normal_scores, anomaly_scores]
    bp = ax2.boxplot(box_data, labels=['Normal', 'Anomalies'], patch_artist=True)
    bp['boxes'][0].set_facecolor('lightgreen')
    bp['boxes'][1].set_facecolor('lightcoral')
    ax2.set_ylabel('Anomaly Score', fontsize=12)
    ax2.set_title('Score Comparison', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    dist_file = output_dir / "score_distribution.png"
    plt.savefig(dist_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved to {dist_file}")
    plt.close()
    
    # 3. Feature Heatmap for Anomalies
    print("\n🔥 Creating feature heatmap...")
    
    # Get top anomalies
    top_anomalies = df[df['is_anomaly'] == 1].nsmallest(10, 'anomaly_score')
    
    if len(top_anomalies) > 0:
        # Select feature columns (exclude timestamp, is_anomaly, anomaly_score)
        feature_cols = [col for col in df.columns 
                       if col not in ['timestamp', 'is_anomaly', 'anomaly_score']]
        
        # Create heatmap data
        heatmap_data = top_anomalies[feature_cols].T
        heatmap_data.columns = [f"Anomaly {i+1}" for i in range(len(top_anomalies))]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='YlOrRd', 
                   cbar_kws={'label': 'Feature Value'}, ax=ax)
        ax.set_title('Feature Values for Top 10 Anomalies', fontsize=14, fontweight='bold')
        ax.set_xlabel('Anomaly Instance', fontsize=12)
        ax.set_ylabel('Features', fontsize=12)
        
        plt.tight_layout()
        heatmap_file = output_dir / "anomaly_features_heatmap.png"
        plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved to {heatmap_file}")
        plt.close()
    
    # 4. Temporal Patterns
    print("\n⏰ Creating temporal pattern analysis...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Hour of day
    df['hour'] = df['timestamp'].dt.hour
    hour_anomalies = df.groupby('hour')['is_anomaly'].agg(['sum', 'count'])
    hour_anomalies['rate'] = hour_anomalies['sum'] / hour_anomalies['count'] * 100
    
    axes[0, 0].bar(hour_anomalies.index, hour_anomalies['rate'], color='coral', edgecolor='black')
    axes[0, 0].set_xlabel('Hour of Day', fontsize=11)
    axes[0, 0].set_ylabel('Anomaly Rate (%)', fontsize=11)
    axes[0, 0].set_title('Anomalies by Hour', fontsize=12, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # Day of week
    df['day_name'] = df['timestamp'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_anomalies = df.groupby('day_name')['is_anomaly'].agg(['sum', 'count'])
    day_anomalies['rate'] = day_anomalies['sum'] / day_anomalies['count'] * 100
    day_anomalies = day_anomalies.reindex([d for d in day_order if d in day_anomalies.index])
    
    axes[0, 1].bar(range(len(day_anomalies)), day_anomalies['rate'], color='skyblue', edgecolor='black')
    axes[0, 1].set_xticks(range(len(day_anomalies)))
    axes[0, 1].set_xticklabels([d[:3] for d in day_anomalies.index], rotation=45)
    axes[0, 1].set_xlabel('Day of Week', fontsize=11)
    axes[0, 1].set_ylabel('Anomaly Rate (%)', fontsize=11)
    axes[0, 1].set_title('Anomalies by Day', fontsize=12, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    # Process count over time
    if 'process_count' in df.columns:
        axes[1, 0].plot(df['timestamp'], df['process_count'], linewidth=1, alpha=0.7)
        axes[1, 0].scatter(anomalies['timestamp'], anomalies['process_count'],
                          color='red', s=50, alpha=0.6, zorder=5)
        axes[1, 0].set_xlabel('Time', fontsize=11)
        axes[1, 0].set_ylabel('Process Count', fontsize=11)
        axes[1, 0].set_title('Process Count Timeline', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)
        plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
    
    # CPU percent over time
    if 'cpu_percent' in df.columns:
        axes[1, 1].plot(df['timestamp'], df['cpu_percent'], linewidth=1, alpha=0.7, color='green')
        axes[1, 1].scatter(anomalies['timestamp'], anomalies['cpu_percent'],
                          color='red', s=50, alpha=0.6, zorder=5)
        axes[1, 1].set_xlabel('Time', fontsize=11)
        axes[1, 1].set_ylabel('CPU %', fontsize=11)
        axes[1, 1].set_title('CPU Usage Timeline', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)
        plt.setp(axes[1, 1].xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    temporal_file = output_dir / "temporal_patterns.png"
    plt.savefig(temporal_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved to {temporal_file}")
    plt.close()
    
    # 5. Feature Importance (based on anomaly correlation)
    print("\n🎯 Creating feature importance analysis...")
    
    feature_cols = [col for col in df.columns 
                   if col not in ['timestamp', 'is_anomaly', 'anomaly_score', 'hour', 'day_name']]
    
    correlations = []
    for col in feature_cols:
        if df[col].std() > 0:  # Only for features with variance
            corr = df[col].corr(df['is_anomaly'])
            correlations.append((col, abs(corr)))
    
    correlations.sort(key=lambda x: x[1], reverse=True)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    features = [c[0] for c in correlations]
    values = [c[1] for c in correlations]
    
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(values)))
    bars = ax.barh(features, values, color=colors, edgecolor='black')
    ax.set_xlabel('Correlation with Anomaly', fontsize=12)
    ax.set_title('Feature Importance for Anomaly Detection', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    importance_file = output_dir / "feature_importance.png"
    plt.savefig(importance_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved to {importance_file}")
    plt.close()
    
    # Summary
    print("\n" + "="*70)
    print("✅ VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\n📁 All visualizations saved to: {output_dir}/")
    print(f"\n📊 Generated visualizations:")
    print(f"   1. anomaly_timeline.png - Anomaly scores over time")
    print(f"   2. score_distribution.png - Score distributions")
    print(f"   3. anomaly_features_heatmap.png - Feature heatmap")
    print(f"   4. temporal_patterns.png - Time-based patterns")
    print(f"   5. feature_importance.png - Feature importance")
    print("="*70 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Visualize anomaly detection results"
    )
    parser.add_argument(
        '--predictions',
        type=str,
        default='predictions.csv',
        help='CSV file with predictions'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='visualizations',
        help='Directory to save visualizations'
    )
    
    args = parser.parse_args()
    
    try:
        visualize_results(
            predictions_file=args.predictions,
            output_dir=args.output_dir
        )
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
