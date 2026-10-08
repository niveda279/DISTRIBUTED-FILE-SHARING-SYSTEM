"""
Chaos Simulation Service.

Provides safe admin-controlled simulation of distributed failure scenarios.
Manipulates simulation_state table and storage_node.status — does NOT
delete actual file data.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation_state import SimulationState
from app.models.storage_node import StorageNode
from app.models.system_event import SystemEvent

logger = logging.getLogger(__name__)


async def _get_or_create_sim(db: AsyncSession, node_id: str) -> SimulationState:
    result = await db.execute(
        select(SimulationState).where(SimulationState.node_id == node_id)
    )
    sim = result.scalar_one_or_none()
    if not sim:
        sim = SimulationState(node_id=node_id, is_simulated=False)
        db.add(sim)
        await db.flush()
    return sim


async def _emit(db: AsyncSession, event_type: str, payload: str, node_id: str,
                severity: str = "WARNING"):
    db.add(SystemEvent(event_type=event_type, severity=severity,
                       node_id=node_id, payload=payload))


async def simulate_node_failure(
    db: AsyncSession, node_id: str, admin_id: int
) -> dict:
    """Mark a node as simulated-offline. Does NOT delete files."""
    node_result = await db.execute(
        select(StorageNode).where(StorageNode.node_id == node_id)
    )
    node = node_result.scalar_one_or_none()
    if not node:
        raise ValueError(f"Node {node_id} not found")

    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = True
    sim.simulated_status = "OFFLINE"
    sim.activated_at = datetime.now(timezone.utc)
    sim.activated_by_id = admin_id

    node.status = "OFFLINE"
    node.failure_count = (node.failure_count or 0) + 1

    await _emit(db, "SIM_NODE_FAILURE",
                f"[SIMULATION] {node_id} forced OFFLINE by admin {admin_id}",
                node_id=node_id, severity="ERROR")

    logger.info(f"SIMULATION: Node {node_id} forced OFFLINE by admin {admin_id}")
    return {
        "action": "node_failure",
        "node_id": node_id,
        "status": "OFFLINE",
        "simulated": True,
    }


async def simulate_node_recovery(
    db: AsyncSession, node_id: str, admin_id: int
) -> dict:
    """Restore a simulated-offline node to UNKNOWN (health monitor will set ONLINE)."""
    node_result = await db.execute(
        select(StorageNode).where(StorageNode.node_id == node_id)
    )
    node = node_result.scalar_one_or_none()
    if not node:
        raise ValueError(f"Node {node_id} not found")

    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = False
    sim.simulated_status = None
    sim.simulated_latency_ms = 0
    sim.simulated_load_pct = 0
    sim.simulated_storage_warning = False

    # Let health monitor restore it
    if node.status == "OFFLINE":
        node.status = "UNKNOWN"

    await _emit(db, "SIM_NODE_RECOVERY",
                f"[SIMULATION] {node_id} recovered by admin {admin_id}",
                node_id=node_id, severity="INFO")

    logger.info(f"SIMULATION: Node {node_id} recovery by admin {admin_id}")
    return {
        "action": "node_recovery",
        "node_id": node_id,
        "status": "UNKNOWN",
        "simulated": False,
    }


async def simulate_network_delay(
    db: AsyncSession, node_id: str, latency_ms: int, admin_id: int
) -> dict:
    """Simulate network latency for a node to degrade placement score."""
    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = True
    sim.simulated_latency_ms = latency_ms
    sim.activated_at = datetime.now(timezone.utc)
    sim.activated_by_id = admin_id

    await _emit(db, "SIM_NETWORK_DELAY",
                f"[SIMULATION] {node_id} simulated latency={latency_ms}ms",
                node_id=node_id)

    return {
        "action": "network_delay",
        "node_id": node_id,
        "simulated_latency_ms": latency_ms,
    }


async def simulate_high_load(
    db: AsyncSession, node_id: str, load_pct: int, admin_id: int
) -> dict:
    """Simulate high node load (affects placement score)."""
    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = True
    sim.simulated_load_pct = min(100, max(0, load_pct))
    sim.activated_at = datetime.now(timezone.utc)
    sim.activated_by_id = admin_id

    await _emit(db, "SIM_HIGH_LOAD",
                f"[SIMULATION] {node_id} simulated load={load_pct}%",
                node_id=node_id)

    return {
        "action": "high_load",
        "node_id": node_id,
        "simulated_load_pct": load_pct,
    }


async def simulate_storage_warning(
    db: AsyncSession, node_id: str, admin_id: int
) -> dict:
    """Simulate a storage capacity warning for a node."""
    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = True
    sim.simulated_storage_warning = True
    sim.activated_at = datetime.now(timezone.utc)
    sim.activated_by_id = admin_id

    await _emit(db, "SIM_STORAGE_WARNING",
                f"[SIMULATION] {node_id} storage capacity warning",
                node_id=node_id, severity="WARNING")

    return {
        "action": "storage_warning",
        "node_id": node_id,
        "storage_warning": True,
    }


async def clear_simulation(
    db: AsyncSession, node_id: str, admin_id: int
) -> dict:
    """Clear all simulations for a node."""
    sim = await _get_or_create_sim(db, node_id)
    sim.is_simulated = False
    sim.simulated_status = None
    sim.simulated_latency_ms = 0
    sim.simulated_load_pct = 0
    sim.simulated_storage_warning = False

    node_result = await db.execute(
        select(StorageNode).where(StorageNode.node_id == node_id)
    )
    node = node_result.scalar_one_or_none()
    if node and node.status == "OFFLINE":
        node.status = "UNKNOWN"

    await _emit(db, "SIM_CLEARED",
                f"[SIMULATION] All simulations cleared for {node_id} by admin {admin_id}",
                node_id=node_id, severity="INFO")

    return {"action": "cleared", "node_id": node_id}


async def get_simulation_status(db: AsyncSession) -> list:
    """Return current simulation state for all nodes."""
    result = await db.execute(select(SimulationState))
    sims = result.scalars().all()
    return [
        {
            "node_id": s.node_id,
            "is_simulated": s.is_simulated,
            "simulated_status": s.simulated_status,
            "simulated_latency_ms": s.simulated_latency_ms,
            "simulated_load_pct": s.simulated_load_pct,
            "simulated_storage_warning": s.simulated_storage_warning,
            "activated_at": s.activated_at.isoformat() if s.activated_at else None,
        }
        for s in sims
    ]
