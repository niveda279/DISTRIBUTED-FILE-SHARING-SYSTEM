"""Admin router – user management, system stats, audit logs, security events."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.node_metric import NodeMetric
from app.models.security_event import SecurityEvent
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
    total_files = (await db.execute(
        select(func.count(File.id)).where(File.is_current_version == True)  # noqa: E712
    )).scalar_one()
    total_size = (await db.execute(
        select(func.coalesce(func.sum(File.size), 0))
        .where(File.is_current_version == True)  # noqa: E712
    )).scalar_one()
    node_result = await db.execute(select(StorageNode))
    nodes = node_result.scalars().all()
    return SystemStats(
        total_users=total_users,
        total_files=total_files,
        total_size_bytes=total_size,
        online_nodes=sum(1 for n in nodes if n.status == "ONLINE"),
        offline_nodes=sum(1 for n in nodes if n.status == "OFFLINE"),
        total_nodes=len(nodes),
    )


@router.get("/stats/extended")
async def extended_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full analytics for admin dashboard."""
    _require_admin(current_user)
    from app.services.deduplication import get_dedup_savings
    from app.services.reliability import compute_reliability_score
    from app.models.replication_event import ReplicationEvent

    dedup = await get_dedup_savings(db)
    reliability = await compute_reliability_score(db)

    total_healed = (await db.execute(
        select(func.count(ReplicationEvent.id)).where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    total_failed_heal = (await db.execute(
        select(func.count(ReplicationEvent.id)).where(ReplicationEvent.status == "FAILED")
    )).scalar_one()

    avg_recovery_ms = (await db.execute(
        select(func.coalesce(func.avg(ReplicationEvent.duration_ms), 0))
        .where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    return {
        "deduplication": dedup,
        "reliability": reliability,
        "healing": {
            "total_healed": total_healed,
            "total_failed": total_failed_heal,
            "avg_recovery_ms": round(float(avg_recovery_ms), 1),
        },
    }


@router.get("/nodes/{node_id}/metrics")
async def node_metrics_history(
    node_id: str,
    hours: int = Query(6, ge=1, le=48),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-node time-series metrics for charts."""
    _require_admin(current_user)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(NodeMetric)
        .where(NodeMetric.node_id == node_id)
        .where(NodeMetric.sampled_at >= since)
        .order_by(NodeMetric.sampled_at.asc())
    )
    metrics = result.scalars().all()
    return [
        {
            "sampled_at": m.sampled_at.isoformat(),
            "latency_ms": m.latency_ms,
            "available_storage": m.available_storage,
            "used_storage": m.used_storage,
            "file_count": m.file_count,
            "is_online": m.is_online,
        }
        for m in metrics
    ]


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
        out.append(AuditLogResponse(
            id=log.id, user_id=log.user_id, user_email=user_email,
            action=log.action, file_id=log.file_id, file_name=file_name,
            node_id=log.node_id, details=log.details, timestamp=log.timestamp,
        ))
    return out


# ──────────────────────── Security Events ──────────────────────

@router.get("/security/events")
async def security_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    risk_level: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
):
    _require_admin(current_user)
    query = select(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(limit)
    if risk_level:
        query = query.where(SecurityEvent.risk_level == risk_level.upper())
    if event_type:
        query = query.where(SecurityEvent.event_type == event_type.upper())
    result = await db.execute(query)
    events = result.scalars().all()

    out = []
    for ev in events:
        user_email = None
        if ev.user_id:
            u_res = await db.execute(select(User).where(User.id == ev.user_id))
            u = u_res.scalar_one_or_none()
            user_email = u.email if u else None
        out.append({
            "id": ev.id,
            "user_id": ev.user_id,
            "user_email": user_email,
            "event_type": ev.event_type,
            "risk_level": ev.risk_level,
            "details": ev.details,
            "timestamp": ev.timestamp.isoformat(),
        })
    return out


@router.get("/security/summary")
async def security_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    window = datetime.now(timezone.utc) - timedelta(hours=24)

    high = (await db.execute(
        select(func.count(SecurityEvent.id))
        .where(SecurityEvent.risk_level == "HIGH")
        .where(SecurityEvent.timestamp >= window)
    )).scalar_one()

    medium = (await db.execute(
        select(func.count(SecurityEvent.id))
        .where(SecurityEvent.risk_level == "MEDIUM")
        .where(SecurityEvent.timestamp >= window)
    )).scalar_one()

    low = (await db.execute(
        select(func.count(SecurityEvent.id))
        .where(SecurityEvent.risk_level == "LOW")
        .where(SecurityEvent.timestamp >= window)
    )).scalar_one()

    integrity = (await db.execute(
        select(func.count(SecurityEvent.id))
        .where(SecurityEvent.event_type == "INTEGRITY_FAILURE")
        .where(SecurityEvent.timestamp >= window)
    )).scalar_one()

    return {
        "period_hours": 24,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "integrity_failures": integrity,
        "total": high + medium + low,
    }
