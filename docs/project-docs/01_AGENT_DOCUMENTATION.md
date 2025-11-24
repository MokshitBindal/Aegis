# Aegis Agent Documentation

**Component:** Aegis Agent (Endpoint Monitoring Agent)  
**Language:** Python 3.11+  
**Type:** System Service / Daemon  
**Author:** Mokshit Bindal  
**Last Updated:** November 19, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Collection](#data-collection)
5. [Analysis Engine](#analysis-engine)
6. [Communication Protocol](#communication-protocol)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Security](#security)

---

## Overview

### Purpose

The Aegis Agent is a lightweight, cross-platform monitoring agent that runs on endpoints (servers, workstations, IoT devices) to collect security-relevant telemetry data and forward it to the Aegis Server for centralized analysis.

### Key Features

- **Real-time Data Collection:** Logs, system metrics, processes, commands
- **Local Analysis:** Pre-processes data and detects basic anomalies
- **Efficient Forwarding:** Batches data and compresses before sending
- **Low Overhead:** <2% CPU, <50MB RAM typical usage
- **Resilient:** Continues operating during network outages with local storage
- **Cross-Platform:** Linux, Windows, macOS support

### System Requirements

- **OS:** Linux (primary), Windows 10+, macOS 10.15+
- **Python:** 3.11 or higher
- **RAM:** Minimum 128MB, Recommended 256MB
- **Disk:** 500MB for application + 1GB for local storage buffer
- **Network:** HTTP/HTTPS access to Aegis Server (port 8000)

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────┐
│               Aegis Agent Process                    │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Collector  │  │  Analysis   │  │  Forwarder │ │
│  │   Module    │→→│   Engine    │→→│   Module   │ │
│  └─────────────┘  └─────────────┘  └────────────┘ │
│         ↓                                    ↓      │
│  ┌─────────────────────────────────────────────┐  │
│  │      Local SQLite Storage (Buffer)         │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
         ↓ (Logs, Metrics, Processes, Commands)
         ↓
    [Network]
         ↓
┌─────────────────────────────────────────────────────┐
│              Aegis Server (Backend)                  │
│            Port 8000 (HTTP/HTTPS)                    │
└─────────────────────────────────────────────────────┘
```

### Directory Structure

```
aegis-agent/
├── main.py                  # Entry point, CLI interface
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project metadata
├── internal/               # Core implementation
│   ├── agent/             # Agent lifecycle management
│   │   ├── __init__.py
│   │   └── agent.py       # Main agent orchestrator
│   ├── collector/         # Data collection modules
│   │   ├── __init__.py
│   │   ├── log_collector.py
│   │   └── process_monitor.py
│   ├── metrics/           # System metrics collection
│   │   ├── __init__.py
│   │   └── collector.py
│   ├── analysis/          # Local analysis engine
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── forwarder/         # Data forwarding to server
│   │   ├── __init__.py
│   │   └── forwarder.py
│   ├── storage/           # Local SQLite storage
│   │   ├── __init__.py
│   │   └── sqlite.py
│   └── config/            # Configuration management
│       ├── __init__.py
│       └── config.py
└── scripts/               # Helper scripts
    ├── run_agent.sh       # Startup script
    └── aegis-agent.service # Systemd service
```

---

## Core Components

### 1. Agent Orchestrator (`internal/agent/agent.py`)

**Responsibility:** Manages agent lifecycle and coordinates all modules.

**Key Functions:**

```python
class AegisAgent:
    async def initialize(self):
        """Initialize all modules and establish server connection"""

    async def start(self):
        """Start all background tasks (collectors, forwarder, analysis)"""

    async def shutdown(self):
        """Graceful shutdown, flush buffers, close connections"""
```

**Lifecycle:**

1. Load configuration
2. Register with server (get agent_id)
3. Initialize collectors, storage, forwarder
4. Start background tasks
5. Monitor health and restart failed tasks
6. Handle signals (SIGTERM, SIGINT) for graceful shutdown

### 2. Collector Module (`internal/collector/`)

**Responsibility:** Collects security-relevant data from the system.

#### Log Collector (`log_collector.py`)

**Sources:**

- System logs: `/var/log/syslog`, `/var/log/messages`
- Auth logs: `/var/log/auth.log`, `/var/log/secure`
- Application logs: `/var/log/apache2/`, `/var/log/nginx/`
- Windows Event Log (on Windows)

**Method:** Tail files using `inotify` (Linux) or file polling

**Collection Rate:** Real-time (event-driven)

**Code Example:**

```python
class LogCollector:
    def __init__(self):
        self.log_files = [
            '/var/log/syslog',
            '/var/log/auth.log'
        ]

    async def collect(self):
        """Monitor log files and yield new entries"""
        for log_file in self.log_files:
            async for line in self.tail_file(log_file):
                yield {
                    'timestamp': datetime.now(UTC),
                    'source': log_file,
                    'raw_data': line,
                    'hostname': socket.gethostname()
                }
```

#### Process Monitor (`process_monitor.py`)

**Data Collected:**

- Process list: PID, name, cmdline, user
- Resource usage: CPU%, memory%, threads
- Network connections: local/remote addresses, state
- File descriptors: open files

**Collection Rate:** Every 60 seconds (configurable)

**Implementation:** Uses `psutil` library for cross-platform compatibility

**Code Example:**

```python
def collect_processes(self) -> List[Dict]:
    """Collect snapshot of all running processes"""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent']):
        try:
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu_percent': proc.cpu_percent(interval=None),
                'memory_percent': proc.memory_percent(),
                'cmdline': ' '.join(proc.cmdline()),
                'create_time': datetime.fromtimestamp(proc.create_time())
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes
```

### 3. Metrics Collector (`internal/metrics/collector.py`)

**System Metrics:**

- **CPU:** Usage percentage, core count, load average
- **Memory:** Total, available, used, swap
- **Disk:** Usage per mount, I/O statistics
- **Network:** Bytes sent/received, connections

**Collection Rate:** Every 60 seconds

**Code Example:**

```python
def collect_all_metrics(self) -> Dict:
    """Collect all system metrics"""
    return {
        'cpu': {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'load_avg': psutil.getloadavg()
        },
        'memory': {
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available': psutil.virtual_memory().available,
            'memory_total': psutil.virtual_memory().total
        },
        'disk': {
            'disk_percent': psutil.disk_usage('/').percent,
            'disk_used': psutil.disk_usage('/').used,
            'disk_total': psutil.disk_usage('/').total
        },
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv
        }
    }
```

### 4. Analysis Engine (`internal/analysis/engine.py`)

**Responsibility:** Local anomaly detection before forwarding to server.

**Detection Rules:**

- CPU spike detection (>80% sustained)
- Memory leak detection (gradual increase)
- Suspicious process detection (unknown executables)
- Failed login attempts (from auth logs)

**Purpose:** Reduces false positives and network bandwidth by filtering obvious normal behavior.

**Code Example:**

```python
class AnalysisEngine:
    def analyze_metrics(self, metrics: Dict) -> Optional[Dict]:
        """Detect local anomalies in metrics"""
        alerts = []

        # CPU spike detection
        if metrics['cpu']['cpu_percent'] > 80:
            alerts.append({
                'type': 'cpu_spike',
                'severity': 'medium',
                'value': metrics['cpu']['cpu_percent']
            })

        # Memory exhaustion
        if metrics['memory']['memory_percent'] > 90:
            alerts.append({
                'type': 'memory_exhaustion',
                'severity': 'high',
                'value': metrics['memory']['memory_percent']
            })

        return alerts if alerts else None
```

### 5. Forwarder Module (`internal/forwarder/forwarder.py`)

**Responsibility:** Sends collected data to Aegis Server.

**Features:**

- **Batching:** Groups data into batches (100-500 records)
- **Compression:** gzip compression before sending
- **Retry Logic:** Exponential backoff on failures
- **Offline Mode:** Stores data locally during outages

**Communication:**

- Protocol: HTTP/HTTPS POST
- Endpoint: `http://server:8000/api/ingest/batch`
- Auth: Bearer token (JWT)
- Format: JSON payload

**Code Example:**

```python
class Forwarder:
    async def forward_batch(self, data_type: str, records: List[Dict]):
        """Forward batch of data to server"""
        url = f"{self.server_url}/api/ingest/batch"

        payload = {
            'agent_id': self.agent_id,
            'data_type': data_type,
            'records': records
        }

        # Compress if large
        if len(json.dumps(payload)) > 10240:  # >10KB
            payload_bytes = gzip.compress(json.dumps(payload).encode())
            headers = {'Content-Encoding': 'gzip'}
        else:
            payload_bytes = json.dumps(payload).encode()
            headers = {}

        headers['Authorization'] = f'Bearer {self.token}'

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload_bytes, headers=headers) as resp:
                if resp.status == 200:
                    logger.info(f"Forwarded {len(records)} {data_type}")
                    return True
                else:
                    logger.error(f"Forward failed: {resp.status}")
                    return False
```

### 6. Local Storage (`internal/storage/sqlite.py`)

**Responsibility:** Buffer data locally during collection/outages.

**Schema:**

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source TEXT,
    raw_data TEXT,
    forwarded INTEGER DEFAULT 0
);

CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    cpu_data TEXT,  -- JSON
    memory_data TEXT,
    disk_data TEXT,
    network_data TEXT,
    forwarded INTEGER DEFAULT 0
);

