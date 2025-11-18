# aegis-server/routers/alert_triage.py

import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from internal.auth.jwt import get_current_user
from internal.auth.permissions import can_escalate_alert, check_alert_access
from internal.storage.postgres import get_db_pool
from models.models import (
    AlertAssignment,
    AlertAssignmentCreate,
    AlertAssignmentUpdate,
    AlertEscalation,
    AssignmentStatus,
    TokenData,
    UserRole,
)

router = APIRouter()


@router.post("/alerts/{alert_id}/claim", response_model=AlertAssignment, status_code=status.HTTP_201_CREATED)
async def claim_alert(
    alert_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Claim an unassigned alert (Admin only).
    Creates a new assignment record and updates alert status.
    """
    # Only Admins can claim alerts
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can claim alerts"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Check if alert exists and is unassigned
        alert = await conn.fetchrow(
            "SELECT id, assignment_status FROM alerts WHERE id = $1",
            alert_id
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        if alert['assignment_status'] != 'unassigned':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alert is already assigned"
            )
        
        # Create assignment
        try:
            assignment = await conn.fetchrow(
                """
                INSERT INTO alert_assignments 
                (alert_id, assigned_to, status, assigned_at, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW(), NOW())
                RETURNING id, alert_id, assigned_to, assigned_at, status, notes, 
                          resolution, resolved_at, escalated_at, escalated_to, 
                          created_at, updated_at
                """,
                alert_id,
                current_user.user_id,
                AssignmentStatus.INVESTIGATING.value
            )
            
            # Update alert assignment_status
            await conn.execute(
                "UPDATE alerts SET assignment_status = $1 WHERE id = $2",
                AssignmentStatus.ASSIGNED.value,
                alert_id
            )
            
            return AlertAssignment.model_validate(dict(assignment))
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to claim alert: {str(e)}"
            )


@router.put("/alerts/{alert_id}/status", response_model=AlertAssignment)
async def update_alert_status(
    alert_id: int,
    update: AlertAssignmentUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update alert assignment status and notes.
    Admin can only update alerts assigned to them.
    Owner can update any alert.
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get current assignment
        assignment = await conn.fetchrow(
            """
            SELECT id, alert_id, assigned_to, status, notes, resolution, 
                   resolved_at, escalated_at, escalated_to
            FROM alert_assignments 
            WHERE alert_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            alert_id
        )
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert assignment not found"
            )
        
        # Check permissions
        if not check_alert_access(current_user, assignment['assigned_to']):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this alert"
            )
        
        # Build update query dynamically
        update_fields = []
        params = []
        param_count = 1
        
        if update.status is not None:
            update_fields.append(f"status = ${param_count}")
            params.append(update.status.value)
            param_count += 1
            
            # If marking as resolved, set resolved_at
            if update.status == AssignmentStatus.RESOLVED:
                update_fields.append(f"resolved_at = ${param_count}")
                params.append(datetime.now())
                param_count += 1
        
        if update.notes is not None:
            update_fields.append(f"notes = ${param_count}")
            params.append(update.notes)
            param_count += 1
        
        if update.resolution is not None:
            update_fields.append(f"resolution = ${param_count}")
            params.append(update.resolution.value)
            param_count += 1
        
        # Always update updated_at
        update_fields.append(f"updated_at = ${param_count}")
        params.append(datetime.now())
        param_count += 1
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Add assignment ID as last parameter
        params.append(assignment['id'])
        
        query = f"""
            UPDATE alert_assignments 
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, alert_id, assigned_to, assigned_at, status, notes, 
                      resolution, resolved_at, escalated_at, escalated_to, 
                      created_at, updated_at
        """
        
        try:
            updated_assignment = await conn.fetchrow(query, *params)
            
            # Update alert assignment_status if resolved
            if update.status == AssignmentStatus.RESOLVED:
                await conn.execute(
                    "UPDATE alerts SET assignment_status = $1 WHERE id = $2",
                    AssignmentStatus.RESOLVED.value,
                    alert_id
                )
            
            return AlertAssignment.model_validate(dict(updated_assignment))
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update alert status: {str(e)}"
            )


