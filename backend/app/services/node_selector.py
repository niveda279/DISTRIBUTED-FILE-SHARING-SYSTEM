"""Node selection algorithm: least-loaded healthy node."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_node import StorageNode


async def get_healthy_nodes(db: AsyncSession) -> List[StorageNode]:
    """Return all nodes with ONLINE status, ordered by file_count ascending."""
    result = await db.execute(
        select(StorageNode)
        .where(StorageNode.status == "ONLINE")
        .order_by(StorageNode.file_count.asc(), StorageNode.available_storage.desc())
    )
    return list(result.scalars().all())


async def select_primary_node(db: AsyncSession) -> Optional[StorageNode]:
    """Pick the least-loaded healthy node for primary storage."""
    nodes = await get_healthy_nodes(db)
    return nodes[0] if nodes else None


async def select_replica_nodes(
    db: AsyncSession, exclude_node_id: str, count: int = 1
) -> List[StorageNode]:
    """Pick healthy nodes for replicas, excluding the primary."""
    nodes = await get_healthy_nodes(db)
    replicas = [n for n in nodes if n.node_id != exclude_node_id]
    return replicas[:count]
