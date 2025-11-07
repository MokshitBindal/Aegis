# aegis-server/routers/alert_triage.py

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


@router.get("/alerts/my-assignments", response_model=List[AlertAssignment])
async def get_my_assignments(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all alerts assigned to the current user.
    Admins see their assigned alerts.
    Owner sees all escalated alerts.
    """
    pool = get_db_pool()
    
    async with pool.acquire() as conn:
        if current_user.role == UserRole.OWNER:
            # Owner sees all escalated alerts
            assignments = await conn.fetch(
                """
                SELECT id, alert_id, assigned_to, assigned_at, status, notes, 
                       resolution, resolved_at, escalated_at, escalated_to, 
                       created_at, updated_at
                FROM alert_assignments 
                WHERE escalated_to = $1
                ORDER BY escalated_at DESC
                """,
                current_user.user_id
            )
        elif current_user.role == UserRole.ADMIN:
            # Admin sees their assigned alerts
            assignments = await conn.fetch(
                """
                SELECT id, alert_id, assigned_to, assigned_at, status, notes, 
                       resolution, resolved_at, escalated_at, escalated_to, 
                       created_at, updated_at
                FROM alert_assignments 
                WHERE assigned_to = $1
                ORDER BY assigned_at DESC
                """,
                current_user.user_id
            )
        else:
            # Device users don't have assignments
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device users cannot access alert assignments"
            )
        
        return [AlertAssignment.model_validate(dict(a)) for a in assignments]


@router.get("/alerts/unassigned", response_model=List[dict])
async def get_unassigned_alerts(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all unassigned alerts (Admin and Owner only).
    Returns alert details for Admins to claim.
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
            SELECT id, agent_id, alert_type, severity, message, 
                   triggered_at, assignment_status, created_at
            FROM alerts 
            WHERE assignment_status = 'unassigned'
            ORDER BY triggered_at DESC
            LIMIT 100
            """
        )
        
        return [dict(a) for a in alerts]