CREATE TABLE processes (
    id INTEGER PRIMARY KEY,
    collected_at TEXT NOT NULL,
    pid INTEGER,
    name TEXT,
    cpu_percent REAL,
    memory_percent REAL,
    forwarded INTEGER DEFAULT 0
);
```

**Cleanup:** Purges forwarded data older than 7 days.

---

## Data Collection

### Collection Pipeline

```
System Event
    ↓
Collector Module
    ↓
Local SQLite (Buffer)
    ↓
Analysis Engine (Optional)
    ↓
Forwarder Module
    ↓
Aegis Server
```

### Collection Intervals

| Data Type | Interval   | Trigger           |
| --------- | ---------- | ----------------- |
| Logs      | Real-time  | File change event |
| Metrics   | 60 seconds | Timer             |
| Processes | 60 seconds | Timer             |
| Commands  | Real-time  | Shell hook        |

### Data Volumes (Typical)

- **Logs:** 100-1000 lines/day (depends on activity)
- **Metrics:** 1440 samples/day (1/min)
- **Processes:** 1440 snapshots/day (~50 processes each)
- **Total:** ~5-10 MB/day compressed

---

## Analysis Engine

### Local Detection Rules

#### 1. CPU Spike Detection

```python
if cpu_percent > 80% for 5 consecutive minutes:
    alert("Sustained high CPU usage")
