"""File activity timeline and replica status router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.file_location import FileLocation
from app.models.file_permission import FilePermission
from app.models.storage_node import StorageNode
from app.models.user import User
from app.security.jwt import get_current_user

router = APIRouter(prefix="/api/files", tags=["Activity"])


def _can_access(file: File, user: User) -> bool:
    return file.owner_id == user.id or user.role == "ADMIN"


@router.get("/{file_id}/activity")
async def file_activity(
    file_id: int,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """File activity timeline from audit logs."""
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access
    if not _can_access(f, current_user):
        perm_result = await db.execute(
            select(FilePermission).where(
                FilePermission.file_id == file_id,
                FilePermission.user_id == current_user.id,
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    logs_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.file_id == file_id)
        .order_by(AuditLog.timestamp.asc())
        .limit(limit)
    )
    logs = logs_result.scalars().all()

    # Enrich with user info
    timeline = []
    for log in logs:
        user_email = None
        if log.user_id:
            u_result = await db.execute(select(User).where(User.id == log.user_id))
            u = u_result.scalar_one_or_none()
            user_email = u.email if u else None
        timeline.append({
            "id": log.id,
            "action": log.action,
            "user_id": log.user_id,
            "user_email": user_email,
            "node_id": log.node_id,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        })
    return timeline


@router.get("/{file_id}/replicas")
async def file_replicas(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current replica locations and their node status."""
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    if not _can_access(f, current_user):
        perm_result = await db.execute(
            select(FilePermission).where(
                FilePermission.file_id == file_id,
                FilePermission.user_id == current_user.id,
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    locs_result = await db.execute(
        select(FileLocation).where(FileLocation.file_id == file_id)
    )
    locations = locs_result.scalars().all()

    replicas = []
    for loc in locations:
        node_result = await db.execute(
            select(StorageNode).where(StorageNode.node_id == loc.node_id)
        )
        node = node_result.scalar_one_or_none()
        replicas.append({
            "id": loc.id,
            "node_id": loc.node_id,
            "node_name": node.name if node else loc.node_id,
            "node_status": node.status if node else "UNKNOWN",
            "location_type": loc.location_type,
            "status": loc.status,
            "created_at": loc.created_at.isoformat(),
            "node_latency_ms": round(node.avg_latency_ms or 0, 1) if node else None,
        })
    return replicas
