# aegis-server/internal/analysis/correlation.py

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta, timezone

from internal.storage.postgres import get_db_pool
# We need the WebSocket pusher to notify the dashboard
from routers.websocket import push_update_to_user

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
    Rule: Detects if the same source IP has > 5 failed logins
    across > 1 distinct agents within the LOOKBACK_MINUTES timeframe.
    """
    rule_name = "Potential Distributed Brute Force"
    # Calculate the time window
    start_time = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)

    # Note: This query assumes your raw_data JSONB contains a field
    #       like '_SOURCE_REALTIME_TIMESTAMP' or similar, and potentially
    #       a source IP field (e.g., from sshd logs).
    #       This query needs refinement based on actual log structure.
    #       For now, we simulate finding a source IP field 'source_ip'.

    # This SQL query needs to parse the JSONB `raw_data` to find failed logins
    # and extract the source IP. This is highly dependent on your log format.
    # LET'S USE A PLACEHOLDER QUERY focusing on the logic flow.
    # We'll imagine logs have a 'source_ip' field and 'login_success = false'.

    # -- THIS IS A CONCEPTUAL QUERY - NEEDS ADJUSTMENT FOR REAL DATA --
    sql = """
    SELECT
        raw_data->>'source_ip' AS source_ip,
        COUNT(DISTINCT agent_id) AS distinct_agents,
        COUNT(*) AS total_failures
    FROM logs
    WHERE
        timestamp >= $1
        AND raw_data->>'login_success' = 'false' -- Adjust condition based on actual data
        AND raw_data->>'source_ip' IS NOT NULL
    GROUP BY source_ip
    HAVING
        COUNT(DISTINCT agent_id) > 1 AND COUNT(*) > 5;
    """

    try:
        suspicious_ips = await conn.fetch(sql, start_time)

        for record in suspicious_ips:
            ip = record['source_ip']
            agents_count = record['distinct_agents']
            failures = record['total_failures']

            print("\n" + "="*20)
            print(f">>> SERVER ALERT: {rule_name}")
            print(f">>> Source IP: {ip}")
            print(f">>> Failed logins: {failures} across {agents_count} agents")
            print("="*20 + "\n")

            # --- Save the Alert to the DB ---
            alert_details = {
                "source_ip": ip,
                "failed_logins": failures,
                "distinct_agents": agents_count,
                "timeframe_minutes": LOOKBACK_MINUTES
            }
            await save_alert(conn, rule_name, alert_details, "medium")

    except Exception as e:
        print(f"Error during brute force check: {e}")
        # Don't crash the loop, just log the error


async def save_alert(conn: asyncpg.Connection, rule_name: str, details: dict, severity: str):
    """
    Saves a generated alert to the database and pushes a notification.
    """
    sql = """
    INSERT INTO alerts (rule_name, details, severity)
    VALUES ($1, $2, $3)
    RETURNING id, created_at
    """
    try:
        result = await conn.fetchrow(sql, rule_name, json.dumps(details), severity)

        # --- Push notification via WebSocket ---
        # We need to notify ALL users who might be affected.
        # A simple approach for now: find owners of the involved agents (complex query needed)
        # OR just broadcast to all connected admins (simpler for now).
        # We don't have user roles yet, so let's skip targeted push for now.

        print(f"Alert saved to DB (ID: {result['id']})")
        
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