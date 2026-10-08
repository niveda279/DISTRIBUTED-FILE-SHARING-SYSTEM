"""
System Reliability Score Service.

Calculates a single 0–100 reliability score from real system metrics:
  - Node availability (40%)
  - Replication health (30%)
  - Storage capacity margin (15%)
  - Integrity status (10%)
  - Recent failure recovery (5%)

Higher = better. Score comes with a breakdown for transparency.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.models.file_location import FileLocation
from app.models.replication_event import ReplicationEvent
from app.models.security_event import SecurityEvent
from app.models.storage_node import StorageNode

logger = logging.getLogger(__name__)

WEIGHTS = {
    "node_availability": 0.40,
    "replication_health": 0.30,
    "storage_capacity": 0.15,
    "integrity": 0.10,
    "recovery_success": 0.05,
}


async def compute_reliability_score(db) -> dict:
    """Compute system reliability score with full breakdown."""

    # ── Node Availability ─────────────────────────────────────
    node_result = await db.execute(select(StorageNode))
    nodes = node_result.scalars().all()
    total_nodes = len(nodes) or 1
    online_nodes = sum(1 for n in nodes if n.status == "ONLINE")
    node_avail_pct = (online_nodes / total_nodes) * 100
    node_score = node_avail_pct

    # ── Replication Health ────────────────────────────────────
    from app.config import get_settings
    settings = get_settings()
    factor = settings.REPLICATION_FACTOR

    files_result = await db.execute(
        select(File).where(File.is_current_version == True)  # noqa: E712
    )
    files = files_result.scalars().all()
    total_files = len(files)

    if total_files == 0:
        replication_score = 100.0
    else:
        healthy_files = 0
        for f in files:
            locs_result = await db.execute(
                select(FileLocation)
                .where(FileLocation.file_id == f.id)
                .where(FileLocation.status == "ACTIVE")
            )
            active_count = len(locs_result.scalars().all())
            if active_count >= factor:
                healthy_files += 1
        replication_score = (healthy_files / total_files) * 100

    # ── Storage Capacity ──────────────────────────────────────
    total_storage = sum(n.total_storage or 0 for n in nodes) or 1
    avail_storage = sum(n.available_storage or 0 for n in nodes)
    storage_score = min(100.0, (avail_storage / total_storage) * 100)

    # ── Integrity Status ──────────────────────────────────────
    from datetime import datetime, timedelta, timezone
    window = datetime.now(timezone.utc) - timedelta(hours=24)
    integrity_count_result = await db.execute(
        select(func.count(SecurityEvent.id))
        .where(SecurityEvent.event_type == "INTEGRITY_FAILURE")
        .where(SecurityEvent.timestamp >= window)
    )
    integrity_failures = integrity_count_result.scalar_one()
    # Penalise: each failure costs 10 points
    integrity_score = max(0.0, 100.0 - integrity_failures * 10)

    # ── Recovery Success ──────────────────────────────────────
    recent_window = datetime.now(timezone.utc) - timedelta(hours=24)
    total_events = await db.execute(
        select(func.count(ReplicationEvent.id))
        .where(ReplicationEvent.trigger == "AUTO_HEAL")
        .where(ReplicationEvent.started_at >= recent_window)
    )
    total_heal = total_events.scalar_one() or 0

    success_events = await db.execute(
        select(func.count(ReplicationEvent.id))
        .where(ReplicationEvent.trigger == "AUTO_HEAL")
        .where(ReplicationEvent.status == "COMPLETE")
        .where(ReplicationEvent.started_at >= recent_window)
    )
    success_heal = success_events.scalar_one() or 0

    recovery_score = (success_heal / total_heal * 100) if total_heal > 0 else 100.0

    # ── Final Score ───────────────────────────────────────────
    final_score = (
        WEIGHTS["node_availability"] * node_score
        + WEIGHTS["replication_health"] * replication_score
        + WEIGHTS["storage_capacity"] * storage_score
        + WEIGHTS["integrity"] * integrity_score
        + WEIGHTS["recovery_success"] * recovery_score
    )
    final_score = round(final_score, 1)

    if final_score >= 95:
        status = "EXCELLENT"
    elif final_score >= 80:
        status = "HEALTHY"
    elif final_score >= 60:
        status = "WARNING"
    else:
        status = "CRITICAL"

    return {
        "final_score": final_score,
        "status": status,
        "breakdown": {
            "node_availability": {
                "score": round(node_score, 1),
                "weight": WEIGHTS["node_availability"],
                "detail": f"{online_nodes}/{total_nodes} nodes online",
            },
            "replication_health": {
                "score": round(replication_score, 1),
                "weight": WEIGHTS["replication_health"],
                "detail": f"{total_files} files, factor={factor}",
            },
            "storage_capacity": {
                "score": round(storage_score, 1),
                "weight": WEIGHTS["storage_capacity"],
                "detail": f"{avail_storage // (1024**3)} GB free of {total_storage // (1024**3)} GB",
            },
            "integrity": {
                "score": round(integrity_score, 1),
                "weight": WEIGHTS["integrity"],
                "detail": f"{integrity_failures} integrity failure(s) in 24h",
            },
            "recovery_success": {
                "score": round(recovery_score, 1),
                "weight": WEIGHTS["recovery_success"],
                "detail": f"{success_heal}/{total_heal} heals succeeded in 24h",
            },
        },
    }