@router.post("/alerts/{alert_id}/escalate", response_model=AlertAssignment)
async def escalate_alert(
    alert_id: int,
    escalation: AlertEscalation,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Escalate an alert to the Owner (Admin only).
    Updates assignment with escalation details.
    """
    # Only Admins can escalate
    if not can_escalate_alert(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can escalate alerts"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get current assignment
        assignment = await conn.fetchrow(
            """
            SELECT id, alert_id, assigned_to, status
            FROM alert_assignments 
            WHERE alert_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            alert_id
        )
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert assignment not found"
            )
        
        # Check that the alert is assigned to current user
        if assignment['assigned_to'] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only escalate alerts assigned to you"
            )
        
        # Get the Owner user ID
        owner = await conn.fetchrow(
            "SELECT id FROM users WHERE role = $1 LIMIT 1",
            UserRole.OWNER.value
        )
        
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No Owner found in the system"
            )
        
        # Update assignment with escalation
        try:
            updated_assignment = await conn.fetchrow(
                """
                UPDATE alert_assignments 
                SET status = $1, 
                    escalated_at = NOW(), 
                    escalated_to = $2,
                    notes = CASE 
                        WHEN notes IS NULL THEN $3 
                        ELSE notes || E'\n\n[ESCALATED] ' || $3 
                    END,
                    updated_at = NOW()
                WHERE id = $4
                RETURNING id, alert_id, assigned_to, assigned_at, status, notes, 
                          resolution, resolved_at, escalated_at, escalated_to, 
                          created_at, updated_at
                """,
                AssignmentStatus.ESCALATED.value,
                owner['id'],
                escalation.notes,
                assignment['id']
            )
            
            # Update alert assignment_status
            await conn.execute(
                "UPDATE alerts SET assignment_status = $1 WHERE id = $2",
                AssignmentStatus.ESCALATED.value,
                alert_id
            )
            
            # TODO: Send email notification to Owner
            # This will be implemented when we add email service
            
            return AlertAssignment.model_validate(dict(updated_assignment))
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to escalate alert: {str(e)}"
            )


@router.get("/alerts/my-assignments")
async def get_my_assignments(
    include_resolved: bool = False,
    limit: int = 1000,  # Increased from 100 to 1000 for better retention
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all alerts assigned to the current user with full alert details.
    Admins see their assigned alerts.
    Owner sees all escalated alerts.
    
    Returns enriched data with alert details, device info, and assignment status.
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        if current_user.role == UserRole.OWNER:
            # Owner sees all escalated alerts
            query = """
                SELECT aa.id, aa.alert_id, aa.assigned_to, aa.assigned_at, 
                       aa.status, aa.notes, aa.resolution, aa.resolved_at, 
                       aa.escalated_at, aa.escalated_to, aa.created_at, aa.updated_at,
                       a.rule_name, a.severity, a.details, a.created_at as alert_created_at,
                       a.assignment_status,
                       d.hostname, d.agent_id,
                       u1.email as assigned_to_email,
                       u2.email as escalated_to_email
                FROM alert_assignments aa
                JOIN alerts a ON aa.alert_id = a.id
                LEFT JOIN devices d ON a.agent_id = d.agent_id
                LEFT JOIN users u1 ON aa.assigned_to = u1.id
                LEFT JOIN users u2 ON aa.escalated_to = u2.id
                WHERE aa.escalated_to = $1
            """
            if not include_resolved:
                query += " AND aa.status != 'resolved'"
            query += " ORDER BY aa.escalated_at DESC LIMIT $2"
            assignments = await conn.fetch(query, current_user.user_id, limit)
            
        elif current_user.role == UserRole.ADMIN:
            # Admin sees their assigned alerts
            query = """
                SELECT aa.id, aa.alert_id, aa.assigned_to, aa.assigned_at, 
                       aa.status, aa.notes, aa.resolution, aa.resolved_at, 
                       aa.escalated_at, aa.escalated_to, aa.created_at, aa.updated_at,
                       a.rule_name, a.severity, a.details, a.created_at as alert_created_at,
                       a.assignment_status,
                       d.hostname, d.agent_id,
                       u1.email as assigned_to_email,
                       u2.email as escalated_to_email
                FROM alert_assignments aa
                JOIN alerts a ON aa.alert_id = a.id
                LEFT JOIN devices d ON a.agent_id = d.agent_id
                LEFT JOIN users u1 ON aa.assigned_to = u1.id
                LEFT JOIN users u2 ON aa.escalated_to = u2.id
                WHERE aa.assigned_to = $1
            """
            if not include_resolved:
                query += " AND aa.status != 'resolved'"
            query += " ORDER BY aa.assigned_at DESC LIMIT $2"
            assignments = await conn.fetch(query, current_user.user_id, limit)
        else:
            # Device users don't have assignments
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device users cannot access alert assignments"
            )
        
        # Format results
        result = []
        for assignment in assignments:
            item = dict(assignment)
            # Parse details JSON
            if isinstance(item.get('details'), str):
                try:
                    item['details'] = json.loads(item['details'])
                except:
                    pass
            # Convert agent_id to string
            if item.get('agent_id'):
                item['agent_id'] = str(item['agent_id'])
            result.append(item)
        
        return {
            "total": len(result),
            "assignments": result
        }


