# aegis-server/internal/analysis/correlation.py

import asyncio
import json
from datetime import UTC, datetime, timedelta

import asyncpg

from internal.analysis.rules_config import RULES_CONFIG
from internal.storage.postgres import get_db_pool

# We need the WebSocket pusher to notify the dashboard

# Get configuration
config = RULES_CONFIG

# How often the analysis loop runs
ANALYSIS_INTERVAL_SECONDS = config.analysis_interval_seconds
# How far back to look for logs each time
LOOKBACK_MINUTES = config.lookback_minutes

async def run_analysis_loop():
    """
    The main background task that periodically runs correlation analysis.
    """
    print("Starting background analysis loop...")
    while True:
        try:
            pool = get_db_pool()
            if not pool:
                print("Analysis loop: DB pool not ready, waiting...")
                await asyncio.sleep(10)
                continue

            async with pool.acquire() as conn:
                if config.ssh_brute_force.enabled:
                    await check_potential_brute_force(conn)
                if config.distributed_brute_force.enabled:
                    await check_distributed_brute_force(conn)
                if config.privilege_escalation.enabled:
                    await check_privilege_escalation(conn)
                if config.port_scan.enabled:
                    await check_port_scan_activity(conn)
                if config.resource_anomaly.enabled:
                    await check_resource_anomalies(conn)
                # --- Add calls to other analysis functions here ---
                # await check_other_rule(conn)

        except Exception as e:
            print(f"Error in analysis loop: {e}")

        # Wait for the next interval
        await asyncio.sleep(ANALYSIS_INTERVAL_SECONDS)

async def check_potential_brute_force(conn: asyncpg.Connection):
    """
    Rule: Detects multiple failed SSH login attempts from the same source IP
    on a single device (> 3 failures within LOOKBACK_MINUTES).
    """
    rule_config = config.ssh_brute_force
    rule_name = rule_config.name
    # Calculate the time window
    start_time = datetime.now(UTC) - timedelta(minutes=rule_config.timeframe_minutes)

    # Extract source IP from MESSAGE field using regex pattern
    # MESSAGE format: "Failed password for invalid user X from IP port PORT ssh2"
    # or "Failed password for X from IP port PORT ssh2"
    sql = """
    WITH failed_logins AS (
        SELECT
            raw_data->>'_HOSTNAME' AS hostname,
            SUBSTRING(raw_data->>'MESSAGE' FROM 'from ([0-9.]+) port') AS source_ip,
            raw_data->>'MESSAGE' AS message,
            timestamp
        FROM logs
        WHERE
            timestamp >= $1
            AND (
                raw_data->>'MESSAGE' ILIKE '%Failed password%'
                OR raw_data->>'MESSAGE' ILIKE '%authentication failure%'
            )
            AND raw_data->>'MESSAGE' ~ 'from [0-9.]+ port'
    )
    SELECT
        fl.hostname,
        fl.source_ip,
        d.agent_id,
        COUNT(*) AS failure_count,
        MIN(fl.timestamp) AS first_attempt,
        MAX(fl.timestamp) AS last_attempt,
        array_agg(DISTINCT SUBSTRING(fl.message, 1, 100)) AS sample_messages
    FROM failed_logins fl
    LEFT JOIN devices d ON d.hostname = fl.hostname
    WHERE fl.source_ip IS NOT NULL
    GROUP BY fl.hostname, fl.source_ip, d.agent_id
    HAVING COUNT(*) >= $2;
    """

    try:
        suspicious_attempts = await conn.fetch(sql, start_time, rule_config.min_failures)

        for record in suspicious_attempts:
            hostname = record['hostname']
            ip = record['source_ip']
            agent_id = record['agent_id']
            failures = record['failure_count']
            first_attempt = record['first_attempt']
            last_attempt = record['last_attempt']

            print("\n" + "="*50)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> Device: {hostname} (agent_id: {agent_id})")
            print(f">>> Source IP: {ip}")
            print(f">>> Failed attempts: {failures}")
            print(f">>> Time range: {first_attempt} to {last_attempt}")
            print("="*50 + "\n")

            # --- Save the Alert to the DB with agent_id ---
            alert_details = {
                "hostname": hostname,
                "source_ip": ip,
                "failed_attempts": failures,
                "first_attempt": first_attempt.isoformat() if first_attempt else None,
                "last_attempt": last_attempt.isoformat() if last_attempt else None,
                "timeframe_minutes": rule_config.timeframe_minutes,
            }
            await save_alert(conn, rule_name, alert_details, rule_config.severity, agent_id)

    except Exception as e:
        print(f"Error during brute force check: {e}")
        # Don't crash the loop, just log the error