```

#### 2. Process Anomaly Detection

```python
if process.name not in known_processes:
    if process.cpu_percent > 50:
        alert("Unknown high-CPU process")
```

#### 3. Failed Authentication Detection

```python
if "Failed password" in auth_log:
    if count_in_last_5_min > 5:
        alert("Brute force attempt")
```

### Purpose of Local Analysis

- **Reduce Network Traffic:** Filter obvious normal behavior
- **Fast Response:** Immediate local alerts for critical issues
- **Offline Capability:** Works without server connection
- **Preprocessing:** Enrich data before forwarding

---

## Communication Protocol

### Registration Flow

```
1. Agent starts → Reads config (server URL)
2. POST /api/register
   Body: {hostname, os, version}
3. Server responds: {agent_id, token}
4. Agent saves credentials to disk
5. Use token for all future requests
```

### Data Forwarding

**Endpoint:** `POST /api/ingest/batch`

**Headers:**

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
Content-Encoding: gzip (if compressed)
```

**Payload:**

```json
{
  "agent_id": "uuid-here",
  "data_type": "logs",
  "records": [
    {
      "timestamp": "2025-11-19T12:00:00Z",
      "source": "/var/log/syslog",
      "raw_data": "Nov 19 12:00:00 hostname kernel: message"
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

### Error Handling

- **Network Failure:** Store in local SQLite, retry later
- **Auth Failure:** Re-register with server
- **Server Overload (503):** Exponential backoff (1s, 2s, 4s, 8s, ...)
- **Invalid Data (400):** Log error, discard batch

---

## Configuration

### Configuration File (`agent.conf`)

```toml
[agent]
server_url = "http://aegis-server:8000"
log_level = "INFO"
data_dir = "/var/lib/aegis-agent"

