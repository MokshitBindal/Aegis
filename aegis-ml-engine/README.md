# Aegis ML Engine

**Purpose:** Machine Learning engine for behavioral anomaly detection in the Aegis SIEM system.

**Author:** Mokshit Bindal  
**Created:** November 13, 2025

---

## 📁 Directory Structure

```text
aegis-ml-engine/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.yaml                  # ML configuration
├── data/                        # Training data (exported from server)
│   ├── raw/                     # Raw CSV/JSON exports
│   ├── processed/               # Preprocessed feature vectors
│   └── labeled/                 # Labeled datasets for supervised learning
├── models/                      # Trained models
│   ├── isolation_forest.pkl     # Isolation Forest model
│   ├── baseline_profiles.json   # Device baseline profiles
│   └── model_metadata.json      # Model version and metrics
├── notebooks/                   # Jupyter notebooks for exploration
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_model_evaluation.ipynb
├── src/                         # Source code
│   ├── __init__.py
│   ├── data_loader.py           # Load exported data
│   ├── feature_extractor.py     # Extract features from raw data
│   ├── baseline_learner.py      # Learn normal behavior baselines
│   ├── anomaly_detector.py      # Isolation Forest implementation
│   ├── model_trainer.py         # Training pipeline
│   └── evaluator.py             # Model evaluation metrics
├── scripts/                     # Utility scripts
│   ├── train_model.py           # Main training script
│   ├── evaluate_model.py        # Evaluation script
│   └── export_model.py          # Export model for deployment
└── tests/                       # Unit tests
    ├── test_feature_extractor.py
    └── test_anomaly_detector.py
```

---

## 🎯 Implementation Plan

### **Phase 1: Data Collection & Preparation** (Current)

- ✅ Set up data export system in Aegis Server
- ✅ Configure auto-export thresholds
- ⏳ Collect 2-4 weeks of normal behavior data
- ⏳ Export labeled datasets

### **Phase 2: Feature Engineering** (Next)

- [ ] Load exported CSV/JSON data
- [ ] Extract relevant features from logs, metrics, processes, commands
- [ ] Create feature vectors (10-15 key features)
- [ ] Normalize and scale features
- [ ] Save processed features

### **Phase 3: Baseline Learning**

- [ ] Analyze normal behavior patterns
- [ ] Calculate statistical baselines (mean, std, p95, p99)
- [ ] Identify common processes and commands
- [ ] Save baseline profiles per device

### **Phase 4: Model Training**

- [ ] Train Isolation Forest on normal behavior
- [ ] Tune hyperparameters (contamination, n_estimators)
- [ ] Validate on held-out normal data
- [ ] Optimize detection threshold

### **Phase 5: Model Evaluation**

- [ ] Create attack scenario test cases
- [ ] Calculate precision, recall, F1-score
- [ ] Analyze false positives and false negatives
- [ ] Compare with rule-based detection

### **Phase 6: Deployment**

- [ ] Export trained model
- [ ] Integrate with Aegis Server
- [ ] Create real-time inference API
- [ ] Deploy and monitor

---

## 🔧 Key Features to Extract

### **Process Features**

- `process_count` - Total number of processes
- `unknown_process_count` - Number of never-seen-before processes
- `process_cpu_deviation` - Deviation from baseline CPU usage
- `process_memory_deviation` - Deviation from baseline memory usage

### **Metrics Features**

- `cpu_percent` - Current CPU usage
- `memory_percent` - Current memory usage
- `disk_io_rate` - Disk I/O rate
- `network_bytes` - Network traffic volume

### **Temporal Features**

- `hour_of_day` - Current hour (0-23)
- `is_weekend` - Boolean flag
- `is_active_hour` - Based on learned active hours

### **Command Features**

- `command_frequency` - Commands per minute
- `sudo_command_count` - Sudo commands in last hour
- `unusual_command_flag` - Never-seen-before command

### **Anomaly Indicators**

- `temporal_anomaly` - Activity at unusual time
- `resource_anomaly` - Unusual resource usage
- `process_anomaly` - Suspicious process patterns

---

## 📊 Model: Isolation Forest

**Why Isolation Forest?**

- ✅ Proven for anomaly detection
- ✅ Fast and scalable
- ✅ No labeled data required (unsupervised)
- ✅ Explainable results (anomaly scores)
- ✅ Works well with high-dimensional data

**Parameters:**

- `n_estimators`: 100-200 trees
- `contamination`: 0.05 (expect 5% anomalies in training data)
- `max_features`: 1.0 (use all features)
- `random_state`: 42 (reproducibility)

**Output:**

- Anomaly score: 0-1 (higher = more anomalous)
- Threshold: 0.6-0.8 (tune based on evaluation)

---

## 🚀 Getting Started

### **1. Install Dependencies**

```bash
cd aegis-ml-engine
pip install -r requirements.txt
```

### **2. Collect Training Data**

```bash
# Trigger manual export from Aegis Server
curl -X POST http://localhost:8000/api/ml-data/export/manual \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Or wait for auto-export (checks every 5 minutes)
```

### **3. Prepare Data**

```bash
# Copy exported data from server
cp -r /path/to/aegis-server/ml_data/export_* ./data/raw/

# Run preprocessing
python scripts/preprocess_data.py
```

### **4. Train Model**

```bash
python scripts/train_model.py --data ./data/processed --output ./models/
```

### **5. Evaluate Model**

```bash
python scripts/evaluate_model.py --model ./models/isolation_forest.pkl
```

---

## 📝 Data Requirements

### **Minimum Training Data**

- **Duration:** 2-4 weeks of normal activity
- **Logs:** 50,000+ entries
- **Metrics:** 10,000+ samples
- **Processes:** 5,000+ snapshots
- **Commands:** 5,000+ entries

### **Labeled Test Data**

- **Normal behavior:** 1 week
- **Attack scenarios:** 20+ different attacks
- **Each scenario:** 30-60 minutes of data

---

## 🎓 Research Goals

This ML engine is part of a research project comparing:

- **Traditional Rule-Based SIEM** (13+ rules)
- **AI-Powered Behavioral Analytics** (Isolation Forest)

**Hypothesis:** AI model will achieve:

- Higher true positive rate (detect more real threats)
- Lower false positive rate (fewer false alarms)
- Better zero-day threat detection

---

## 📞 Contact

**Maintainer:** Mokshit Bindal  
**Project:** Aegis SIEM  
**Status:** In Development
