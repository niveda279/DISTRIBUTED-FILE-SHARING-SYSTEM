"""
DFS Master Server – FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.models import audit_log, file, file_location, file_permission, storage_node, user  # noqa: F401 – ensure tables are registered
from app.routers import admin, auth, files, nodes, sharing
from app.services.health_monitor import start_health_monitor, stop_health_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


async def _seed_storage_nodes(conn):
    """Ensure the three storage nodes are registered in the DB."""
    from sqlalchemy import text
    nodes = [
        {"node_id": "node1", "name": "Storage Node 1", "host": "node1", "port": 8001},
        {"node_id": "node2", "name": "Storage Node 2", "host": "node2", "port": 8002},
        {"node_id": "node3", "name": "Storage Node 3", "host": "node3", "port": 8003},
    ]
    for n in nodes:
        await conn.execute(
            text(
                """
                INSERT INTO storage_nodes (node_id, name, host, port, status)
                VALUES (:node_id, :name, :host, :port, 'UNKNOWN')
                ON CONFLICT (node_id) DO NOTHING
                """
            ),
            n,
        )



@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────
    logger.info("Creating database tables …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _seed_storage_nodes(conn)

    logger.info("Starting health monitor …")
    start_health_monitor()

    logger.info("DFS Master Server ready ✓")
    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("Stopping health monitor …")
    stop_health_monitor()
    await engine.dispose()
    logger.info("DFS Master Server shut down ✓")


# ─────────────────────── App ──────────────────────────────────
app = FastAPI(
    title="Distributed File Sharing System – Master API",
    version="1.0.0",
    description="Fault-tolerant distributed file sharing with replication and SHA-256 integrity.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────── Routers ──────────────────────────────
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(sharing.router)
app.include_router(nodes.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "service": "DFS Master Server",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