async def check_distributed_brute_force(conn: asyncpg.Connection):
    """
    Rule: Detects distributed brute force attacks - same source IP targeting
    multiple devices (> 2 devices) with failed login attempts.
    """
    rule_config = config.distributed_brute_force
    rule_name = rule_config.name
    start_time = datetime.now(UTC) - timedelta(minutes=rule_config.timeframe_minutes)

    sql = """
    WITH failed_logins AS (
        SELECT
            raw_data->>'_HOSTNAME' AS hostname,
            SUBSTRING(raw_data->>'MESSAGE' FROM 'from ([0-9.]+) port') AS source_ip,
            timestamp,
            raw_data->>'MESSAGE' AS message
        FROM logs
        WHERE
            timestamp >= $1
            AND (
                raw_data->>'MESSAGE' ILIKE '%Failed password%'
                OR raw_data->>'MESSAGE' ILIKE '%authentication failure%'
            )
            AND raw_data->>'MESSAGE' ~ 'from [0-9.]+ port'
    )
    SELECT
        fl.source_ip,
        COUNT(DISTINCT fl.hostname) AS affected_devices,
        COUNT(*) AS total_attempts,
        array_agg(DISTINCT fl.hostname) AS hostnames,
        MIN(fl.timestamp) AS first_attempt,
        MAX(fl.timestamp) AS last_attempt
    FROM failed_logins fl
    WHERE fl.source_ip IS NOT NULL
    GROUP BY fl.source_ip
    HAVING COUNT(DISTINCT fl.hostname) > $2 AND COUNT(*) >= $3;
    """

    try:
        attacks = await conn.fetch(
            sql, start_time, rule_config.min_devices, rule_config.min_attempts
        )

        for record in attacks:
            ip = record['source_ip']
            device_count = record['affected_devices']
            total_attempts = record['total_attempts']
            hostnames = record['hostnames']

            print("\n" + "="*50)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> Source IP: {ip}")
            print(f">>> Targeted {device_count} devices with {total_attempts} attempts")
            print(f">>> Affected hosts: {', '.join(hostnames)}")
            print("="*50 + "\n")

            alert_details = {
                "source_ip": ip,
                "affected_devices": device_count,
                "total_attempts": total_attempts,
                "hostnames": hostnames,
                "first_attempt": record['first_attempt'].isoformat(),
                "last_attempt": record['last_attempt'].isoformat(),
                "timeframe_minutes": rule_config.timeframe_minutes,
            }
            # No specific agent_id since this spans multiple devices
            await save_alert(conn, rule_name, alert_details, rule_config.severity, None)

    except Exception as e:
        print(f"Error during distributed brute force check: {e}")


async def check_privilege_escalation(conn: asyncpg.Connection):
    """
    Rule: Detects privilege escalation attempts via failed sudo commands
    or unauthorized access attempts.
    """
    rule_config = config.privilege_escalation
    rule_name = rule_config.name
    start_time = datetime.now(UTC) - timedelta(minutes=rule_config.timeframe_minutes)

    sql = """
    WITH escalation_attempts AS (
        SELECT
            raw_data->>'_HOSTNAME' AS hostname,
            raw_data->>'MESSAGE' AS message,
            raw_data->>'_UID' AS uid,
            raw_data->>'SYSLOG_IDENTIFIER' AS identifier,
            timestamp
        FROM logs
        WHERE
            timestamp >= $1
            AND (
                (raw_data->>'MESSAGE' ILIKE '%sudo%' AND 
                 (raw_data->>'MESSAGE' ILIKE '%incorrect password%' OR
                  raw_data->>'MESSAGE' ILIKE '%authentication failure%' OR
                  raw_data->>'MESSAGE' ILIKE '%not in sudoers%'))
                OR
                (raw_data->>'MESSAGE' ILIKE '%su:%' AND 
                 raw_data->>'MESSAGE' ILIKE '%authentication failure%')
                OR
                raw_data->>'MESSAGE' ILIKE '%unauthorized%'
            )
    )
    SELECT
        ea.hostname,
        d.agent_id,
        COUNT(*) AS attempt_count,
        array_agg(DISTINCT SUBSTRING(ea.message, 1, 100)) AS sample_messages,
        MIN(ea.timestamp) AS first_attempt,
        MAX(ea.timestamp) AS last_attempt
    FROM escalation_attempts ea
    LEFT JOIN devices d ON d.hostname = ea.hostname
    GROUP BY ea.hostname, d.agent_id
    HAVING COUNT(*) >= $2;
    """

    try:
        attempts = await conn.fetch(sql, start_time, rule_config.min_attempts)

        for record in attempts:
            hostname = record['hostname']
            agent_id = record['agent_id']
            count = record['attempt_count']

            print("\n" + "="*50)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> Device: {hostname}")
            print(f">>> Attempts: {count}")
            print("="*50 + "\n")

            alert_details = {
                "hostname": hostname,
                "attempt_count": count,
                "sample_messages": record['sample_messages'],
                "first_attempt": record['first_attempt'].isoformat(),
                "last_attempt": record['last_attempt'].isoformat(),
                "timeframe_minutes": rule_config.timeframe_minutes,
            }
            await save_alert(conn, rule_name, alert_details, rule_config.severity, agent_id)

    except Exception as e:
        print(f"Error during privilege escalation check: {e}")


