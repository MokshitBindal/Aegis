# aegis-server/internal/analysis/incident_aggregator.py

"""
Alert aggregation and incident creation logic.
Groups related alerts into incidents for better threat visibility.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import asyncpg

from internal.storage.postgres import get_db_pool


class IncidentAggregator:
    """
    Analyzes alerts and groups related ones into incidents.
    """

    def __init__(self):
        self.aggregation_window = timedelta(minutes=30)  # Time window for grouping
        self.min_alerts_for_incident = 2  # Minimum alerts to create incident

    async def aggregate_alerts(self):
        """
        Main aggregation loop - finds ungrouped alerts and creates incidents.
        """
        pool = get_db_pool()
        if not pool:
            print("Incident aggregator: DB pool not ready")
            return

        try:
            async with pool.acquire() as conn:
                # Find ungrouped alerts from the last hour
                ungrouped_alerts = await self._get_ungrouped_alerts(conn)

                if not ungrouped_alerts:
                    return

                print(f"Found {len(ungrouped_alerts)} ungrouped alerts")

                # Group alerts by correlation keys
                alert_groups = self._correlate_alerts(ungrouped_alerts)

                # Create incidents for significant groups
                for group in alert_groups:
                    if len(group) >= self.min_alerts_for_incident:
                        await self._create_incident(conn, group)

        except Exception as e:
            print(f"Error in incident aggregation: {e}")

    async def _get_ungrouped_alerts(
        self, conn: asyncpg.Connection
    ) -> list[dict]:
        """
        Fetch alerts that haven't been grouped into incidents yet.
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=1)

        sql = """
        SELECT 
            id, rule_name, severity, details, agent_id, created_at
        FROM alerts
        WHERE 
            incident_id IS NULL
            AND created_at >= $1
        ORDER BY created_at DESC
        """

        rows = await conn.fetch(sql, cutoff_time)

        alerts = []
        for row in rows:
            alert = dict(row)
            # Parse details JSON
            if isinstance(alert['details'], str):
                try:
                    alert['details'] = json.loads(alert['details'])
                except json.JSONDecodeError:
                    alert['details'] = {}
            alerts.append(alert)

        return alerts

    def _correlate_alerts(self, alerts: list[dict]) -> list[list[dict]]:
        """
        Group alerts based on correlation criteria.

        Correlation strategies:
        1. Same source IP attacking multiple devices
        2. Same device experiencing multiple alert types
        3. Similar attack patterns within time window
        """
        groups = []
        processed_ids = set()

        for alert in alerts:
            if alert['id'] in processed_ids:
                continue

            # Start a new group with this alert
            group = [alert]
            processed_ids.add(alert['id'])

            # Find related alerts
            for other_alert in alerts:
                if other_alert['id'] in processed_ids:
                    continue

                if self._are_related(alert, other_alert):
                    group.append(other_alert)
                    processed_ids.add(other_alert['id'])

            groups.append(group)

        return groups

    def _are_related(self, alert1: dict, alert2: dict) -> bool:
        """
        Determine if two alerts are related and should be grouped.
        """
        # Check time proximity
        time_diff = abs(
            (alert1['created_at'] - alert2['created_at']).total_seconds()
        )
        if time_diff > self.aggregation_window.total_seconds():
            return False

        details1 = alert1.get('details', {})
        details2 = alert2.get('details', {})

        # Strategy 1: Same source IP
        source_ip1 = details1.get('source_ip')
        source_ip2 = details2.get('source_ip')
        if source_ip1 and source_ip2 and source_ip1 == source_ip2:
            return True

        # Strategy 2: Same device
        if alert1.get('agent_id') and alert2.get('agent_id'):
            if alert1['agent_id'] == alert2['agent_id']:
                # Same device, check if related attack types
                if self._are_attack_types_related(
                    alert1['rule_name'], alert2['rule_name']
                ):
                    return True

        # Strategy 3: Same hostname
        hostname1 = details1.get('hostname')
        hostname2 = details2.get('hostname')
        if hostname1 and hostname2 and hostname1 == hostname2:
            return True

        return False

    def _are_attack_types_related(self, rule1: str, rule2: str) -> bool:
        """
        Check if two rule types are related attack patterns.
        """
        # Define rule families
        brute_force_rules = [
            'SSH Failed Login Attempts',
            'Distributed Brute Force Attack',
            'Agent: SSH Brute Force Detected',
        ]
        escalation_rules = ['Privilege Escalation Attempt']
        resource_rules = [
            'Coordinated Resource Spike',
            'Agent: Sustained High CPU Usage',
        ]

        # Check if both rules are in the same family
        for family in [brute_force_rules, escalation_rules, resource_rules]:
            if rule1 in family and rule2 in family:
                return True

        return False

    async def _create_incident(
        self, conn: asyncpg.Connection, alert_group: list[dict]
    ):
        """
        Create an incident from a group of related alerts.
        """
        if not alert_group:
            return

        # Determine incident attributes
        severity = self._determine_incident_severity(alert_group)
        name = self._generate_incident_name(alert_group)
        description = self._generate_incident_description(alert_group)
        affected_devices = list(
            set(
                alert.get('details', {}).get('hostname', 'Unknown')
                for alert in alert_group
            )
        )
        attack_vector = self._determine_attack_vector(alert_group)

        # Build metadata
        metadata = {
            'alert_types': list(set(alert['rule_name'] for alert in alert_group)),
            'time_range': {
                'start': min(
                    alert['created_at'] for alert in alert_group
                ).isoformat(),
                'end': max(
                    alert['created_at'] for alert in alert_group
                ).isoformat(),
            },
            'source_ips': list(
                set(
                    alert.get('details', {}).get('source_ip')
                    for alert in alert_group
                    if alert.get('details', {}).get('source_ip')
                )
            ),
        }

        try:
            # Create incident
            incident_sql = """
            INSERT INTO incidents 
            (name, description, severity, status, alert_count, affected_devices, 
             attack_vector, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            RETURNING id
            """

            incident_id = await conn.fetchval(
                incident_sql,
                name,
                description,
                severity,
                'open',
                len(alert_group),
                affected_devices,
                attack_vector,
                json.dumps(metadata),
            )

            # Link alerts to incident
            alert_ids = [alert['id'] for alert in alert_group]
            update_sql = """
            UPDATE alerts 
            SET incident_id = $1
            WHERE id = ANY($2)
            """

            await conn.execute(update_sql, incident_id, alert_ids)

            print(f"\n{'='*50}")
            print(f">>> INCIDENT CREATED: {name}")
            print(f">>> Severity: {severity}")
            print(f">>> Alerts: {len(alert_group)}")
            print(f">>> Devices: {', '.join(affected_devices)}")
            print(f"{'='*50}\n")

        except Exception as e:
            print(f"Error creating incident: {e}")

    def _determine_incident_severity(self, alerts: list[dict]) -> str:
        """
        Determine incident severity based on alerts.
        """
        severity_order = ['low', 'medium', 'high', 'critical']
        max_severity = 'low'

        for alert in alerts:
            alert_severity = alert.get('severity', 'low')
            if severity_order.index(alert_severity) > severity_order.index(
                max_severity
            ):
                max_severity = alert_severity

        # Escalate if multiple high-severity alerts
        high_count = sum(
            1 for a in alerts if a.get('severity') in ['high', 'critical']
        )
        if high_count >= 3 and max_severity == 'high':
            max_severity = 'critical'

        return max_severity

    def _generate_incident_name(self, alerts: list[dict]) -> str:
        """
        Generate a descriptive name for the incident.
        """
        # Check for source IP attacks
        source_ips = set(
            alert.get('details', {}).get('source_ip')
            for alert in alerts
            if alert.get('details', {}).get('source_ip')
        )

        if source_ips:
            ip = list(source_ips)[0]
            return f"Attack from {ip} - {len(alerts)} alerts"

        # Check for device-specific incidents
        devices = set(
            alert.get('details', {}).get('hostname')
            for alert in alerts
            if alert.get('details', {}).get('hostname')
        )

        if len(devices) == 1:
            device = list(devices)[0]
            return f"Security incident on {device}"

        # Multi-device incident
        if len(devices) > 1:
            return f"Multi-device security incident ({len(devices)} devices)"

        # Fallback
        return f"Security incident - {len(alerts)} alerts"

    def _generate_incident_description(self, alerts: list[dict]) -> str:
        """
        Generate incident description.
        """
        rule_types = set(alert['rule_name'] for alert in alerts)
        return f"Correlated incident with {len(alerts)} alerts: {', '.join(rule_types)}"

    def _determine_attack_vector(self, alerts: list[dict]) -> str:
        """
        Determine the primary attack vector.
        """
        rule_names = [alert['rule_name'] for alert in alerts]

        if any('Brute Force' in rule for rule in rule_names):
            return 'brute_force'
        elif any('Privilege Escalation' in rule for rule in rule_names):
            return 'privilege_escalation'
        elif any('Port Scan' in rule for rule in rule_names):
            return 'reconnaissance'
        elif any('Resource' in rule for rule in rule_names):
            return 'resource_abuse'
        else:
            return 'unknown'


async def run_incident_aggregation_loop():
    """
    Background task that periodically aggregates alerts into incidents.
    """
    print("Starting incident aggregation loop...")
    aggregator = IncidentAggregator()

    while True:
        try:
            await aggregator.aggregate_alerts()
        except Exception as e:
            print(f"Error in aggregation loop: {e}")

        # Run every 2 minutes
        await asyncio.sleep(120)
