# aegis-server/internal/analysis/correlation.py

import asyncio
import json
from datetime import UTC, datetime, timedelta

import asyncpg

from internal.storage.postgres import get_db_pool

# We need the WebSocket pusher to notify the dashboard

# How often the analysis loop runs
ANALYSIS_INTERVAL_SECONDS = 60
# How far back to look for logs each time
LOOKBACK_MINUTES = 5

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
                await check_potential_brute_force(conn)
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
    rule_name = "SSH Failed Login Attempts"
    # Calculate the time window
    start_time = datetime.now(UTC) - timedelta(minutes=LOOKBACK_MINUTES)

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
    HAVING COUNT(*) >= 3;
    """

    try:
        suspicious_attempts = await conn.fetch(sql, start_time)

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
                "timeframe_minutes": LOOKBACK_MINUTES
            }
            await save_alert(conn, rule_name, alert_details, "high", agent_id)

    except Exception as e:
        print(f"Error during brute force check: {e}")
        # Don't crash the loop, just log the error


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