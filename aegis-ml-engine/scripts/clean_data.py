#!/usr/bin/env python3
"""
Data Cleaning Script for ML Training Data

This script:
1. Checks exported CSV files for duplicates
2. Removes duplicate rows based on key columns
3. Validates data integrity (missing values, data types)
4. Creates cleaned versions of the files
5. Generates a cleaning report

Author: Mokshit Bindal
Date: November 13, 2025
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import argparse


class DataCleaner:
    """Cleans and validates exported ML data"""
    
    def __init__(self, data_dir: str, output_dir: str = None):
        """
        Initialize data cleaner
        
        Args:
            data_dir: Directory containing raw exported CSV files
            output_dir: Directory for cleaned files (default: data_dir/cleaned)
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir) if output_dir else self.data_dir / "cleaned"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'files_processed': {},
            'total_duplicates_removed': 0,
            'total_rows_before': 0,
            'total_rows_after': 0
        }
    
    def clean_logs(self):
        """Clean logs.csv - remove TRUE duplicates (same timestamp + content)
        
        Note: Repeated commands at different times are KEPT as they represent
        normal behavioral patterns needed for ML training.
        """
        print("\n=== Cleaning logs.csv ===")
        
        csv_file = self.data_dir / "logs.csv"
        if not csv_file.exists():
            print(f"❌ File not found: {csv_file}")
            return
        
        # Read CSV
        print(f"📖 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        rows_before = len(df)
        print(f"   Total rows: {rows_before:,}")
        
        # ONLY remove true duplicates: exact same timestamp + agent_id + content
        # Repeated commands at different times are NORMAL BEHAVIOR - keep them!
        duplicate_cols = ['timestamp', 'agent_id', 'raw_json']
        
        # Check which columns exist
        available_cols = [col for col in duplicate_cols if col in df.columns]
        if not available_cols:
            print("⚠️  Warning: No key columns found for duplicate detection")
            available_cols = df.columns.tolist()[:3]
        
        print(f"   Checking for TRUE duplicates (same timestamp + content)...")
        print(f"   Note: Repeated commands at different times are KEPT (normal behavior)")
        duplicates = df.duplicated(subset=available_cols, keep='first')
        duplicates_count = duplicates.sum()
        
        if duplicates_count > 0:
            print(f"   ⚠️  Found {duplicates_count:,} TRUE duplicate rows ({duplicates_count/rows_before*100:.2f}%)")
            print(f"   These are exact copies (same timestamp) - safe to remove")
            df_clean = df[~duplicates].copy()
        else:
            print(f"   ✅ No true duplicates found!")
            df_clean = df.copy()
        
        rows_after = len(df_clean)
        
        # Check for missing values
        missing = df_clean.isnull().sum()
        if missing.any():
            print(f"   ⚠️  Missing values found:")
            for col, count in missing[missing > 0].items():
                print(f"      - {col}: {count} ({count/rows_after*100:.1f}%)")
        
        # Save cleaned file
        output_file = self.output_dir / "logs_clean.csv"
        print(f"💾 Saving cleaned file to {output_file}...")
        df_clean.to_csv(output_file, index=False)
        
        # Update report
        self.report['files_processed']['logs'] = {
            'rows_before': rows_before,
            'rows_after': rows_after,
            'duplicates_removed': duplicates_count,
            'missing_values': missing[missing > 0].to_dict() if missing.any() else {}
        }
        self.report['total_rows_before'] += rows_before
        self.report['total_rows_after'] += rows_after
        self.report['total_duplicates_removed'] += duplicates_count
        
        print(f"✅ Logs cleaned: {rows_before:,} → {rows_after:,} rows")
    
    def clean_metrics(self):
        """Clean metrics.csv - remove duplicates based on timestamp + agent_id"""
        print("\n=== Cleaning metrics.csv ===")
        
        csv_file = self.data_dir / "metrics.csv"
        if not csv_file.exists():
            print(f"❌ File not found: {csv_file}")
            return
        
        # Read CSV
        print(f"📖 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        rows_before = len(df)
        print(f"   Total rows: {rows_before:,}")
        
        # Check for duplicates (metrics with same timestamp and agent should be unique)
        duplicate_cols = ['timestamp', 'agent_id']
        available_cols = [col for col in duplicate_cols if col in df.columns]
        
        print(f"   Checking for duplicates based on: {available_cols}")
        duplicates = df.duplicated(subset=available_cols, keep='first')
        duplicates_count = duplicates.sum()
        
        if duplicates_count > 0:
            print(f"   ❌ Found {duplicates_count:,} duplicate rows ({duplicates_count/rows_before*100:.2f}%)")
            df_clean = df[~duplicates].copy()
        else:
            print(f"   ✅ No duplicates found!")
            df_clean = df.copy()
        
        rows_after = len(df_clean)
        
        # Check for missing values
        missing = df_clean.isnull().sum()
        if missing.any():
            print(f"   ⚠️  Missing values found:")
            for col, count in missing[missing > 0].items():
                print(f"      - {col}: {count} ({count/rows_after*100:.1f}%)")
        
        # Save cleaned file
        output_file = self.output_dir / "metrics_clean.csv"
        print(f"💾 Saving cleaned file to {output_file}...")
        df_clean.to_csv(output_file, index=False)
        
        # Update report
        self.report['files_processed']['metrics'] = {
            'rows_before': rows_before,
            'rows_after': rows_after,
            'duplicates_removed': duplicates_count,
            'missing_values': missing[missing > 0].to_dict() if missing.any() else {}
        }
        self.report['total_rows_before'] += rows_before
        self.report['total_rows_after'] += rows_after
        self.report['total_duplicates_removed'] += duplicates_count
        
        print(f"✅ Metrics cleaned: {rows_before:,} → {rows_after:,} rows")
    
    def clean_processes(self):
        """Clean processes.csv - remove duplicates based on collected_at + agent_id + pid"""
        print("\n=== Cleaning processes.csv ===")
        
        csv_file = self.data_dir / "processes.csv"
        if not csv_file.exists():
            print(f"❌ File not found: {csv_file}")
            return
        
        # Read CSV
        print(f"📖 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        rows_before = len(df)
        print(f"   Total rows: {rows_before:,}")
        
        # Check for duplicates (processes with same timestamp, agent, and pid)
        duplicate_cols = ['collected_at', 'agent_id', 'pid']
        available_cols = [col for col in duplicate_cols if col in df.columns]
        
        print(f"   Checking for duplicates based on: {available_cols}")
        duplicates = df.duplicated(subset=available_cols, keep='first')
        duplicates_count = duplicates.sum()
        
        if duplicates_count > 0:
            print(f"   ❌ Found {duplicates_count:,} duplicate rows ({duplicates_count/rows_before*100:.2f}%)")
            df_clean = df[~duplicates].copy()
        else:
            print(f"   ✅ No duplicates found!")
            df_clean = df.copy()
        
        rows_after = len(df_clean)
        
        # Check for missing values
        missing = df_clean.isnull().sum()
        if missing.any():
            print(f"   ⚠️  Missing values found:")
            for col, count in missing[missing > 0].items():
                print(f"      - {col}: {count} ({count/rows_after*100:.1f}%)")
        
        # Save cleaned file
        output_file = self.output_dir / "processes_clean.csv"
        print(f"💾 Saving cleaned file to {output_file}...")
        df_clean.to_csv(output_file, index=False)
        
        # Update report
        self.report['files_processed']['processes'] = {
            'rows_before': rows_before,
            'rows_after': rows_after,
            'duplicates_removed': duplicates_count,
            'missing_values': missing[missing > 0].to_dict() if missing.any() else {}
        }
        self.report['total_rows_before'] += rows_before
        self.report['total_rows_after'] += rows_after
        self.report['total_duplicates_removed'] += duplicates_count
        
        print(f"✅ Processes cleaned: {rows_before:,} → {rows_after:,} rows")
    
    def clean_commands(self):
        """Clean commands.csv - remove TRUE duplicates (same timestamp)
        
        Note: Same command executed at different times is NORMAL - that's your
        behavioral pattern! Only remove exact duplicates at the same timestamp.
        """
        print("\n=== Cleaning commands.csv ===")
        
        csv_file = self.data_dir / "commands.csv"
        if not csv_file.exists():
            print(f"❌ File not found: {csv_file}")
            return
        
        # Read CSV
        print(f"📖 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        rows_before = len(df)
        print(f"   Total rows: {rows_before:,}")
        
        # ONLY remove true duplicates: exact same timestamp + agent_id + command
        # Repeated commands at different times show your normal usage patterns!
        duplicate_cols = ['timestamp', 'agent_id', 'command']
        available_cols = [col for col in duplicate_cols if col in df.columns]
        
        print(f"   Checking for TRUE duplicates (same timestamp)...")
        print(f"   Note: Same command at different times is KEPT (your behavioral pattern)")
        duplicates = df.duplicated(subset=available_cols, keep='first')
        duplicates_count = duplicates.sum()
        
        if duplicates_count > 0:
            print(f"   ⚠️  Found {duplicates_count:,} TRUE duplicate rows ({duplicates_count/rows_before*100:.2f}%)")
            print(f"   These are exact copies (same timestamp) - safe to remove")
            df_clean = df[~duplicates].copy()
        else:
            print(f"   ✅ No true duplicates found!")
            df_clean = df.copy()
        
        rows_after = len(df_clean)
        
        # Check for missing values
        missing = df_clean.isnull().sum()
        if missing.any():
            print(f"   ⚠️  Missing values found:")
            for col, count in missing[missing > 0].items():
                print(f"      - {col}: {count} ({count/rows_after*100:.1f}%)")
        
        # Save cleaned file
        output_file = self.output_dir / "commands_clean.csv"
        print(f"💾 Saving cleaned file to {output_file}...")
        df_clean.to_csv(output_file, index=False)
        
        # Update report
        self.report['files_processed']['commands'] = {
            'rows_before': rows_before,
            'rows_after': rows_after,
            'duplicates_removed': duplicates_count,
            'missing_values': missing[missing > 0].to_dict() if missing.any() else {}
        }
        self.report['total_rows_before'] += rows_before
        self.report['total_rows_after'] += rows_after
        self.report['total_duplicates_removed'] += duplicates_count
        
        print(f"✅ Commands cleaned: {rows_before:,} → {rows_after:,} rows")
    
    def generate_report(self):
        """Generate cleaning report"""
        print("\n" + "="*60)
        print("📊 DATA CLEANING REPORT")
        print("="*60)
        
        print(f"\n🕐 Timestamp: {self.report['timestamp']}")
        print(f"📁 Input directory: {self.data_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total rows before: {self.report['total_rows_before']:,}")
        print(f"   Total rows after:  {self.report['total_rows_after']:,}")
        print(f"   TRUE duplicates removed: {self.report['total_duplicates_removed']:,}")
        
        if self.report['total_rows_before'] > 0:
            reduction = (1 - self.report['total_rows_after'] / self.report['total_rows_before']) * 100
            print(f"   Data reduction: {reduction:.2f}%")
        
        print(f"\n💡 Note: Repeated commands/logs at DIFFERENT times are KEPT")
        print(f"   → These show your normal behavioral patterns")
        print(f"   → Essential for ML training to learn what's normal!")
        print(f"   → Only removed: exact copies at the SAME timestamp")
        
        print(f"\n📋 Files Processed: {len(self.report['files_processed'])}")
        
        for file_type, stats in self.report['files_processed'].items():
            print(f"\n   {file_type.upper()}:")
            print(f"      Before: {stats['rows_before']:,} rows")
            print(f"      After:  {stats['rows_after']:,} rows")
            print(f"      TRUE duplicates: {stats['duplicates_removed']:,}")
            
            if stats['missing_values']:
                print(f"      Missing values:")
                for col, count in stats['missing_values'].items():
                    print(f"         - {col}: {count}")
        
        # Save report to JSON
        import json
        report_file = self.output_dir / "cleaning_report.json"
        
        # Convert numpy/pandas types to native Python types
        def convert_types(obj):
            if isinstance(obj, dict):
                return {key: convert_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy/pandas types
                return obj.item()
            return obj
        
        with open(report_file, 'w') as f:
            json.dump(convert_types(self.report), f, indent=2)
        
        print(f"\n💾 Full report saved to: {report_file}")
        print("="*60)
    
    def run(self):
        """Run full cleaning pipeline"""
        print("\n" + "="*60)
        print("🧹 Starting Data Cleaning Process")
        print("="*60)
        
        # Clean all file types
        self.clean_logs()
        self.clean_metrics()
        self.clean_processes()
        self.clean_commands()
        
        # Generate report
        self.generate_report()
        
        print("\n✅ Data cleaning complete!")
        print(f"📁 Cleaned files available in: {self.output_dir}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Clean and validate ML training data exports"
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../../aegis-server/ml_data',
        help='Directory containing raw CSV exports (default: ../../aegis-server/ml_data)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory for cleaned files (default: data-dir/cleaned)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = Path(__file__).parent
    data_dir = (script_dir / args.data_dir).resolve()
    output_dir = (script_dir / args.output_dir).resolve() if args.output_dir else None
    
    # Check if data directory exists
    if not data_dir.exists():
        print(f"❌ Error: Data directory not found: {data_dir}")
        print(f"\nPlease ensure ML data has been exported first.")
        print(f"You can trigger an export from the dashboard or API:")
        print(f"  POST http://localhost:8000/api/ml-data/export/manual")
        return 1
    
    # Run cleaning
    cleaner = DataCleaner(str(data_dir), str(output_dir) if output_dir else None)
    cleaner.run()
    
    return 0


if __name__ == "__main__":
    exit(main())
