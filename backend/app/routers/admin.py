"""Admin router – user management, system stats, audit logs."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.storage_node import StorageNode
from app.models.user import User
from app.schemas.admin import AdminUserResponse, AuditLogResponse, SystemStats
from app.security.jwt import get_current_user
from app.services.audit import log_event

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _require_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


# ──────────────────────── Users ────────────────────────────────

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
):
    _require_admin(current_user)
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users/{user_id}/disable", response_model=AdminUserResponse)
async def disable_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await log_event(db, "DISABLE_USER", user_id=current_user.id, details=f"Disabled user {user_id}")
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/enable", response_model=AdminUserResponse)
async def enable_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await log_event(db, "ENABLE_USER", user_id=current_user.id, details=f"Enabled user {user_id}")
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/promote", response_model=AdminUserResponse)
async def promote_to_admin(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote a user to ADMIN role."""
    _require_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = "ADMIN"
    await log_event(db, "PROMOTE_USER", user_id=current_user.id, details=f"Promoted user {user_id} to ADMIN")
    await db.commit()
    await db.refresh(user)
    return user


# ──────────────────────── Stats ────────────────────────────────

@router.get("/stats", response_model=SystemStats)
async def system_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_files = (await db.execute(select(func.count(File.id)))).scalar_one()
    total_size = (await db.execute(select(func.coalesce(func.sum(File.size), 0)))).scalar_one()

    node_result = await db.execute(select(StorageNode))
    nodes = node_result.scalars().all()
    online_nodes = sum(1 for n in nodes if n.status == "ONLINE")
    offline_nodes = sum(1 for n in nodes if n.status == "OFFLINE")

    return SystemStats(
        total_users=total_users,
        total_files=total_files,
        total_size_bytes=total_size,
        online_nodes=online_nodes,
        offline_nodes=offline_nodes,
        total_nodes=len(nodes),
    )


# ──────────────────────── Audit Logs ───────────────────────────

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    action: Optional[str] = Query(None),
):
    _require_admin(current_user)

    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    if action:
        query = query.where(AuditLog.action == action.upper())

    result = await db.execute(query)
    logs = result.scalars().all()

    out = []
    for log in logs:
        user_email = None
        user_res = await db.execute(select(User).where(User.id == log.user_id))
        u = user_res.scalar_one_or_none()
        if u:
            user_email = u.email

        file_name = None
        if log.file_id:
            file_res = await db.execute(select(File).where(File.id == log.file_id))
            f = file_res.scalar_one_or_none()
            if f:
                file_name = f.original_filename

        out.append(
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=user_email,
                action=log.action,
                file_id=log.file_id,
                file_name=file_name,
                node_id=log.node_id,
                details=log.details,
                timestamp=log.timestamp,
            )
        )
    return out
