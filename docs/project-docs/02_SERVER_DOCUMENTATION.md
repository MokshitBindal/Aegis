# Aegis Server Documentation

**Component:** Aegis Server (Central Backend & API)  
**Language:** Python 3.11+ (FastAPI Framework)  
**Type:** REST API Server  
**Author:** Mokshit Bindal  
**Last Updated:** November 19, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Database Schema](#database-schema)
5. [Analysis & Correlation](#analysis--correlation)
6. [ML Integration](#ml-integration)
7. [Authentication & Authorization](#authentication--authorization)
8. [Deployment](#deployment)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Overview

### Purpose

The Aegis Server is the central backend that ingests data from agents, performs correlation analysis, detects threats using ML models, manages alerts, and provides REST APIs for the dashboard.

### Key Features

- **Data Ingestion:** Handles logs, metrics, processes, commands from agents
- **Real-time Analysis:** Rule-based detection + ML anomaly detection
- **Correlation Engine:** Links related events into incidents
- **Alert Management:** Creation, assignment, triage, resolution
- **User Management:** Multi-role authentication (Owner, Admin, Analyst, User)
- **ML Training:** Exports data for model training
- **REST API:** Comprehensive API for dashboard and integrations

### System Requirements

- **OS:** Linux (Ubuntu 22.04+, Debian 11+, RHEL 9+)
- **Python:** 3.11 or higher
- **Database:** PostgreSQL 14+ with TimescaleDB
- **RAM:** Minimum 2GB, Recommended 4GB+
- **Disk:** 20GB+ for database and logs
- **CPU:** 2+ cores recommended

---

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│              Aegis Server (Port 8000)                     │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │            FastAPI Application                   │    │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────┐     │    │
│  │  │ Ingest  │  │   Auth   │  │   Query    │     │    │
│  │  │   API   │  │   API    │  │    API     │     │    │
│  │  └────┬────┘  └────┬─────┘  └─────┬──────┘     │    │
│  └───────┼────────────┼──────────────┼────────────┘    │
│          ↓            ↓              ↓                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │         PostgreSQL + TimescaleDB                  │  │
│  │  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ │  │
│  │  │ Logs   │ │ Metrics │ │ Processes│ │ Alerts │ │  │
│  │  └────────┘ └─────────┘ └──────────┘ └────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│          ↑                                               │
│  ┌───────┴──────────────────────────────────────────┐  │
│  │        Background Tasks (asyncio)                 │  │
│  │  ┌──────────────┐  ┌──────────────┐             │  │
│  │  │ Correlation  │  │  ML Detector │             │  │
│  │  │   Engine     │  │  (10 min)    │             │  │
│  │  └──────────────┘  └──────────────┘             │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
        ↑                          ↑
   [Agents]                  [Dashboard]
```

### Directory Structure

```
aegis-server/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── config.toml               # Server configuration
├── pyproject.toml            # Project metadata
├── routers/                  # API route handlers
│   ├── auth.py              # Authentication endpoints
│   ├── ingest.py            # Data ingestion
│   ├── alerts.py            # Alert management
│   ├── query.py             # Data querying
│   ├── device.py            # Device management
│   ├── user_management.py   # User CRUD
│   ├── ml_data.py           # ML data export
│   └── ml_detection.py      # ML detection API
├── models/                   # Pydantic data models
│   └── models.py            # Request/response models
├── internal/                 # Core business logic
│   ├── auth/                # Authentication & authorization
│   │   ├── jwt.py          # JWT token management
│   │   └── security.py     # Password hashing (Argon2)
│   ├── storage/            # Database layer
│   │   ├── postgres.py     # Connection pooling
│   │   └── database.py     # Query helpers
│   ├── analysis/           # Threat detection
│   │   ├── correlation.py  # Event correlation
│   │   └── incident_aggregator.py
│   ├── ml/                 # Machine learning integration
│   │   ├── ml_detector.py  # Real-time ML detection
│   │   ├── data_exporter.py # Training data export
│   │   └── anomaly_detector.py # Model wrapper
│   └── config/             # Configuration management
│       └── config.py
├── models/                  # ML models
│   ├── latest_model.pkl    # Trained Isolation Forest
│   ├── latest_scaler.pkl   # Feature scaler
│   └── latest_config.json  # Model metadata
└── scripts/                # Utility scripts
    ├── init_db.py         # Database initialization
    └── aegis-manage.py    # Admin CLI tool
```

---

## API Endpoints

### Authentication

#### POST `/auth/signup`

Create new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**

```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "device_user",
  "is_active": true
}
```

#### POST `/auth/login`

Authenticate and receive JWT token.

**Request:**

```json
{
  "username": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Data Ingestion

#### POST `/api/ingest/batch`

Ingest batch of data from agent.

**Headers:**

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request:**

```json
{
  "agent_id": "uuid-here",
  "data_type": "logs",
  "records": [
    {
      "timestamp": "2025-11-19T12:00:00Z",
      "source": "/var/log/syslog",
      "raw_data": "Log message..."
    }
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "ingested": 100
}
```

#### POST `/api/ingest/metrics`

Ingest system metrics.

**Request:**

```json
{
  "agent_id": "uuid",
  "cpu_data": { "cpu_percent": 45.2 },
  "memory_data": { "memory_percent": 68.1 },
  "disk_data": { "disk_percent": 55.0 },
  "network_data": { "bytes_sent": 1024000 }
}
```

### Alerts

#### GET `/api/alerts`

Retrieve alerts with filtering.

**Query Parameters:**

- `severity`: Filter by severity (low, medium, high, critical)
- `assignment_status`: Filter by status (unassigned, assigned, resolved)
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset

**Response:**

```json
{
  "alerts": [
    {
      "id": 123,
      "rule_name": "High CPU Usage",
      "severity": "high",
      "agent_id": "uuid",
      "details": {...},
      "assignment_status": "unassigned",
      "created_at": "2025-11-19T12:00:00Z"
    }
  ],
  "total": 150
}
```

#### POST `/api/alerts/{alert_id}/assign`

Assign alert to analyst.

**Request:**

```json
{
  "assigned_to": 5
}
```

#### POST `/api/alerts/{alert_id}/resolve`

Mark alert as resolved.

**Request:**

```json
{
  "resolution_notes": "False positive - scheduled maintenance"
}
```

### Devices

#### GET `/api/devices`

List all registered devices.

**Response:**

```json
{
  "devices": [
    {
      "agent_id": "uuid",
      "hostname": "server-01",
      "os": "Linux",
      "status": "online",
      "last_seen": "2025-11-19T12:00:00Z"
    }
  ]
}
```

### ML Detection

#### GET `/api/ml/status`

Get ML detection service status.

**Response:**

```json
{
  "initialized": true,
  "model_loaded": true,
  "model_type": "IsolationForest",
  "features_count": 15,
  "trained_at": "2025-11-18T03:10:56"
}
```

#### POST `/api/ml/detect`

Manually trigger ML detection.

**Response:**

```json
{
  "success": true,
  "message": "ML detection completed",
  "alerts_generated": 2
}
```

### ML Data Export

#### GET `/api/ml-data/status`

View export status and unexported counts.

**Response:**

```json
{
  "unexported_logs": 2000,
  "unexported_metrics": 210,
  "unexported_processes": 704,
  "logs_threshold": 5000,
  "metrics_threshold": 1000,
  "last_export_time": "2025-11-13T23:50:00Z"
}
```

#### POST `/api/ml-data/export/manual`

Trigger manual data export for ML training.

---

## Database Schema

### Core Tables

#### devices

```sql
CREATE TABLE devices (
    agent_id UUID PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    os VARCHAR(50),
    os_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'online',
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### logs (TimescaleDB Hypertable)

```sql
CREATE TABLE logs (
    timestamp TIMESTAMPTZ NOT NULL,
    agent_id UUID NOT NULL REFERENCES devices(agent_id),
    hostname VARCHAR(255),
    raw_data TEXT,
    PRIMARY KEY (timestamp, agent_id)
);

SELECT create_hypertable('logs', 'timestamp');
```

#### system_metrics (TimescaleDB Hypertable)

```sql
CREATE TABLE system_metrics (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES devices(agent_id),
    timestamp TIMESTAMPTZ NOT NULL,
    cpu_data JSONB NOT NULL,
    memory_data JSONB NOT NULL,
    disk_data JSONB NOT NULL,
    network_data JSONB NOT NULL,
    process_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_agent_time ON system_metrics(agent_id, timestamp DESC);
```

#### alerts

```sql
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    details JSONB,
    agent_id UUID REFERENCES devices(agent_id),
    assignment_status VARCHAR(20) DEFAULT 'unassigned',
    assigned_to INTEGER REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(assignment_status);
CREATE INDEX idx_alerts_agent ON alerts(agent_id);
```

#### users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_pass TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);
```

#### incidents

```sql
CREATE TABLE incidents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20),
    status VARCHAR(20) DEFAULT 'open',
    agent_id UUID REFERENCES devices(agent_id),
    assigned_to INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Many-to-many relationship with alerts
CREATE TABLE incident_alerts (
    incident_id BIGINT REFERENCES incidents(id),
    alert_id BIGINT REFERENCES alerts(id),
    PRIMARY KEY (incident_id, alert_id)
);
```

---

## Analysis & Correlation

### Rule-Based Detection

**Location:** `internal/analysis/correlation.py`

**Detection Rules (13 total):**

1. **High CPU Usage:** `max_process_cpu > 200%`
2. **High Memory:** `memory_percent > 90%`
3. **Process Spike:** `process_count > 15000`
4. **Fork Bomb:** Rapid process creation
5. **Brute Force:** Multiple failed logins
6. **Privilege Escalation:** Unexpected sudo usage
7. **Suspicious Commands:** `rm -rf`, `dd`, etc.
8. **Port Scan:** Multiple connection attempts
9. **Data Exfiltration:** High network egress
10. **Malware Indicators:** Known malicious process names
11. **Log Deletion:** `/var/log` modifications
12. **Cron Job Tampering:** Crontab modifications
13. **Service Disruption:** Critical service stops

**Analysis Loop:**

```python
async def run_analysis_loop():
    """Background task analyzing events every 30 seconds"""
    while True:
        # Fetch recent data
        logs = await fetch_recent_logs(last_30_seconds)
        metrics = await fetch_recent_metrics()
        processes = await fetch_recent_processes()

        # Apply detection rules
        for rule in detection_rules:
            if rule.matches(logs, metrics, processes):
                await create_alert(rule)

        await asyncio.sleep(30)
```

### Correlation Engine

**Purpose:** Group related alerts into incidents.

**Correlation Criteria:**

- **Time-based:** Events within 5-minute window
- **Device-based:** Same agent_id
- **Severity-based:** Multiple HIGH alerts
- **Pattern-based:** Attack chain signatures

**Example Correlation:**

```
Alert 1: Failed SSH login (12:00:00)
Alert 2: Failed SSH login (12:00:15)
Alert 3: Failed SSH login (12:00:30)
Alert 4: Successful SSH login (12:00:45)
Alert 5: Suspicious sudo command (12:01:00)

→ Incident: "SSH Brute Force + Privilege Escalation"
   Severity: CRITICAL
   Alerts: [1, 2, 3, 4, 5]
```

---

## ML Integration

### Architecture

```
┌─────────────────────────────────────────────────────┐
│          Aegis Server (Background Tasks)             │
│                                                      │
│  ┌────────────────┐        ┌────────────────┐     │
│  │ Data Exporter  │───────→│ Training Data  │     │
│  │ (Every 5 min)  │        │  (CSV Files)   │     │
│  └────────────────┘        └────────────────┘     │
│                                     ↓               │
│                            ┌────────────────┐     │
│                            │   ML Engine    │     │
│                            │  (External)    │     │
│                            └────────────────┘     │
│                                     ↓               │
│                            ┌────────────────┐     │
│                            │ Trained Model  │     │
│                            │  (.pkl files)  │     │
│                            └────────┬───────┘     │
│                                     ↓               │
│  ┌────────────────┐        ┌────────────────┐     │
│  │  ML Detector   │───────→│ Anomaly Alerts │     │
│  │ (Every 10 min) │        │   (Database)   │     │
│  └────────────────┘        └────────────────┘     │
└─────────────────────────────────────────────────────┘
```

### Data Export

**Module:** `internal/ml/data_exporter.py`

**Export Triggers:**

- **Logs:** Every 5,000 new entries
- **Metrics:** Every 1,000 new samples
- **Processes:** Every 500 new snapshots
- **Commands:** Every 1,000 new commands

**Export Format:** CSV files in `ml_data/cleaned/`

**Files:**

- `logs_clean.csv`
- `metrics_clean.csv`
- `processes_clean.csv`
- `commands_clean.csv`

### ML Detection

**Module:** `internal/ml/ml_detector.py`

**Detection Flow:**

1. Every 10 minutes, check for active devices
2. Extract features from last hour of data
3. Scale features using trained scaler
4. Run prediction through Isolation Forest
5. Generate alert if anomaly detected (score < -0.4)

**Features Extracted (15 total):**

- Temporal: `hour`, `day_of_week`, `is_weekend`
- System: `cpu_percent`, `memory_percent`, `disk_percent`
- Network: `network_mb_sent`, `network_mb_recv`
- Processes: `process_count`, `max_process_cpu`, `max_process_memory`
- Commands: `command_count`, `sudo_count`
- Logs: `log_count`, `error_count`

**Anomaly Scoring:**

- Score < -0.6: **HIGH** severity
- Score -0.5 to -0.6: **MEDIUM** severity
- Score -0.4 to -0.5: **LOW** severity
- Score > -0.4: Normal (no alert)

---

## Authentication & Authorization

### Password Security

**Algorithm:** Argon2id (industry standard)

**Hashing:**

```python
from argon2 import PasswordHasher

pwd_hasher = PasswordHasher()
hashed = pwd_hasher.hash("user_password")
# Result: $argon2id$v=19$m=65536,t=3,p=4$...
```

**Verification:**

```python
try:
    pwd_hasher.verify(hashed, "user_password")
    # Success
except VerifyMismatchError:
    # Invalid password
```

### JWT Tokens

**Claims:**

```json
{
  "sub": "user@example.com",
  "role": "owner",
  "user_id": 1,
  "exp": 1700000000
}
```

**Expiration:** 7 days

**Secret:** Stored in `config.toml` (should be 32+ random bytes)

### Role-Based Access Control (RBAC)

| Role            | Permissions                       |
| --------------- | --------------------------------- |
| **owner**       | Full system access, create admins |
| **admin**       | Manage users, devices, alerts     |
| **analyst**     | View/assign/resolve alerts        |
| **device_user** | Submit data only (agents)         |

**Enforcement:**

```python
@router.get("/admin/users")
async def list_users(current_user: TokenData = Depends(get_current_user)):
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # ...
```

---

## Deployment

### Installation

**1. Install PostgreSQL + TimescaleDB:**

```bash
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-14-timescaledb
```

**2. Initialize Database:**

```bash
sudo -u postgres psql -c "CREATE DATABASE aegis_db;"
sudo -u postgres psql -c "CREATE USER aegis_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aegis_db TO aegis_user;"
sudo -u postgres psql -d aegis_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

**3. Install Server:**

```bash
cd aegis-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Configure:**

```bash
cp config.toml.example config.toml
nano config.toml  # Edit database credentials, JWT secret
```

**5. Initialize Schema:**

```bash
python scripts/init_db.py
```

**6. Start Server:**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production Deployment

**Systemd Service:**

```ini
[Unit]
Description=Aegis SIEM Server
After=network.target postgresql.service

[Service]
Type=simple
User=aegis
WorkingDirectory=/opt/aegis-server
ExecStart=/opt/aegis-server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx Reverse Proxy:**

```nginx
server {
    listen 80;
    server_name aegis.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Monitoring & Maintenance

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "aegis-siem-server", "version": "1.0.0"}
```

### Database Maintenance

**Vacuum (weekly):**

```bash
python scripts/aegis-manage.py
# Choose option 4: Vacuum database
```

**Data Retention:**

```bash
python scripts/aegis-manage.py
# Choose option 3: Cleanup old data
# Enter retention period (e.g., 90 days)
```

### Logs

```bash
# Server logs (uvicorn)
journalctl -u aegis-server -f

# Database logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

---

**For More Information:**

- Agent Documentation: `01_AGENT_DOCUMENTATION.md`
- Dashboard Documentation: `03_DASHBOARD_DOCUMENTATION.md`
- ML Model Documentation: `04_ML_MODEL_DOCUMENTATION.md`
- Complete Project Overview: `05_PROJECT_OVERVIEW.md`
