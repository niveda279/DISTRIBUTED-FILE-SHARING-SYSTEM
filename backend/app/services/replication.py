"""File replication service."""
import asyncio
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_location import FileLocation
from app.models.storage_node import StorageNode
from app.services import storage_client

logger = logging.getLogger(__name__)


async def replicate_to_node(
    node_id: str, file_id: str, file_bytes: bytes, original_filename: str
) -> bool:
    """
    Replicate a file to a specific storage node.
    Returns True on success, False on failure.
    """
    try:
        await storage_client.store_file_on_node(node_id, file_id, file_bytes, original_filename)
        logger.info(f"Replicated file {file_id} to {node_id}")
        return True
    except Exception as e:
        logger.error(f"Replication of {file_id} to {node_id} failed: {e}")
        return False


async def create_replicas(
    db: AsyncSession,
    file_id_int: int,
    storage_file_id: str,
    file_bytes: bytes,
    original_filename: str,
    replica_nodes: List[StorageNode],
) -> List[str]:
    """
    Send the file to each replica node and record FileLocation rows.
    Returns list of node_ids that succeeded.
    """
    succeeded = []
    tasks = [
        replicate_to_node(n.node_id, storage_file_id, file_bytes, original_filename)
        for n in replica_nodes
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for node, result in zip(replica_nodes, results):
        if result is True:
            loc = FileLocation(
                file_id=file_id_int,
                node_id=node.node_id,
                location_type="REPLICA",
                status="ACTIVE",
            )
            db.add(loc)
            node.file_count = (node.file_count or 0) + 1
            succeeded.append(node.node_id)
        else:
            logger.warning(f"Replica on {node.node_id} skipped due to error")

    return succeeded