@router.get("/alerts/unassigned", response_model=List[dict])
async def get_unassigned_alerts(
    limit: int = 1000,  # Increased from 500 to 1000 for better retention
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all unassigned alerts (Admin and Owner only).
    Returns alert details with IDs for Admins to claim.
    Sorted by severity (high->medium->low) then by created_at (newest first).
    Default limit increased to 1000 for better visibility.
    """
    # Only Admins and Owner can view unassigned alerts
    if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        alerts = await conn.fetch(
            """
            SELECT a.id, a.agent_id, a.rule_name, a.severity, a.details, 
                   a.created_at, a.assignment_status, d.hostname
            FROM alerts a
            LEFT JOIN devices d ON a.agent_id = d.agent_id
            WHERE a.assignment_status = 'unassigned'
            ORDER BY 
                CASE a.severity 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                a.created_at DESC
            LIMIT $1
            """,
            limit
        )
        
        result = []
        for alert in alerts:
            alert_dict = dict(alert)
            # Always include the alert ID prominently
            alert_dict['alert_id'] = alert_dict['id']
            if alert_dict.get('agent_id'):
                alert_dict['agent_id'] = str(alert_dict['agent_id'])
            if isinstance(alert_dict.get('details'), str):
                try:
                    alert_dict['details'] = json.loads(alert_dict['details'])
                except:
                    pass
            result.append(alert_dict)
        
        return result


@router.get("/alerts/assignments/stats")
async def get_assignment_statistics(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get assignment statistics for the current user.
    Shows count by status, resolution type, etc.
    """
    if current_user.role == UserRole.DEVICE_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device users cannot access assignment statistics"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Determine which assignments to query
        if current_user.role == UserRole.OWNER:
            user_condition = "escalated_to = $1"
        else:  # ADMIN
            user_condition = "assigned_to = $1"
        
        # Get counts by status
        status_counts = await conn.fetch(
            f"""
            SELECT status, COUNT(*) as count
            FROM alert_assignments
            WHERE {user_condition}
            GROUP BY status
            """,
            current_user.user_id
        )
        
        # Get counts by resolution type (for resolved alerts)
        resolution_counts = await conn.fetch(
            f"""
            SELECT resolution, COUNT(*) as count
            FROM alert_assignments
            WHERE {user_condition} AND resolution IS NOT NULL
            GROUP BY resolution
            """,
            current_user.user_id
        )
        
        # Get total assignments
        total = await conn.fetchval(
            f"""
            SELECT COUNT(*)
            FROM alert_assignments
            WHERE {user_condition}
            """,
            current_user.user_id
        )
        
        # Get average resolution time
        avg_resolution_time = await conn.fetchval(
            f"""
            SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - assigned_at)))
            FROM alert_assignments
            WHERE {user_condition} AND resolved_at IS NOT NULL
            """,
            current_user.user_id
        )
        
        return {
            "total_assignments": total or 0,
            "by_status": {row['status']: row['count'] for row in status_counts},
            "by_resolution": {row['resolution']: row['count'] for row in resolution_counts},
            "avg_resolution_time_seconds": float(avg_resolution_time) if avg_resolution_time else None
        }


@router.post("/alerts/bulk-assign")
async def bulk_assign_alerts(
    alert_ids: List[int],
    assigned_to_user_id: int | None = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Bulk assign multiple alerts to a user.
    Owner can assign to any admin.
    Admin can only assign to themselves.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Determine target user
    if assigned_to_user_id is None:
        target_user_id = current_user.user_id
    else:
        # Only Owner can assign to others
        if current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Owner can assign alerts to other users"
            )
        target_user_id = assigned_to_user_id
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Verify target user exists and is admin
        target_user = await conn.fetchrow(
            "SELECT id, role FROM users WHERE id = $1",
            target_user_id
        )
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found"
            )
        
        if target_user['role'] not in ['admin', 'owner']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only assign to Admin or Owner users"
            )
        
        # Begin transaction
        async with conn.transaction():
            assigned_count = 0
            failed_alerts = []
            
            for alert_id in alert_ids:
                try:
                    # Check if alert exists and is unassigned
                    alert = await conn.fetchrow(
                        "SELECT id, assignment_status FROM alerts WHERE id = $1",
                        alert_id
                    )
                    
                    if not alert:
                        failed_alerts.append({"alert_id": alert_id, "reason": "not_found"})
                        continue
                    
                    if alert['assignment_status'] != 'unassigned':
                        failed_alerts.append({"alert_id": alert_id, "reason": "already_assigned"})
                        continue
                    
                    # Create assignment
                    await conn.execute(
                        """
                        INSERT INTO alert_assignments 
                        (alert_id, assigned_to, status, assigned_at, created_at, updated_at)
                        VALUES ($1, $2, $3, NOW(), NOW(), NOW())
                        """,
                        alert_id,
                        target_user_id,
                        AssignmentStatus.INVESTIGATING.value
                    )
                    
                    # Update alert status
                    await conn.execute(
                        "UPDATE alerts SET assignment_status = $1 WHERE id = $2",
                        AssignmentStatus.ASSIGNED.value,
                        alert_id
                    )
                    
                    assigned_count += 1
                    
                except Exception as e:
                    failed_alerts.append({"alert_id": alert_id, "reason": str(e)})
            
            return {
                "success": True,
                "assigned_count": assigned_count,
                "total_requested": len(alert_ids),
                "failed_alerts": failed_alerts
            }


