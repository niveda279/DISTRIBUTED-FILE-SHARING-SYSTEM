"""Background health monitor: periodically polls all storage nodes."""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.storage_node import StorageNode
from app.services.storage_client import check_node_health

logger = logging.getLogger(__name__)
settings = get_settings()

_monitor_task = None


async def _run_health_checks():
    """Run one round of health checks against all registered nodes."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(StorageNode))
        nodes = list(result.scalars().all())

    for node in nodes:
        if node.status == "DISABLED":
            continue  # skip administratively disabled nodes

        health = await check_node_health(node.node_id)
        async with AsyncSessionLocal() as db:
            node_result = await db.execute(
                select(StorageNode).where(StorageNode.node_id == node.node_id)
            )
            db_node = node_result.scalar_one_or_none()
            if not db_node:
                continue

            if health:
                db_node.status = "ONLINE"
                db_node.available_storage = health.get("available_storage", 0)
                db_node.total_storage = health.get("total_storage", 0)
                db_node.file_count = health.get("file_count", 0)
                db_node.last_heartbeat = datetime.now(timezone.utc)
                logger.debug(f"Node {node.node_id} is ONLINE")
            else:
                if db_node.status not in ("DISABLED",):
                    db_node.status = "OFFLINE"
                logger.warning(f"Node {node.node_id} is OFFLINE")

            await db.commit()


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
