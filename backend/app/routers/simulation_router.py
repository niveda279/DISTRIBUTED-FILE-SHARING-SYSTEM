"""Admin Chaos Simulation router."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security.jwt import get_current_user
from app.services import simulation as sim_svc

router = APIRouter(prefix="/api/admin/simulation", tags=["Simulation"])


def _require_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/status")
async def simulation_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    return await sim_svc.get_simulation_status(db)


@router.post("/node-failure/{node_id}")
async def simulate_failure(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        result = await sim_svc.simulate_node_failure(db, node_id, current_user.id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/node-recovery/{node_id}")
async def simulate_recovery(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    try:
        result = await sim_svc.simulate_node_recovery(db, node_id, current_user.id)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/network-delay/{node_id}")
async def simulate_delay(
    node_id: str,
    latency_ms: int = Body(500, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await sim_svc.simulate_network_delay(db, node_id, latency_ms, current_user.id)
    await db.commit()
    return result


@router.post("/high-load/{node_id}")
async def simulate_high_load(
    node_id: str,
    load_pct: int = Body(80, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await sim_svc.simulate_high_load(db, node_id, load_pct, current_user.id)
    await db.commit()
    return result


@router.post("/storage-warning/{node_id}")
async def simulate_storage_warn(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await sim_svc.simulate_storage_warning(db, node_id, current_user.id)
    await db.commit()
    return result


@router.post("/clear/{node_id}")
async def clear_simulation(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = await sim_svc.clear_simulation(db, node_id, current_user.id)
    await db.commit()
    return result


@router.post("/clear-all")
async def clear_all_simulations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear simulations for all nodes at once."""
    from sqlalchemy import select
    from app.models.simulation_state import SimulationState
    _require_admin(current_user)
    result = await db.execute(select(SimulationState))
    sims = result.scalars().all()
    cleared = 0
    for sim in sims:
        if sim.is_simulated:
            await sim_svc.clear_simulation(db, sim.node_id, current_user.id)
            cleared += 1
    await db.commit()
    return {"message": f"Cleared {cleared} simulation(s)", "cleared": cleared}

