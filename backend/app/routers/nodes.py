"""Storage nodes router – list & status (public); manage (admin)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.storage_node import StorageNode
from app.models.user import User
from app.schemas.node import NodeResponse
from app.security.jwt import get_current_user
from app.services.storage_client import check_node_health

router = APIRouter(prefix="/api/nodes", tags=["Nodes"])


def _require_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/", response_model=List[NodeResponse])
async def list_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all registered storage nodes."""
    result = await db.execute(select(StorageNode))
    nodes = result.scalars().all()
    return nodes


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(StorageNode).where(StorageNode.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/{node_id}/ping")
async def ping_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Immediately health-check a node and return live status."""
    result = await db.execute(select(StorageNode).where(StorageNode.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    health = await check_node_health(node_id)
    if health:
        return {"node_id": node_id, "online": True, **health}
    return {"node_id": node_id, "online": False}


@router.post("/{node_id}/disable", response_model=NodeResponse)
async def disable_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Administratively disable a node (admin only)."""
    _require_admin(current_user)
    result = await db.execute(select(StorageNode).where(StorageNode.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.status = "DISABLED"
    await db.commit()
    await db.refresh(node)
    return node


@router.post("/{node_id}/enable", response_model=NodeResponse)
async def enable_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-enable a disabled node (admin only)."""
    _require_admin(current_user)
    result = await db.execute(select(StorageNode).where(StorageNode.node_id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.status = "UNKNOWN"  # Health monitor will update to ONLINE/OFFLINE
    await db.commit()
    await db.refresh(node)
    return node
