"""Cluster topology, metrics, reliability, and SSE stream router."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.file_location import FileLocation
from app.models.node_metric import NodeMetric
from app.models.replication_event import ReplicationEvent
from app.models.simulation_state import SimulationState
from app.models.storage_node import StorageNode
from app.models.system_event import SystemEvent
from app.models.user import User
from app.security.jwt import get_current_user
from app.services.deduplication import get_dedup_savings
from app.services.placement_engine import get_placement_scores
from app.services.reliability import compute_reliability_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cluster", tags=["Cluster"])


@router.get("/topology")
async def cluster_topology(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full cluster view: nodes with placement scores, sim state, per-node file counts."""
    scores = await get_placement_scores(db)

    sims_result = await db.execute(select(SimulationState))
    sim_map = {s.node_id: s for s in sims_result.scalars().all()}

    nodes_data = []
    for ns in scores:
        node = ns.node
        sim = sim_map.get(node.node_id)

        # Count replicas
        primary_count_result = await db.execute(
            select(func.count(FileLocation.id))
            .where(FileLocation.node_id == node.node_id)
            .where(FileLocation.location_type == "PRIMARY")
            .where(FileLocation.status == "ACTIVE")
        )
        replica_count_result = await db.execute(
            select(func.count(FileLocation.id))
            .where(FileLocation.node_id == node.node_id)
            .where(FileLocation.location_type == "REPLICA")
            .where(FileLocation.status == "ACTIVE")
        )

        nodes_data.append({
            **ns.to_dict(),
            "name": node.name,
            "host": node.host,
            "port": node.port,
            "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
            "primary_files": primary_count_result.scalar_one(),
            "replica_files": replica_count_result.scalar_one(),
            "simulation": {
                "is_simulated": sim.is_simulated if sim else False,
                "simulated_status": sim.simulated_status if sim else None,
                "simulated_latency_ms": sim.simulated_latency_ms if sim else 0,
                "simulated_load_pct": sim.simulated_load_pct if sim else 0,
                "simulated_storage_warning": sim.simulated_storage_warning if sim else False,
            } if sim else None,
        })

    return {
        "nodes": nodes_data,
        "cluster_summary": {
            "total_nodes": len(scores),
            "online_nodes": sum(1 for s in scores if s.health_score == 100.0),
            "offline_nodes": sum(1 for s in scores if s.health_score == 0.0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/metrics")
async def cluster_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate analytics metrics."""
    from app.config import get_settings
    settings = get_settings()

    total_files = (await db.execute(
        select(func.count(File.id)).where(File.is_current_version == True)  # noqa: E712
    )).scalar_one()

    total_size = (await db.execute(
        select(func.coalesce(func.sum(File.size), 0))
        .where(File.is_current_version == True)  # noqa: E712
    )).scalar_one()

    total_locs = (await db.execute(
        select(func.count(FileLocation.id)).where(FileLocation.status == "ACTIVE")
    )).scalar_one()

    # Replication overhead = total location bytes vs primary-only bytes
    primary_size = (await db.execute(
        select(func.coalesce(func.sum(File.size), 0))
        .select_from(File)
        .join(FileLocation, (FileLocation.file_id == File.id) & (FileLocation.location_type == "PRIMARY"))
        .where(FileLocation.status == "ACTIVE")
        .where(File.is_current_version == True)  # noqa: E712
    )).scalar_one()

    nodes_result = await db.execute(select(StorageNode))
    nodes = nodes_result.scalars().all()

    # Failover count from audit logs
    failover_count = (await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.action == "DOWNLOAD")
        .where(AuditLog.details.like("%replica%").op("OR")(AuditLog.details.like("%failover%")))
    )).scalar_one()

    # Healing stats
    healed_count = (await db.execute(
        select(func.count(ReplicationEvent.id))
        .where(ReplicationEvent.trigger == "AUTO_HEAL")
        .where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    avg_recovery_ms = (await db.execute(
        select(func.coalesce(func.avg(ReplicationEvent.duration_ms), 0))
        .where(ReplicationEvent.status == "COMPLETE")
    )).scalar_one()

    # Upload/Download counts (24h)
    window_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    upload_count_24h = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.action == "UPLOAD")
        .where(AuditLog.timestamp >= window_24h)
    )).scalar_one()

    download_count_24h = (await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.action == "DOWNLOAD")
        .where(AuditLog.timestamp >= window_24h)
    )).scalar_one()

    dedup = await get_dedup_savings(db)

    return {
        "files": {
            "total": total_files,
            "total_size_bytes": int(total_size),
            "total_locations": total_locs,
            "replication_factor": settings.REPLICATION_FACTOR,
        },
        "nodes": {
            "total": len(nodes),
            "online": sum(1 for n in nodes if n.status == "ONLINE"),
            "offline": sum(1 for n in nodes if n.status == "OFFLINE"),
            "total_storage_bytes": sum(n.total_storage or 0 for n in nodes),
            "available_storage_bytes": sum(n.available_storage or 0 for n in nodes),
            "avg_latency_ms": round(
                sum(n.avg_latency_ms or 0 for n in nodes) / max(len(nodes), 1), 2
            ),
        },
        "healing": {
            "healed_count": healed_count,
            "avg_recovery_ms": round(float(avg_recovery_ms), 1),
        },
        "deduplication": dedup,
        "activity": {
            "uploads_24h": upload_count_24h,
            "downloads_24h": download_count_24h,
        },
        "integrity_failures": (await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == "INTEGRITY_FAILURE")
        )).scalar_one(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/reliability")
async def reliability_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute and return the system reliability score."""
    return await compute_reliability_score(db)


@router.get("/node-history/{node_id}")
async def node_history(
    node_id: str,
    hours: int = 6,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return time-series node metrics for charting."""
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
            "placement_score": m.placement_score,
        }
        for m in metrics
    ]


@router.get("/events/recent")
async def recent_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent system events for dashboard."""
    result = await db.execute(
        select(SystemEvent)
        .order_by(SystemEvent.timestamp.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "node_id": e.node_id,
            "file_id": e.file_id,
            "payload": e.payload,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]


async def _sse_event_stream(request: Request) -> AsyncGenerator[str, None]:
    """Async generator that pushes new system events via SSE."""
    last_id = 0
    try:
        while True:
            if await request.is_disconnected():
                break
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SystemEvent)
                    .where(SystemEvent.id > last_id)
                    .order_by(SystemEvent.id.asc())
                    .limit(20)
                )
                events = result.scalars().all()
                for ev in events:
                    last_id = ev.id
                    data = json.dumps({
                        "id": ev.id,
                        "event_type": ev.event_type,
                        "severity": ev.severity,
                        "node_id": ev.node_id,
                        "file_id": ev.file_id,
                        "payload": ev.payload,
                        "timestamp": ev.timestamp.isoformat(),
                    })
                    yield f"data: {data}\n\n"

            # Also send heartbeat every 5s
            yield f"data: {json.dumps({'event_type': 'PING', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass


@router.get("/events/stream")
async def events_stream(request: Request, current_user: User = Depends(get_current_user)):
    """Server-Sent Events stream for real-time dashboard updates."""
    return StreamingResponse(
        _sse_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