async def check_port_scan_activity(conn: asyncpg.Connection):
    """
    Rule: Detects potential port scanning by analyzing connection patterns
    in firewall/iptables logs.
    """
    rule_config = config.port_scan
    rule_name = rule_config.name
    start_time = datetime.now(UTC) - timedelta(minutes=rule_config.timeframe_minutes)

    sql = """
    WITH connection_attempts AS (
        SELECT
            raw_data->>'_HOSTNAME' AS hostname,
            SUBSTRING(raw_data->>'MESSAGE' FROM 'SRC=([0-9.]+)') AS source_ip,
            SUBSTRING(raw_data->>'MESSAGE' FROM 'DPT=([0-9]+)') AS dest_port,
            timestamp
        FROM logs
        WHERE
            timestamp >= $1
            AND (
                raw_data->>'MESSAGE' ILIKE '%kernel:%'
                OR raw_data->>'SYSLOG_IDENTIFIER' = 'kernel'
            )
            AND (
                raw_data->>'MESSAGE' ILIKE '%IN=%'
                AND raw_data->>'MESSAGE' ~ 'SRC=[0-9.]+'
                AND raw_data->>'MESSAGE' ~ 'DPT=[0-9]+'
            )
    )
    SELECT
        ca.hostname,
        ca.source_ip,
        d.agent_id,
        COUNT(DISTINCT ca.dest_port) AS unique_ports,
        COUNT(*) AS total_attempts,
        array_agg(DISTINCT ca.dest_port) AS ports,
        MIN(ca.timestamp) AS first_attempt,
        MAX(ca.timestamp) AS last_attempt
    FROM connection_attempts ca
    LEFT JOIN devices d ON d.hostname = ca.hostname
    WHERE ca.source_ip IS NOT NULL AND ca.dest_port IS NOT NULL
    GROUP BY ca.hostname, ca.source_ip, d.agent_id
    HAVING COUNT(DISTINCT ca.dest_port) >= $2;
    """

    try:
        scans = await conn.fetch(sql, start_time, rule_config.min_unique_ports)

        for record in scans:
            hostname = record['hostname']
            source_ip = record['source_ip']
            agent_id = record['agent_id']
            unique_ports = record['unique_ports']

            print("\n" + "="*50)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> Device: {hostname}")
            print(f">>> Source IP: {source_ip}")
            print(f">>> Scanned {unique_ports} unique ports")
            print("="*50 + "\n")

            alert_details = {
                "hostname": hostname,
                "source_ip": source_ip,
                "unique_ports": unique_ports,
                "total_attempts": record['total_attempts'],
                "first_attempt": record['first_attempt'].isoformat(),
                "last_attempt": record['last_attempt'].isoformat(),
                "timeframe_minutes": rule_config.timeframe_minutes,
            }
            await save_alert(conn, rule_name, alert_details, rule_config.severity, agent_id)

    except Exception as e:
        print(f"Error during port scan check: {e}")


