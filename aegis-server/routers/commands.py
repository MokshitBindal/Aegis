# aegis-server/routers/commands.py

"""
API endpoints for receiving and querying terminal commands from agents.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData
from routers.device import get_user_by_email


class CommandEntry(BaseModel):
    """Model for a command sent by an agent."""
    command: str
    user: str
    timestamp: str
    shell: Optional[str] = None
    source: Optional[str] = None
    working_directory: Optional[str] = None
    exit_code: Optional[int] = None
    agent_id: str


class CommandResponse(BaseModel):
    """Model for command query response."""
    id: int
    command: str
    user_name: str
    timestamp: datetime
    shell: Optional[str]
    source: Optional[str]
    working_directory: Optional[str]
    exit_code: Optional[int]
    agent_id: str
    created_at: datetime


router = APIRouter()


@router.post("/commands")
async def ingest_commands(
    commands: List[CommandEntry],
    request: Request,
    x_aegis_agent_id: uuid.UUID = Header(None)
):
    """
    Receive terminal commands from an agent.
    
    Args:
        commands: List of command entries
        x_aegis_agent_id: Agent UUID from header
        
    Returns:
        Success message with count
    """
    if not x_aegis_agent_id:
        raise HTTPException(
            status_code=401, detail="X-Aegis-Agent-ID header is missing"
        )
    
    pool = get_db_pool()
    if not pool:
        raise HTTPException(
            status_code=500, detail="Database connection pool not available"
        )
    
    # Verify agent is registered
    try:
        async with pool.acquire() as conn:
            sql = "SELECT user_id FROM devices WHERE agent_id = $1"
            record = await conn.fetchrow(sql, x_aegis_agent_id)
            if not record:
                raise HTTPException(status_code=403, detail="Agent not registered")
            
            user_id = record['user_id']
            
            # Update last_seen timestamp to indicate agent is active
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), status = 'online' WHERE agent_id = $1",
                x_aegis_agent_id
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent auth error: {e}")
    
    # Insert commands into database
    stored_count = 0
    try:
        async with pool.acquire() as conn:
            for cmd in commands:
                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(cmd.timestamp.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    timestamp = datetime.now()
                
                # Insert command
                sql = """
                INSERT INTO commands 
                (command, user_name, timestamp, shell, source, working_directory, exit_code, agent_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """
                
                result = await conn.fetchrow(
                    sql,
                    cmd.command,
                    cmd.user,
                    timestamp,
                    cmd.shell,
                    cmd.source,
                    cmd.working_directory,
                    cmd.exit_code,
                    uuid.UUID(cmd.agent_id)
                )
                
                if result:
                    stored_count += 1
        
        print(f"Stored {stored_count} commands from agent {x_aegis_agent_id}")
        return {"message": f"Successfully stored {stored_count} commands"}
        
    except Exception as e:
        print(f"Error storing commands: {e}")
        raise HTTPException(status_code=500, detail="Failed to store commands")


@router.get("/commands/last-sync/{agent_id}")
async def get_last_command_timestamp(
    agent_id: uuid.UUID,
    x_aegis_agent_id: str = Header(None)
):
    """Get the timestamp of the most recent command for an agent."""
    try:
        # Verify agent ID from header matches the route parameter
        if x_aegis_agent_id != str(agent_id):
            raise HTTPException(status_code=403, detail="Agent ID mismatch")
        
        pool = get_db_pool()
        
        # Get the most recent command timestamp for this agent
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT MAX(timestamp) as last_timestamp
                FROM commands
                WHERE agent_id = $1
                """,
                agent_id
            )
        
        if result and result['last_timestamp']:
            return {"timestamp": result['last_timestamp'].isoformat()}
        else:
            # No commands yet, return None
            return {"timestamp": None}
            
    except Exception as e:
        print(f"Error fetching last command timestamp: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch last command timestamp")