@router.post("/alerts/{alert_id}/comment")
async def add_alert_comment(
    alert_id: int,
    comment: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Add a comment to an alert assignment.
    Appends to the notes field with timestamp and user.
    """
    if current_user.role == UserRole.DEVICE_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device users cannot comment on alerts"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get current assignment
        assignment = await conn.fetchrow(
            """
            SELECT id, assigned_to, escalated_to, notes
            FROM alert_assignments 
            WHERE alert_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            alert_id
        )
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert assignment not found"
            )
        
        # Check permissions
        can_comment = (
            assignment['assigned_to'] == current_user.user_id or
            assignment['escalated_to'] == current_user.user_id or
            current_user.role == UserRole.OWNER
        )
        
        if not can_comment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to comment on this alert"
            )
        
        # Get user email for comment attribution
        user = await conn.fetchrow(
            "SELECT email FROM users WHERE id = $1",
            current_user.user_id
        )
        
        # Format new comment
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_comment = f"[{timestamp}] {user['email']}: {comment}"
        
        # Append to existing notes
        current_notes = assignment['notes'] or ""
        updated_notes = current_notes + "\n\n" + new_comment if current_notes else new_comment
        
        # Update assignment
        await conn.execute(
            """
            UPDATE alert_assignments
            SET notes = $1, updated_at = NOW()
            WHERE id = $2
            """,
            updated_notes,
            assignment['id']
        )
        
        return {
            "success": True,
            "message": "Comment added successfully",
            "comment": new_comment
        }


