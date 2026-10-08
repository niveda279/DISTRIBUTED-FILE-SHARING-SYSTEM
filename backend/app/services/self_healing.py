"""
Self-Healing Replication Service.

Detects files whose active replica count is below the configured
REPLICATION_FACTOR and automatically copies missing replicas from
a healthy source node to a healthy target node.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.file import File
from app.models.file_location import FileLocation
from app.models.replication_event import ReplicationEvent
from app.models.storage_node import StorageNode
from app.models.system_event import SystemEvent
from app.services import storage_client
from app.services.audit import log_event

logger = logging.getLogger(__name__)
settings = get_settings()


async def _emit_event(db: AsyncSession, event_type: str, payload: str,
                      node_id: str = None, file_id: int = None,
                      severity: str = "INFO"):
    ev = SystemEvent(event_type=event_type, severity=severity,
                     node_id=node_id, file_id=file_id, payload=payload)
    db.add(ev)


async def detect_under_replicated(db: AsyncSession) -> List[File]:
    """Return files with fewer ACTIVE locations than REPLICATION_FACTOR."""
    factor = settings.REPLICATION_FACTOR
    # Load all files with their active locations
    result = await db.execute(
        select(File)
        .options(selectinload(File.locations))
        .where(File.is_current_version == True)  # noqa: E712
    )
    files = result.scalars().all()

    under_replicated = []
    for f in files:
        active = [loc for loc in f.locations if loc.status == "ACTIVE"]
        if len(active) < factor:
            under_replicated.append(f)
    return under_replicated


async def _find_source_node(db: AsyncSession, file: File) -> Optional[str]:
    """Find a healthy node that has an ACTIVE copy of this file."""
    active_locs = [loc for loc in file.locations if loc.status == "ACTIVE"]
    for loc in active_locs:
        node_result = await db.execute(
            select(StorageNode).where(StorageNode.node_id == loc.node_id)
        )
        node = node_result.scalar_one_or_none()
        if node and node.status == "ONLINE":
            # Verify node actually has the file
            try:
                health = await storage_client.check_node_health(loc.node_id)
                if health:
                    return loc.node_id
            except Exception:
                continue
    return None


async def _find_target_node(db: AsyncSession, file: File) -> Optional[str]:
    """Find a healthy node that does NOT already have this file."""
    occupied = {loc.node_id for loc in file.locations if loc.status == "ACTIVE"}
    result = await db.execute(
        select(StorageNode).where(StorageNode.status == "ONLINE")
    )
    nodes = result.scalars().all()
    for node in nodes:
        if node.node_id not in occupied:
            return node.node_id
    return None


async def heal_file(db: AsyncSession, file: File, trigger: str = "AUTO_HEAL") -> bool:
    """
    Copy a missing replica for a file to a new healthy node.
    Returns True if healing succeeded.
    """
    source_node = await _find_source_node(db, file)
    if not source_node:
        logger.warning(f"No healthy source for file {file.id} — cannot heal")
        return False

    target_node = await _find_target_node(db, file)
    if not target_node:
        logger.warning(f"No available target node for file {file.id} — cannot heal")
        return False

    # Create replication event
    rep_event = ReplicationEvent(
        file_id=file.id,
        source_node=source_node,
        target_node=target_node,
        trigger=trigger,
        status="IN_PROGRESS",
    )
    db.add(rep_event)
    await db.flush()

    await _emit_event(
        db, "SELF_HEAL_START",
        f"Healing file {file.id} ({file.original_filename}): {source_node} → {target_node}",
        node_id=target_node, file_id=file.id, severity="WARNING"
    )

    started = datetime.now(timezone.utc)
    try:
        # Retrieve file bytes from source
        file_bytes = await storage_client.retrieve_file_from_node(source_node, file.filename)

        # Push to target
        await storage_client.store_file_on_node(target_node, file.filename, file_bytes, file.original_filename)

        # Record new file_location
        new_loc = FileLocation(
            file_id=file.id,
            node_id=target_node,
            location_type="REPLICA",
            status="ACTIVE",
        )
        db.add(new_loc)

        # Update node file count
        target_result = await db.execute(
            select(StorageNode).where(StorageNode.node_id == target_node)
        )
        t_node = target_result.scalar_one_or_none()
        if t_node:
            t_node.file_count = (t_node.file_count or 0) + 1

        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        rep_event.status = "COMPLETE"
        rep_event.completed_at = datetime.now(timezone.utc)
        rep_event.duration_ms = duration_ms

        await _emit_event(
            db, "SELF_HEAL_COMPLETE",
            f"Replica restored for file {file.id} on {target_node} ({duration_ms}ms)",
            node_id=target_node, file_id=file.id, severity="INFO"
        )

        await log_event(
            db, "REPLICA_HEALED",
            file_id=file.id,
            node_id=target_node,
            details=f"Self-healed replica: {source_node}→{target_node} in {duration_ms}ms",
        )

        logger.info(f"Successfully healed file {file.id}: {source_node}→{target_node}")
        return True

    except Exception as e:
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        rep_event.status = "FAILED"
        rep_event.completed_at = datetime.now(timezone.utc)
        rep_event.duration_ms = duration_ms
        rep_event.error_detail = str(e)

        await _emit_event(
            db, "SELF_HEAL_FAILED",
            f"Healing failed for file {file.id}: {e}",
            node_id=target_node, file_id=file.id, severity="ERROR"
        )

        logger.error(f"Healing failed for file {file.id}: {e}")
        return False


async def run_healing_cycle() -> dict:
    """
    Run a complete self-healing cycle.
    Called periodically by the health monitor.
    Returns summary dict.
    """
    if not settings.SELF_HEALING_ENABLED:
        return {"skipped": True}

    healed = 0
    failed = 0
    under_replicated_ids = []

    async with AsyncSessionLocal() as db:
        try:
            files = await detect_under_replicated(db)
            under_replicated_ids = [f.id for f in files]

            if files:
                logger.info(f"Self-healing: {len(files)} file(s) under-replicated")
                await _emit_event(
                    db, "HEAL_CYCLE_START",
                    f"Healing {len(files)} under-replicated file(s)",
                    severity="WARNING"
                )

            for f in files:
                success = await heal_file(db, f)
                if success:
                    healed += 1
                else:
                    failed += 1

            await db.commit()
        except Exception as e:
            logger.error(f"Healing cycle error: {e}")
            await db.rollback()

    return {
        "under_replicated": len(under_replicated_ids),
        "healed": healed,
        "failed": failed,
        "file_ids": under_replicated_ids,
    }
