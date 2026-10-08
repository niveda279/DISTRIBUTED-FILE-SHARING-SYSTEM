"""Background health monitor: periodically polls all storage nodes,
tracks latency, stores node_metrics snapshots, triggers self-healing,
and runs security analysis."""
import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.node_metric import NodeMetric
from app.models.storage_node import StorageNode
from app.models.system_event import SystemEvent
from app.services.storage_client import check_node_health

logger = logging.getLogger(__name__)
settings = get_settings()

_monitor_task = None
_cycle_count = 0
_SECURITY_ANALYSIS_EVERY = 3   # run security analysis every N health cycles
_HEAL_EVERY = 2                  # run healing every N health cycles


async def _emit_event(node_id: str, event_type: str, payload: str, severity: str = "INFO"):
    """Emit a SystemEvent without a db session (creates its own)."""
    async with AsyncSessionLocal() as db:
        db.add(SystemEvent(event_type=event_type, severity=severity,
                           node_id=node_id, payload=payload))
        await db.commit()


async def _run_health_checks():
    """Run one round of health checks against all registered nodes."""
    global _cycle_count
    _cycle_count += 1

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(StorageNode))
        nodes = list(result.scalars().all())

    for node in nodes:
        if node.status == "DISABLED":
            continue

        start_ts = time.monotonic()
        health = await check_node_health(node.node_id)
        latency_ms = (time.monotonic() - start_ts) * 1000

        async with AsyncSessionLocal() as db:
            node_result = await db.execute(
                select(StorageNode).where(StorageNode.node_id == node.node_id)
            )
            db_node = node_result.scalar_one_or_none()
            if not db_node:
                continue

            prev_status = db_node.status

            if health:
                db_node.status = "ONLINE"
                db_node.available_storage = health.get("available_storage", 0)
                db_node.total_storage = health.get("total_storage", 0)
                db_node.file_count = health.get("file_count", 0)
                db_node.last_heartbeat = datetime.now(timezone.utc)
                db_node.last_latency_ms = round(latency_ms, 2)
                # Rolling average latency
                if db_node.avg_latency_ms == 0:
                    db_node.avg_latency_ms = latency_ms
                else:
                    db_node.avg_latency_ms = round(
                        db_node.avg_latency_ms * 0.7 + latency_ms * 0.3, 2
                    )
                db_node.request_count = (db_node.request_count or 0) + 1

                if prev_status not in ("ONLINE",) and prev_status not in ("UNKNOWN",):
                    # Node came back online
                    db.add(SystemEvent(
                        event_type="NODE_ONLINE",
                        severity="INFO",
                        node_id=node.node_id,
                        payload=f"Node {node.node_id} is back ONLINE"
                    ))

                logger.debug(f"Node {node.node_id} ONLINE (latency={latency_ms:.0f}ms)")
            else:
                if db_node.status not in ("DISABLED",):
                    if db_node.status == "ONLINE":
                        # Node just went offline
                        db_node.failure_count = (db_node.failure_count or 0) + 1
                        db.add(SystemEvent(
                            event_type="NODE_OFFLINE",
                            severity="ERROR",
                            node_id=node.node_id,
                            payload=f"Node {node.node_id} went OFFLINE"
                        ))
                    db_node.status = "OFFLINE"
                logger.warning(f"Node {node.node_id} OFFLINE")

            # Record metric snapshot
            db.add(NodeMetric(
                node_id=db_node.node_id,
                latency_ms=round(latency_ms, 2),
                available_storage=db_node.available_storage,
                used_storage=max(0, (db_node.total_storage or 0) - (db_node.available_storage or 0)),
                file_count=db_node.file_count,
                request_count=db_node.request_count,
                is_online=db_node.status == "ONLINE",
                placement_score=0,  # updated by placement engine in the router
            ))

            await db.commit()

    # ── Self-Healing ────────────────────────────────────────
    if _cycle_count % _HEAL_EVERY == 0:
        try:
            from app.services.self_healing import run_healing_cycle
            result = await run_healing_cycle()
            if result.get("healed", 0) > 0:
                logger.info(f"Self-healing: {result['healed']} file(s) repaired")
        except Exception as e:
            logger.error(f"Self-healing failed: {e}")

    # ── Security Analysis ───────────────────────────────────
    if _cycle_count % _SECURITY_ANALYSIS_EVERY == 0:
        try:
            from app.services.security_monitor import run_security_analysis
            async with AsyncSessionLocal() as db:
                await run_security_analysis(db)
        except Exception as e:
            logger.error(f"Security analysis failed: {e}")


async def _monitor_loop():
    interval = settings.HEALTH_CHECK_INTERVAL
    logger.info(f"Health monitor started (interval={interval}s)")
    while True:
        try:
            await _run_health_checks()
        except Exception as e:
            logger.error(f"Health check error: {e}")
        await asyncio.sleep(interval)


def start_health_monitor():
    global _monitor_task
    _monitor_task = asyncio.create_task(_monitor_loop())


def stop_health_monitor():
    global _monitor_task
    if _monitor_task:
        _monitor_task.cancel()
        _monitor_task = None