async def check_resource_anomalies(conn: asyncpg.Connection):
    """
    Rule: Detects sudden resource usage spikes across multiple devices
    within a short timeframe (potential DDoS, cryptomining, etc.).
    """
    rule_config = config.resource_anomaly
    rule_name = rule_config.name
    start_time = datetime.now(UTC) - timedelta(minutes=rule_config.timeframe_minutes)

    sql = """
    WITH recent_metrics AS (
        SELECT
            agent_id,
            timestamp,
            (cpu_data->>'cpu_percent')::float as cpu_percent,
            (memory_data->>'memory_percent')::float as memory_percent,
            (disk_data->>'disk_percent')::float as disk_percent
        FROM system_metrics
        WHERE timestamp >= $1
    ),
    high_usage AS (
        SELECT
            agent_id,
            COUNT(*) as spike_count,
            AVG(cpu_percent) as avg_cpu,
            AVG(memory_percent) as avg_memory,
            MIN(timestamp) as first_spike,
            MAX(timestamp) as last_spike
        FROM recent_metrics
        WHERE cpu_percent > $2 OR memory_percent > $3
        GROUP BY agent_id
        HAVING COUNT(*) >= $4
    )
    SELECT
        COUNT(DISTINCT hu.agent_id) as affected_devices,
        array_agg(DISTINCT d.hostname) as hostnames,
        array_agg(DISTINCT hu.agent_id) as agent_ids,
        AVG(hu.avg_cpu) as overall_avg_cpu,
        AVG(hu.avg_memory) as overall_avg_memory,
        MIN(hu.first_spike) as first_spike,
        MAX(hu.last_spike) as last_spike
    FROM high_usage hu
    LEFT JOIN devices d ON d.agent_id = hu.agent_id
    HAVING COUNT(DISTINCT hu.agent_id) >= $5;
    """

    try:
        anomalies = await conn.fetch(
            sql,
            start_time,
            rule_config.cpu_threshold,
            rule_config.memory_threshold,
            rule_config.min_spike_count,
            rule_config.min_devices,
        )

        for record in anomalies:
            device_count = record['affected_devices']
            hostnames = record['hostnames']
            avg_cpu = record['overall_avg_cpu']
            avg_memory = record['overall_avg_memory']

            print("\n" + "="*50)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> {device_count} devices experiencing resource spikes")
            print(f">>> Avg CPU: {avg_cpu:.1f}%, Avg Memory: {avg_memory:.1f}%")
            print(f">>> Affected: {', '.join(hostnames) if hostnames else 'Unknown'}")
            print("="*50 + "\n")

            alert_details = {
                "affected_devices": device_count,
                "hostnames": hostnames,
                "average_cpu": round(avg_cpu, 2) if avg_cpu else 0,
                "average_memory": round(avg_memory, 2) if avg_memory else 0,
                "first_spike": record['first_spike'].isoformat() if record['first_spike'] else None,
                "last_spike": record['last_spike'].isoformat() if record['last_spike'] else None,
                "timeframe_minutes": rule_config.timeframe_minutes,
            }
            # No specific agent_id since this spans multiple devices
            await save_alert(conn, rule_name, alert_details, rule_config.severity, None)

    except Exception as e:
        print(f"Error during resource anomaly check: {e}")


async def save_alert(
    conn: asyncpg.Connection, rule_name: str, details: dict, severity: str, agent_id=None
):
    """
    Saves a generated alert to the database and pushes a notification.
    """
    sql = """
    INSERT INTO alerts (rule_name, details, severity, agent_id)
    VALUES ($1, $2, $3, $4)
    RETURNING id, created_at
    """
    try:
        result = await conn.fetchrow(sql, rule_name, json.dumps(details), severity, agent_id)

        # --- Push notification via WebSocket ---
        # We need to notify ALL users who might be affected.
        # A simple approach for now: find owners of the involved agents
        # (complex query needed) OR just broadcast to all connected admins
        # (simpler for now). We don't have user roles yet, so let's skip
        # targeted push for now.

        print(f"Alert saved to DB (ID: {result['id']}, agent_id: {agent_id})")
        
        # --- Placeholder for targeted WebSocket push ---
        # Find user_ids related to this alert (e.g., owners of affected agents)
        # For user_id in relevant_user_ids:
        #    await push_update_to_user(user_id, {
        #        "type": "new_alert",
        #        "payload": {
        #            "id": result['id'],
        #            "rule_name": rule_name,
        #            "details": details,
        #            "severity": severity,
        #            "created_at": result['created_at'].isoformat()
        #        }
        #    })

    except Exception as e:
        print(f"Error saving alert: {e}")