#!/usr/bin/env python3
"""
Aegis SIEM Management CLI
A unified interface for all administrative tasks.

Usage: python aegis-manage.py
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from internal.config.config import DB_URL


class AegisManager:
    """Unified management interface for Aegis SIEM"""
    
    def __init__(self):
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(DB_URL)
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def clear_all_alerts(self):
        """Delete all alerts and alert assignments"""
        print("\n" + "="*60)
        print("🗑️  CLEAR ALL ALERTS")
        print("="*60)
        
        # Get current counts
        alert_count = await self.conn.fetchval("SELECT COUNT(*) FROM alerts")
        assignment_count = await self.conn.fetchval("SELECT COUNT(*) FROM alert_assignments")
        
        print(f"\nCurrent database state:")
        print(f"  • Alerts: {alert_count}")
        print(f"  • Alert Assignments: {assignment_count}")
        
        if alert_count == 0 and assignment_count == 0:
            print("\n✅ No alerts to delete. Database is already clean.")
            return
        
        confirm = input(f"\n⚠️  Delete ALL {alert_count} alerts? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Operation cancelled.")
            return
        
        print("\n🗑️  Deleting...")
        
        # Delete assignments first
        result = await self.conn.execute("DELETE FROM alert_assignments")
        count_assignments = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {count_assignments} alert assignments")
        
        # Delete alerts
        result = await self.conn.execute("DELETE FROM alerts")
        count_alerts = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {count_alerts} alerts")
        
        # Reset sequences
        await self.conn.execute("ALTER SEQUENCE alerts_id_seq RESTART WITH 1")
        await self.conn.execute("ALTER SEQUENCE alert_assignments_id_seq RESTART WITH 1")
        print(f"   ✓ Reset ID sequences")
        
        # Vacuum
        await self.conn.execute("VACUUM ANALYZE alerts")
        await self.conn.execute("VACUUM ANALYZE alert_assignments")
        print(f"   ✓ Reclaimed disk space")
        
        print("\n✅ Successfully cleared all alerts!")
    
    async def cleanup_old_data(self):
        """Delete old logs, metrics, and commands"""
        print("\n" + "="*60)
        print("🧹 CLEANUP OLD DATA")
        print("="*60)
        
        print("\nChoose retention period:")
        print("  1. 30 days")
        print("  2. 90 days (3 months)")
        print("  3. 180 days (6 months)")
        print("  4. Custom days")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        days_map = {"1": 30, "2": 90, "3": 180}
        if choice in days_map:
            days = days_map[choice]
        elif choice == "4":
            try:
                days = int(input("Enter number of days to keep: "))
            except ValueError:
                print("❌ Invalid number")
                return
        else:
            print("❌ Invalid choice")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        print(f"\n⚠️  This will delete data older than {cutoff_date.strftime('%Y-%m-%d')}")
        print(f"   (Keeping last {days} days)")
        
        confirm = input("\nProceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Operation cancelled.")
            return
        
        print("\n🗑️  Deleting old data...")
        
        # Delete old logs
        result = await self.conn.execute(
            "DELETE FROM logs WHERE timestamp < $1", cutoff_date
        )
        logs_deleted = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {logs_deleted:,} log entries")
        
        # Delete old commands
        result = await self.conn.execute(
            "DELETE FROM commands WHERE timestamp < $1", cutoff_date
        )
        commands_deleted = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {commands_deleted:,} command entries")
        
        # Delete old metrics (try both table names)
        metrics_deleted = 0
        try:
            result = await self.conn.execute(
                "DELETE FROM system_metrics WHERE timestamp < $1", cutoff_date
            )
            metrics_deleted = int(result.split()[-1]) if result else 0
        except Exception:
            try:
                result = await self.conn.execute(
                    "DELETE FROM metrics WHERE timestamp < $1", cutoff_date
                )
                metrics_deleted = int(result.split()[-1]) if result else 0
            except Exception:
                pass
        print(f"   ✓ Deleted {metrics_deleted:,} metric entries")
        
        # Delete old processes
        result = await self.conn.execute(
            "DELETE FROM processes WHERE timestamp < $1", cutoff_date
        )
        processes_deleted = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {processes_deleted:,} process entries")
        
        # Vacuum
        print("\n🧹 Reclaiming disk space...")
        for table in ["logs", "commands", "system_metrics", "processes"]:
            try:
                await self.conn.execute(f"VACUUM ANALYZE {table}")
            except Exception:
                pass  # Skip if table doesn't exist
        
        total_deleted = logs_deleted + commands_deleted + metrics_deleted + processes_deleted
        print(f"\n✅ Cleanup complete! Deleted {total_deleted:,} total records.")
    
    async def database_stats(self):
        """Show database statistics"""
        print("\n" + "="*60)
        print("📊 DATABASE STATISTICS")
        print("="*60)
        
        # Get counts with error handling for missing tables
        async def safe_count(table_name):
            try:
                return await self.conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            except Exception:
                return None
        
        stats = {
            "Devices": await safe_count("devices"),
            "Alerts": await safe_count("alerts"),
            "Alert Assignments": await safe_count("alert_assignments"),
            "Logs": await safe_count("logs"),
            "Commands": await safe_count("commands"),
            "Metrics": await safe_count("system_metrics"),  # Correct table name
            "Processes": await safe_count("processes"),
            "Users": await safe_count("users"),
        }
        
        print("\nRecord counts:")
        for key, value in stats.items():
            if value is not None:
                print(f"  • {key:20s}: {value:,}")
            else:
                print(f"  • {key:20s}: N/A (table not found)")
        
        # Alert breakdown
        print("\nAlert severity breakdown:")
        alert_severity = await self.conn.fetch(
            "SELECT severity, COUNT(*) as count FROM alerts GROUP BY severity ORDER BY count DESC"
        )
        for row in alert_severity:
            print(f"  • {row['severity']:15s}: {row['count']:,}")
        
        # Alert status breakdown
        print("\nAlert status breakdown:")
        alert_status = await self.conn.fetch(
            "SELECT assignment_status, COUNT(*) as count FROM alerts GROUP BY assignment_status ORDER BY count DESC"
        )
        for row in alert_status:
            print(f"  • {row['assignment_status']:15s}: {row['count']:,}")
        
        # Database size
        db_size = await self.conn.fetchval(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        print(f"\nTotal database size: {db_size}")
    
    async def reset_users(self):
        """Reset user accounts"""
        print("\n" + "="*60)
        print("👥 RESET USERS")
        print("="*60)
        
        user_count = await self.conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"\nCurrent users: {user_count}")
        
        confirm = input(f"\n⚠️  Delete all {user_count} users? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Operation cancelled.")
            return
        
        print("\n🗑️  Deleting users...")
        
        # Delete device assignments first
        result = await self.conn.execute("DELETE FROM device_assignments")
        print(f"   ✓ Deleted device assignments")
        
        # Delete users
        result = await self.conn.execute("DELETE FROM users")
        count = int(result.split()[-1]) if result else 0
        print(f"   ✓ Deleted {count} users")
        
        # Reset sequence
        await self.conn.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
        print(f"   ✓ Reset user ID sequence")
        
        print("\n✅ Successfully reset users!")
        print("ℹ️  You can now create new users via the API.")
    
    async def clear_invitations(self):
        """Clear invitation codes"""
        print("\n" + "="*60)
        print("📧 CLEAR INVITATIONS")
        print("="*60)
        
        invite_count = await self.conn.fetchval("SELECT COUNT(*) FROM invitations")
        print(f"\nCurrent invitations: {invite_count}")
        
        if invite_count == 0:
            print("\n✅ No invitations to delete.")
            return
        
        confirm = input(f"\n⚠️  Delete all {invite_count} invitations? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Operation cancelled.")
            return
        
        result = await self.conn.execute("DELETE FROM invitations")
        count = int(result.split()[-1]) if result else 0
        print(f"\n✅ Deleted {count} invitations")
    
    async def vacuum_database(self):
        """Run VACUUM on all tables"""
        print("\n" + "="*60)
        print("🧹 VACUUM DATABASE")
        print("="*60)
        
        print("\nThis will reclaim disk space and update statistics.")
        confirm = input("\nProceed? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("❌ Operation cancelled.")
            return
        
        tables = [
            "devices", "alerts", "alert_assignments", "logs", 
            "commands", "system_metrics", "processes", "users", 
            "device_assignments", "invitations", "incidents"
        ]
        
        print("\n🧹 Running VACUUM ANALYZE on all tables...")
        for table in tables:
            try:
                await self.conn.execute(f"VACUUM ANALYZE {table}")
                print(f"   ✓ {table}")
            except Exception as e:
                print(f"   ⚠️  {table}: {e}")
        
        print("\n✅ Database vacuum complete!")
    
    def show_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("🛡️  AEGIS SIEM MANAGEMENT CLI")
        print("="*60)
        print("\nDatabase Operations:")
        print("  1. Show database statistics")
        print("  2. Clear all alerts")
        print("  3. Cleanup old data (logs/metrics/commands)")
        print("  4. Vacuum database")
        print("\nUser Management:")
        print("  5. Reset users")
        print("  6. Clear invitations")
        print("\nOther:")
        print("  7. Exit")
        print("="*60)
    
    async def run(self):
        """Main execution loop"""
        print("\n🛡️  Aegis SIEM Management CLI")
        print("Connecting to database...")
        
        if not await self.connect():
            return
        
        print("✅ Connected successfully!\n")
        
        try:
            while True:
                self.show_menu()
                choice = input("\nEnter your choice (1-7): ").strip()
                
                if choice == "1":
                    await self.database_stats()
                elif choice == "2":
                    await self.clear_all_alerts()
                elif choice == "3":
                    await self.cleanup_old_data()
                elif choice == "4":
                    await self.vacuum_database()
                elif choice == "5":
                    await self.reset_users()
                elif choice == "6":
                    await self.clear_invitations()
                elif choice == "7":
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("\n❌ Invalid choice. Please try again.")
                
                input("\nPress Enter to continue...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
        finally:
            await self.close()


if __name__ == "__main__":
    manager = AegisManager()
    asyncio.run(manager.run())
