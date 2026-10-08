"""
Intelligent Node Placement Engine.

Calculates a composite placement score for each storage node based on:
  - Storage availability (how much free space is there)
  - Current utilization (used/total ratio)
  - File count (how many files it already holds)
  - Node health (ONLINE vs anything else)
  - Recent response latency
  - Historical failure rate
  - File size being uploaded (affects storage score)
  - Simulated load (from chaos simulation)

Score range: 0 (worst) → 100 (best).
Higher score = better candidate for placement.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_node import StorageNode
from app.models.simulation_state import SimulationState

logger = logging.getLogger(__name__)

MAX_LATENCY_MS = 2000.0   # latency above this scores 0
MAX_FILES_REF  = 10000    # normaliser for file count score
GB = 1024 ** 3


@dataclass
class NodeScore:
    node: StorageNode
    storage_score: float    # 0–100
    load_score: float       # 0–100
    health_score: float     # 0 or 100
    latency_score: float    # 0–100
    failure_score: float    # 0–100
    final_score: float      # weighted composite 0–100

    def to_dict(self) -> dict:
        return {
            "node_id": self.node.node_id,
            "node_name": self.node.name,
            "status": self.node.status,
            "storage_score": round(self.storage_score, 1),
            "load_score": round(self.load_score, 1),
            "health_score": round(self.health_score, 1),
            "latency_score": round(self.latency_score, 1),
            "failure_score": round(self.failure_score, 1),
            "final_score": round(self.final_score, 1),
            "avg_latency_ms": round(self.node.avg_latency_ms or 0, 1),
            "failure_count": self.node.failure_count or 0,
            "available_storage": self.node.available_storage or 0,
            "total_storage": self.node.total_storage or 0,
            "file_count": self.node.file_count or 0,
        }


# Weights (must sum to 1.0)
WEIGHTS = {
    "storage": 0.30,
    "load": 0.25,
    "health": 0.20,
    "latency": 0.15,
    "failure": 0.10,
}


def _storage_score(node: StorageNode, file_size: int = 0) -> float:
    """Score based on available storage after accommodating the file."""
    total = node.total_storage or 1
    available = max(0, (node.available_storage or 0) - file_size)
    if available <= 0:
        return 0.0
    ratio = available / total
    return min(100.0, ratio * 100.0)


def _load_score(node: StorageNode, sim: Optional[SimulationState] = None) -> float:
    """Score based on inverse utilisation. Lower utilisation = higher score."""
    total = node.total_storage or 1
    used = total - max(0, node.available_storage or 0)
    util_ratio = used / total

    # Apply simulated load penalty
    sim_load = 0
    if sim and sim.is_simulated and sim.simulated_load_pct:
        sim_load = sim.simulated_load_pct / 100.0

    effective_util = min(1.0, util_ratio + sim_load * 0.5)
    return max(0.0, (1.0 - effective_util) * 100.0)


def _health_score(node: StorageNode, sim: Optional[SimulationState] = None) -> float:
    """Binary: 100 if ONLINE and not simulated-offline, else 0."""
    if sim and sim.is_simulated and sim.simulated_status == "OFFLINE":
        return 0.0
    return 100.0 if node.status == "ONLINE" else 0.0


def _latency_score(node: StorageNode, sim: Optional[SimulationState] = None) -> float:
    """Inverse latency score. Lower latency = higher score."""
    latency = node.avg_latency_ms or 0
    # Add simulated latency
    if sim and sim.is_simulated and sim.simulated_latency_ms:
        latency += sim.simulated_latency_ms
    if latency <= 0:
        return 100.0
    return max(0.0, (1.0 - min(latency, MAX_LATENCY_MS) / MAX_LATENCY_MS) * 100.0)


def _failure_score(node: StorageNode) -> float:
    """Penalise nodes with high historical failure counts."""
    failures = node.failure_count or 0
    # Every 5 failures costs 10 points, capped at 0
    return max(0.0, 100.0 - (failures / 5.0) * 10.0)


def compute_node_score(
    node: StorageNode,
    sim: Optional[SimulationState] = None,
    file_size: int = 0,
) -> NodeScore:
    s = _storage_score(node, file_size)
    l = _load_score(node, sim)
    h = _health_score(node, sim)
    la = _latency_score(node, sim)
    f = _failure_score(node)
    final = (
        WEIGHTS["storage"] * s
        + WEIGHTS["load"] * l
        + WEIGHTS["health"] * h
        + WEIGHTS["latency"] * la
        + WEIGHTS["failure"] * f
    )
    return NodeScore(
        node=node,
        storage_score=s,
        load_score=l,
        health_score=h,
        latency_score=la,
        failure_score=f,
        final_score=final,
    )


async def get_placement_scores(
    db: AsyncSession,
    file_size: int = 0,
) -> List[NodeScore]:
    """Return placement scores for all nodes, sorted best-first."""
    nodes_result = await db.execute(select(StorageNode))
    nodes = list(nodes_result.scalars().all())

    sims_result = await db.execute(select(SimulationState))
    sim_map = {s.node_id: s for s in sims_result.scalars().all()}

    scores = []
    for node in nodes:
        sim = sim_map.get(node.node_id)
        score = compute_node_score(node, sim, file_size)
        scores.append(score)

    scores.sort(key=lambda x: x.final_score, reverse=True)
    return scores


async def select_primary_with_score(
    db: AsyncSession, file_size: int = 0
) -> Optional[NodeScore]:
    """Select the best node for primary placement."""
    scores = await get_placement_scores(db, file_size)
    eligible = [s for s in scores if s.health_score == 100.0 and s.storage_score > 0]
    return eligible[0] if eligible else None


async def select_replica_with_score(
    db: AsyncSession,
    exclude_node_id: str,
    file_size: int = 0,
    count: int = 1,
) -> List[NodeScore]:
    """Select best replica nodes excluding the primary."""
    scores = await get_placement_scores(db, file_size)
    eligible = [
        s for s in scores
        if s.node.node_id != exclude_node_id
        and s.health_score == 100.0
        and s.storage_score > 0
    ]
    return eligible[:count]