@router.get("/commands", response_model=List[CommandResponse])
async def get_commands(
    request: Request,
    agent_id: uuid.UUID = Query(None),
    user_name: str = Query(None),
    limit: int = Query(100, le=1000),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Query terminal commands.
    
    Args:
        agent_id: Optional filter by device
        user_name: Optional filter by username
        limit: Maximum number of results
        
    Returns:
        List of command entries
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Get current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Build query based on filters
            if agent_id:
                # Verify user has access to this device (owner, assigned, or owns it)
                from models.models import UserRole
                
                if user.role == UserRole.OWNER:
                    # Owner can access all devices
                    device_check = await conn.fetchrow(
                        "SELECT id FROM devices WHERE agent_id = $1", agent_id
                    )
                elif user.role == UserRole.ADMIN:
                    # Admin can access devices they own OR are assigned to
                    device_check = await conn.fetchrow(
                        """
                        SELECT d.id FROM devices d
                        LEFT JOIN device_assignments da ON d.id = da.device_id
                        WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                        """,
                        agent_id, user.id
                    )
                else:
                    # Device User can only access their own devices
                    device_check = await conn.fetchrow(
                        "SELECT id FROM devices WHERE agent_id = $1 AND user_id = $2",
                        agent_id, user.id
                    )
                
                if not device_check:
                    raise HTTPException(
                        status_code=403,
                        detail="Access forbidden: You do not have access to this device"
                    )
                
                # Fetch commands for specific device
                if user_name:
                    sql = """
                    SELECT * FROM commands
                    WHERE agent_id = $1 AND user_name = $2
                    ORDER BY timestamp DESC
                    LIMIT $3
                    """
                    records = await conn.fetch(sql, agent_id, user_name, limit)
                else:
                    sql = """
                    SELECT * FROM commands
                    WHERE agent_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """
                    records = await conn.fetch(sql, agent_id, limit)
            else:
                # Fetch commands for all accessible devices
                from models.models import UserRole
                
                if user.role == UserRole.OWNER:
                    # Owner sees all commands
                    if user_name:
                        sql = """
                        SELECT * FROM commands
                        WHERE user_name = $1
                        ORDER BY timestamp DESC
                        LIMIT $2
                        """
                        records = await conn.fetch(sql, user_name, limit)
                    else:
                        sql = """
                        SELECT * FROM commands
                        ORDER BY timestamp DESC
                        LIMIT $1
                        """
                        records = await conn.fetch(sql, limit)
                elif user.role == UserRole.ADMIN:
                    # Admin sees commands from owned devices + assigned devices
                    if user_name:
                        sql = """
                        SELECT c.*
                        FROM commands c
                        INNER JOIN devices d ON c.agent_id = d.agent_id
                        LEFT JOIN device_assignments da ON d.id = da.device_id
                        WHERE (d.user_id = $1 OR da.user_id = $1) AND c.user_name = $2
                        ORDER BY c.timestamp DESC
                        LIMIT $3
                        """
                        records = await conn.fetch(sql, user.id, user_name, limit)
                    else:
                        sql = """
                        SELECT c.*
                        FROM commands c
                        INNER JOIN devices d ON c.agent_id = d.agent_id
                        LEFT JOIN device_assignments da ON d.id = da.device_id
                        WHERE d.user_id = $1 OR da.user_id = $1
                        ORDER BY c.timestamp DESC
                        LIMIT $2
                        """
                        records = await conn.fetch(sql, user.id, limit)
                else:
                    # Device User sees only their own device commands
                    if user_name:
                        sql = """
                        SELECT c.*
                        FROM commands c
                        LEFT JOIN devices d ON c.agent_id = d.agent_id
                        WHERE d.user_id = $1 AND c.user_name = $2
                        ORDER BY c.timestamp DESC
                        LIMIT $3
                        """
                        records = await conn.fetch(sql, user.id, user_name, limit)
                    else:
                        sql = """
                        SELECT c.*
                        FROM commands c
                        LEFT JOIN devices d ON c.agent_id = d.agent_id
                        WHERE d.user_id = $1
                        ORDER BY c.timestamp DESC
                        LIMIT $2
                        """
                        records = await conn.fetch(sql, user.id, limit)
            
            # Convert to response models
            commands = []
            for record in records:
                cmd_dict = dict(record)
                if cmd_dict.get('agent_id'):
                    cmd_dict['agent_id'] = str(cmd_dict['agent_id'])
                commands.append(CommandResponse.model_validate(cmd_dict))
            
            return commands
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching commands: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch commands")