[collector]
log_paths = ["/var/log/syslog", "/var/log/auth.log"]
metrics_interval = 60  # seconds
process_interval = 60

[forwarder]
batch_size = 100
batch_timeout = 300  # seconds
retry_max_attempts = 5
compression_threshold = 10240  # bytes
```

### Environment Variables

- `AEGIS_SERVER_URL`: Override server URL
- `AEGIS_LOG_LEVEL`: Set log level (DEBUG, INFO, WARN, ERROR)
- `AEGIS_DATA_DIR`: Override data directory

---

## Deployment

### Installation

**Linux (Debian/Ubuntu):**

```bash
# Install .deb package
sudo dpkg -i aegis-agent_1.0.0_amd64.deb

# Configure server URL
sudo nano /etc/aegis/agent.conf

# Start service
sudo systemctl start aegis-agent
sudo systemctl enable aegis-agent
```

**Manual Installation:**

```bash
cd aegis-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo python main.py install  # Creates systemd service
```

### Running as Service

**Systemd (Linux):**

```ini
[Unit]
Description=Aegis SIEM Agent
After=network.target

[Service]
Type=simple
User=aegis
ExecStart=/usr/bin/aegis-agent run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Commands:**

```bash
sudo systemctl start aegis-agent
sudo systemctl stop aegis-agent
sudo systemctl status aegis-agent
sudo journalctl -u aegis-agent -f  # View logs
```

---

## Security

### Authentication

- **JWT Tokens:** Obtained during registration
- **Token Storage:** Secure file permissions (600)
- **Token Rotation:** Automatic renewal before expiration

### Data Protection

- **In Transit:** HTTPS/TLS encryption
- **At Rest:** SQLite database with restricted permissions
- **Credentials:** Never logged or transmitted in plaintext

### Privilege Management

- **Runs as:** Non-root user (`aegis` user)
- **Requires:** Read access to log files (via group membership)
- **No Root:** Does NOT require root except for installation

### Hardening

- Limited file system access (only logs directory)
- Network access only to Aegis Server
- Resource limits (CPU, memory via cgroups)
- Sandboxing (AppArmor/SELinux profiles available)

---

## Troubleshooting

### Agent Not Starting

```bash
# Check logs
sudo journalctl -u aegis-agent -n 100

# Verify configuration
aegis-agent config validate

# Test server connectivity
curl http://aegis-server:8000/health
```

### No Data Appearing in Dashboard

1. Check agent status: `systemctl status aegis-agent`
2. Verify registration: `cat /var/lib/aegis-agent/agent.id`
3. Test network: `telnet aegis-server 8000`
4. Check server logs for ingestion errors

### High Resource Usage

- Reduce collection frequency in config
- Enable compression for all data
- Adjust batch sizes
- Check for log file rotation issues

---

## Metrics & Monitoring

### Agent Health Metrics

- **CPU Usage:** Should be <5% average
- **Memory:** Should be <100MB RSS
- **Network:** Varies by data volume (typically <1Mbps)
- **Disk I/O:** Minimal (only local buffer)

### Performance Tuning

```toml
# High-performance configuration (busy server)
[collector]
metrics_interval = 30  # More frequent
batch_size = 500       # Larger batches

# Low-overhead configuration (IoT device)
[collector]
metrics_interval = 300  # Less frequent
batch_size = 50         # Smaller batches
process_collection = false  # Disable process monitoring
```

---

## Version History

- **v1.0.0** (Nov 2025): Initial production release
- Features: Log collection, metrics, process monitoring, ML data export

---

**For More Information:**

- Server Documentation: `02_SERVER_DOCUMENTATION.md`
- Dashboard Documentation: `03_DASHBOARD_DOCUMENTATION.md`
- Complete Project Overview: `05_PROJECT_OVERVIEW.md`
