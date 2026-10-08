"""Node selection algorithm — delegates to the intelligent placement engine."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_node import StorageNode
from app.services.placement_engine import (
    select_primary_with_score,
    select_replica_with_score,
    get_placement_scores,
)


async def get_healthy_nodes(db: AsyncSession) -> List[StorageNode]:
    """Return all ONLINE nodes ordered by placement score (best first)."""
    scores = await get_placement_scores(db)
    return [s.node for s in scores if s.health_score == 100.0]


async def select_primary_node(db: AsyncSession, file_size: int = 0) -> Optional[StorageNode]:
    """Pick the best node for primary storage using scoring engine."""
    score = await select_primary_with_score(db, file_size)
    return score.node if score else None


async def select_replica_nodes(
    db: AsyncSession, exclude_node_id: str, count: int = 1, file_size: int = 0
) -> List[StorageNode]:
    """Pick best replica nodes, excluding the primary."""
    scores = await select_replica_with_score(db, exclude_node_id, file_size, count)
    return [s.node for s in scores]