@router.get("/alerts/{alert_id}/details")
async def get_alert_details(
    alert_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get comprehensive details for a specific alert.
    Includes alert data, device info, assignment status, and full history.
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get alert with device details
        alert = await conn.fetchrow(
            """
            SELECT a.*, 
                   d.hostname, d.status as device_status, d.last_seen
            FROM alerts a
            LEFT JOIN devices d ON a.agent_id = d.agent_id
            WHERE a.id = $1
            """,
            alert_id
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check permissions based on role
        if current_user.role == UserRole.DEVICE_USER:
            # Device users can only see alerts from their devices
            device = await conn.fetchrow(
                "SELECT user_id FROM devices WHERE agent_id = $1",
                alert['agent_id']
            )
            if not device or device['user_id'] != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this alert"
                )
        
        # Get assignment details if exists
        assignment = await conn.fetchrow(
            """
            SELECT aa.*, 
                   u1.email as assigned_to_email, u1.role as assigned_to_role,
                   u2.email as escalated_to_email, u2.role as escalated_to_role
            FROM alert_assignments aa
            LEFT JOIN users u1 ON aa.assigned_to = u1.id
            LEFT JOIN users u2 ON aa.escalated_to = u2.id
            WHERE aa.alert_id = $1
            ORDER BY aa.created_at DESC
            LIMIT 1
            """,
            alert_id
        )
        
        # Get all assignment history
        assignment_history = await conn.fetch(
            """
            SELECT aa.id, aa.status, aa.notes, aa.resolution,
                   aa.assigned_at, aa.resolved_at, aa.escalated_at,
                   aa.created_at, aa.updated_at,
                   u1.email as assigned_to_email,
                   u2.email as escalated_to_email
            FROM alert_assignments aa
            LEFT JOIN users u1 ON aa.assigned_to = u1.id
            LEFT JOIN users u2 ON aa.escalated_to = u2.id
            WHERE aa.alert_id = $1
            ORDER BY aa.created_at ASC
            """,
            alert_id
        )
        
        # Format alert data
        alert_dict = dict(alert)
        if alert_dict.get('agent_id'):
            alert_dict['agent_id'] = str(alert_dict['agent_id'])
        if isinstance(alert_dict.get('details'), str):
            try:
                alert_dict['details'] = json.loads(alert_dict['details'])
            except:
                pass
        
        # Format assignment data
        assignment_dict = dict(assignment) if assignment else None
        history_list = [dict(h) for h in assignment_history] if assignment_history else []
        
        return {
            "alert": alert_dict,
            "assignment": assignment_dict,
            "assignment_history": history_list,
            "can_claim": (
                current_user.role in [UserRole.ADMIN, UserRole.OWNER] and
                alert['assignment_status'] == 'unassigned'
            ),
            "can_update": (
                current_user.role == UserRole.OWNER or
                (assignment and assignment['assigned_to'] == current_user.user_id)
            ),
            "can_escalate": (
                current_user.role == UserRole.ADMIN and
                assignment and 
                assignment['assigned_to'] == current_user.user_id and
                assignment['status'] != 'escalated'
            )
        }


@router.get("/alerts/{alert_id}/assignment")
async def get_alert_assignment_details(
    alert_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get detailed assignment information for a specific alert.
    Includes assignment history and user details.
    
    Note: For comprehensive alert details, use GET /api/alerts/{alert_id}/details
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Get assignment with user details
        assignment = await conn.fetchrow(
            """
            SELECT aa.*, 
                   u1.email as assigned_to_email,
                   u2.email as escalated_to_email
            FROM alert_assignments aa
            LEFT JOIN users u1 ON aa.assigned_to = u1.id
            LEFT JOIN users u2 ON aa.escalated_to = u2.id
            WHERE aa.alert_id = $1
            ORDER BY aa.created_at DESC
            LIMIT 1
            """,
            alert_id
        )
        
        if not assignment:
            return {
                "has_assignment": False,
                "alert_id": alert_id
            }
        
        # Check permissions
        can_view = (
            current_user.role == UserRole.OWNER or
            assignment['assigned_to'] == current_user.user_id or
            assignment['escalated_to'] == current_user.user_id
        )
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this assignment"
            )
        
        assignment_dict = dict(assignment)
        
        return {
            "has_assignment": True,
            "alert_id": alert_id,
            "assignment": assignment_dict
        }


@router.get("/alerts/by-status/{assignment_status}")
async def get_alerts_by_status(
    assignment_status: str,
    limit: int = 1000,  # Increased from 100 to 1000 for better retention
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get alerts filtered by assignment status.
    Valid statuses: unassigned, assigned, investigating, resolved, escalated
    """
    valid_statuses = ['unassigned', 'assigned', 'investigating', 'resolved', 'escalated']
    
    if assignment_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    if current_user.role == UserRole.DEVICE_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device users cannot access alert assignments"
        )
    
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        # Build query based on role
        if current_user.role == UserRole.OWNER:
            # Owner sees all alerts
            alerts = await conn.fetch(
                """
                SELECT a.id as alert_id, a.id, a.agent_id, a.rule_name, a.severity, a.details,
                       a.created_at, a.assignment_status,
                       d.hostname,
                       aa.assigned_to, aa.status as assignment_status_detail,
                       aa.id as assignment_id,
                       u.email as assigned_to_email
                FROM alerts a
                LEFT JOIN devices d ON a.agent_id = d.agent_id
                LEFT JOIN alert_assignments aa ON a.id = aa.alert_id
                LEFT JOIN users u ON aa.assigned_to = u.id
                WHERE a.assignment_status = $1
                ORDER BY 
                    CASE a.severity 
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    a.created_at DESC
                LIMIT $2
                """,
                assignment_status,
                limit
            )
        else:  # ADMIN
            # Admin sees their assigned alerts or unassigned
            if assignment_status == 'unassigned':
                alerts = await conn.fetch(
                    """
                    SELECT a.id as alert_id, a.id, a.agent_id, a.rule_name, a.severity, a.details,
                           a.created_at, a.assignment_status,
                           d.hostname
                    FROM alerts a
                    LEFT JOIN devices d ON a.agent_id = d.agent_id
                    WHERE a.assignment_status = 'unassigned'
                    ORDER BY 
                        CASE a.severity 
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                            ELSE 5
                        END,
                        a.created_at DESC
                    LIMIT $1
                    """,
                    limit
                )
            else:
                alerts = await conn.fetch(
                    """
                    SELECT a.id as alert_id, a.id, a.agent_id, a.rule_name, a.severity, a.details,
                           a.created_at, a.assignment_status,
                           d.hostname,
                           aa.assigned_to, aa.status as assignment_status_detail,
                           aa.id as assignment_id,
                           u.email as assigned_to_email
                    FROM alerts a
                    LEFT JOIN devices d ON a.agent_id = d.agent_id
                    LEFT JOIN alert_assignments aa ON a.id = aa.alert_id
                    LEFT JOIN users u ON aa.assigned_to = u.id
                    WHERE a.assignment_status = $1 AND aa.assigned_to = $2
                    ORDER BY 
                        CASE a.severity 
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                            ELSE 5
                        END,
                        a.created_at DESC
                    LIMIT $3
                    """,
                    assignment_status,
                    current_user.user_id,
                    limit
                )
        
        # Format response
        result = []
        for alert in alerts:
            alert_dict = dict(alert)
            # Ensure alert_id is prominent
            if 'id' in alert_dict and 'alert_id' not in alert_dict:
                alert_dict['alert_id'] = alert_dict['id']
            if alert_dict.get('agent_id'):
                alert_dict['agent_id'] = str(alert_dict['agent_id'])
            if isinstance(alert_dict.get('details'), str):
                try:
                    alert_dict['details'] = json.loads(alert_dict['details'])
                except:
                    pass
            result.append(alert_dict)
        
        return {
            "status": assignment_status,
            "count": len(result),
            "alerts": result
        }
