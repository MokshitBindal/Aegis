# ML Engine Scripts

This directory contains utility scripts for the Aegis ML Engine.

## Data Cleaning Script

### clean_data.py

Cleans and validates exported ML training data by:

- **Removing duplicates** based on key columns
- **Checking data integrity** (missing values, data types)
- **Creating cleaned versions** of CSV files
- **Generating detailed reports** on cleaning operations

#### Usage

```bash
# From the scripts directory
cd /path/to/aegis-ml-engine/scripts

# Clean data with default paths
python clean_data.py

# Specify custom data directory
python clean_data.py --data-dir /path/to/ml_data

# Specify custom output directory
python clean_data.py --data-dir ../aegis-server/ml_data --output-dir /path/to/output
```

#### Duplicate Detection Logic

Each file type has specific columns used to identify duplicates:

- **logs.csv**: `timestamp + agent_id + raw_json`
- **metrics.csv**: `timestamp + agent_id`
- **processes.csv**: `collected_at + agent_id + pid`
- **commands.csv**: `timestamp + agent_id + command`

When duplicates are found, the **first occurrence is kept** and subsequent duplicates are removed.

#### Output

The script creates:

- `cleaned/` directory with cleaned CSV files
  - `logs_clean.csv`
  - `metrics_clean.csv`
  - `processes_clean.csv`
  - `commands_clean.csv`
- `cleaning_report.json` with detailed statistics

#### Example Output

```
=== Cleaning logs.csv ===
📖 Reading logs.csv...
   Total rows: 50,000
   Checking for duplicates based on: ['timestamp', 'agent_id', 'raw_json']
   ❌ Found 1,234 duplicate rows (2.47%)
   ⚠️  Missing values found:
      - hostname: 15 (0.0%)
💾 Saving cleaned file to cleaned/logs_clean.csv...
✅ Logs cleaned: 50,000 → 48,766 rows

📊 DATA CLEANING REPORT
=======================================================
Total rows before: 150,000
Total rows after:  145,234
Duplicates removed: 4,766
Data reduction: 3.18%
```

#### When to Run

- **Weekly** during data collection phase (Phase 4)
- **Before feature engineering** (Phase 5)
- **After any data export issues** or collection problems
- **Before model training** to ensure clean training data

#### Requirements

```bash
pip install pandas
```

## Future Scripts

Additional scripts planned for this directory:

- `validate_features.py` - Validate feature distributions
- `train_baseline.py` - Train baseline model
- `evaluate_model.py` - Model performance evaluation
- `generate_attack_data.py` - Synthetic attack scenario generator
