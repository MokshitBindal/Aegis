#!/usr/bin/env python3
"""
Training script for learning device behavioral baselines.

Usage:
    python scripts/train_behavioral_model.py --device-id <uuid> --days 28
    python scripts/train_behavioral_model.py --all --days 28

Author: Mokshit Bindal
Date: November 8, 2025
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from internal.config.config import DB_URL
from internal.analysis.baseline_engine import BaselineLearner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def train_single_device(device_id: UUID, duration_days: int):
    """Train baseline for a single device"""
    logger.info(f"Training baseline for device {device_id}")
    logger.info(f"Analyzing {duration_days} days of historical data")
    
    pool = None
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=5)
        
        # Check if device exists
        async with pool.acquire() as conn:
            device = await conn.fetchrow(
                "SELECT agent_id, hostname FROM devices WHERE agent_id = $1",
                device_id
            )
        
        if not device:
            logger.error(f"Device {device_id} not found")
            await pool.close()
            return False
        
        logger.info(f"Device found: {device['hostname']}")
        
        # Create baseline learner and train
        learner = BaselineLearner(pool)
        baseline = await learner.learn_device_baseline(device_id, duration_days)
        
        # Store baselines in database
        baseline_types = ['process_baseline', 'metrics_baseline', 'activity_baseline', 'command_baseline']
        
        async with pool.acquire() as conn:
            for baseline_type in baseline_types:
                if baseline_type in baseline and baseline[baseline_type]:
                    # Check if baseline already exists
                    existing = await conn.fetchrow(
                        """
                        SELECT id, version FROM device_baselines
                        WHERE device_id = $1 AND baseline_type = $2
                        ORDER BY version DESC
                        LIMIT 1
                        """,
                        device_id, baseline_type.replace('_baseline', '')
                    )
                    
                    new_version = (existing['version'] + 1) if existing else 1
                    
                    # Insert new baseline (convert dict to JSON string for JSONB column)
                    import json
                    await conn.execute(
                        """
                        INSERT INTO device_baselines (
                            device_id, baseline_type, baseline_data, 
                            learned_at, duration_days, version
                        )
                        VALUES ($1, $2, $3::jsonb, NOW(), $4, $5)
                        """,
                        device_id,
                        baseline_type.replace('_baseline', ''),
                        json.dumps(baseline[baseline_type]),
                        duration_days,
                        new_version
                    )
                    
                    logger.info(f"✓ Stored {baseline_type} (version {new_version})")
            
            # Store full baseline (convert dict to JSON string)
            await conn.execute(
                """
                INSERT INTO device_baselines (
                    device_id, baseline_type, baseline_data, 
                    learned_at, duration_days, version
                )
                VALUES ($1, $2, $3::jsonb, NOW(), $4, 1)
                ON CONFLICT (device_id, baseline_type, version)
                DO UPDATE SET baseline_data = $3::jsonb
                """,
                device_id,
                'full',
                json.dumps(baseline),
                duration_days
            )
            
            logger.info(f"✓ Stored full baseline")
        
        await pool.close()
        
        logger.info(f"✓ Baseline training complete for {device['hostname']}")
        logger.info(f"  - Process snapshots analyzed: {baseline['process_baseline'].get('snapshots_analyzed', 0)}")
        logger.info(f"  - Metric samples analyzed: {baseline['metrics_baseline'].get('samples_analyzed', 0)}")
        logger.info(f"  - Commands analyzed: {baseline['command_baseline'].get('total_commands', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to train baseline for device {device_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def train_all_devices(duration_days: int):
    """Train baselines for all devices"""
    logger.info("Training baselines for ALL devices")
    
    pool = None
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=5)
        
        # Get all devices
        async with pool.acquire() as conn:
            devices = await conn.fetch("SELECT agent_id, hostname FROM devices WHERE status = 'active'")
        
        if not devices:
            logger.warning("No active devices found")
            await pool.close()
            return
        
        logger.info(f"Found {len(devices)} active devices")
        
        success_count = 0
        fail_count = 0
        
        for device in devices:
            logger.info(f"\n{'='*60}")
            logger.info(f"Training: {device['hostname']} ({device['agent_id']})")
            logger.info(f"{'='*60}")
            
            success = await train_single_device(device['agent_id'], duration_days)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Training complete!")
        logger.info(f"  ✓ Successful: {success_count}")
        logger.info(f"  ✗ Failed: {fail_count}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Failed to train all devices: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if pool:
            await pool.close()


def main():
    parser = argparse.ArgumentParser(
        description="Train behavioral baselines for Aegis SIEM devices"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--device-id',
        type=str,
        help='UUID of specific device to train'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Train baselines for all active devices'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=28,
        help='Number of days of historical data to analyze (default: 28)'
    )
    
    args = parser.parse_args()
    
    # Validate days
    if args.days < 7 or args.days > 90:
        logger.error("Days must be between 7 and 90")
        sys.exit(1)
    
    # Run training
    if args.all:
        asyncio.run(train_all_devices(args.days))
    else:
        try:
            device_id = UUID(args.device_id)
            success = asyncio.run(train_single_device(device_id, args.days))
            sys.exit(0 if success else 1)
        except ValueError:
            logger.error(f"Invalid device ID: {args.device_id}")
            sys.exit(1)


if __name__ == "__main__":
    main()
