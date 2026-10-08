"""Self-healing replication router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.replication_event import ReplicationEvent
from app.models.system_event import SystemEvent
from app.models.user import User
from app.security.jwt import get_current_user
from app.services.self_healing import run_healing_cycle, detect_under_replicated

router = APIRouter(prefix="/api/admin/self-healing", tags=["Self-Healing"])


def _require_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/events")
async def healing_events(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await db.execute(
        select(ReplicationEvent)
        .order_by(ReplicationEvent.started_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "file_id": e.file_id,
            "source_node": e.source_node,
            "target_node": e.target_node,
            "trigger": e.trigger,
            "status": e.status,
            "started_at": e.started_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "duration_ms": e.duration_ms,
            "error_detail": e.error_detail,
        }
        for e in events
    ]


@router.get("/status")
async def healing_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    from sqlalchemy import func
    from app.config import get_settings
    settings = get_settings()

    under_rep = await detect_under_replicated(db)
    total_healed = (await db.execute(
        select(func.count(ReplicationEvent.id))
        .where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    total_failed = (await db.execute(
        select(func.count(ReplicationEvent.id))
        .where(ReplicationEvent.status == "FAILED")
    )).scalar_one()

    avg_duration = (await db.execute(
        select(func.coalesce(func.avg(ReplicationEvent.duration_ms), 0))
        .where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    return {
        "replication_factor": settings.REPLICATION_FACTOR,
        "under_replicated_files": len(under_rep),
        "under_replicated_ids": [f.id for f in under_rep],
        "total_healed": total_healed,
        "total_failed": total_failed,
        "avg_recovery_ms": round(float(avg_duration), 1),
        "healing_enabled": settings.SELF_HEALING_ENABLED,
    }


@router.post("/repair")
async def trigger_repair(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a self-healing cycle."""
    _require_admin(current_user)
    result = await run_healing_cycle()
    return {
        "message": "Healing cycle complete",
        **result
    }
