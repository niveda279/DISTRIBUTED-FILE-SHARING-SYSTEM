"""
Storage Node Server – shared FastAPI application.
Each node runs this same code, configured by environment variables.
"""
import hashlib
import os
import shutil
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

load_dotenv()

# ──────────────────────── Config ────────────────────────────
NODE_ID   = os.getenv("NODE_ID",   "node1")
NODE_NAME = os.getenv("NODE_NAME", "Storage Node 1")
HOST      = os.getenv("HOST",      "0.0.0.0")
PORT      = int(os.getenv("PORT",  "8001"))

# Storage root: each node stores files in /app/<NODE_ID>/files/
# This ensures isolation between nodes even if they share the same image.
_app_root    = Path("/app")
BASE_DIR     = _app_root / NODE_ID
STORAGE_DIR  = BASE_DIR / "files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Track whether this node is administratively disabled
DISABLED_FLAG = BASE_DIR / ".disabled"


# ──────────────────────── Helpers ───────────────────────────
def is_disabled() -> bool:
    return DISABLED_FLAG.exists()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_storage_info():
    total, used, free = shutil.disk_usage(str(STORAGE_DIR))
    file_count = len(list(STORAGE_DIR.iterdir()))
    return {
        "total_storage":     total,
        "available_storage": free,
        "used_storage":      used,
        "file_count":        file_count,
    }


# ──────────────────────── Lifespan ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{NODE_ID}] Storage node starting on port {PORT}")
    print(f"[{NODE_ID}] Storage directory: {STORAGE_DIR}")
    yield
    print(f"[{NODE_ID}] Storage node shutting down")


# ──────────────────────── App ───────────────────────────────
app = FastAPI(
    title=f"DFS Storage Node – {NODE_NAME}",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────── Routes ────────────────────────────

@app.get("/health")
async def health_check():
    """Node health endpoint polled by the master server."""
    if is_disabled():
        raise HTTPException(status_code=503, detail="Node is administratively disabled")

    info = get_storage_info()
    return {
        "node_id":           NODE_ID,
        "node_name":         NODE_NAME,
        "status":            "healthy",
        "available_storage": info["available_storage"],
        "total_storage":     info["total_storage"],
        "used_storage":      info["used_storage"],
        "file_count":        info["file_count"],
        "timestamp":         datetime.now(timezone.utc).isoformat(),
    }


@app.post("/store")
async def store_file(
    file_id: str,
    file: UploadFile = File(...),
):
    """Receive a file from the master server and persist it."""
    if is_disabled():
        raise HTTPException(status_code=503, detail="Node is administratively disabled")

    safe_id = "".join(c for c in file_id if c.isalnum() or c in "-_")
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid file_id")

    dest_path = STORAGE_DIR / safe_id

    # Stream to disk
    h = hashlib.sha256()
    async with aiofiles.open(dest_path, "wb") as out:
        while chunk := await file.read(65536):
            h.update(chunk)
            await out.write(chunk)

    checksum = h.hexdigest()
    size = dest_path.stat().st_size

    return {
        "node_id":   NODE_ID,
        "file_id":   safe_id,
        "checksum":  checksum,
        "size":      size,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/files/{file_id}")
async def retrieve_file(file_id: str):
    """Stream a stored file back to the master server."""
    if is_disabled():
        raise HTTPException(status_code=503, detail="Node is administratively disabled")

    safe_id = "".join(c for c in file_id if c.isalnum() or c in "-_")
    file_path = STORAGE_DIR / safe_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {file_id} not found on {NODE_ID}")

    def iterfile():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(iterfile(), media_type="application/octet-stream")


@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a stored file."""
    safe_id = "".join(c for c in file_id if c.isalnum() or c in "-_")
    file_path = STORAGE_DIR / safe_id

    if not file_path.exists():
        # Idempotent – not an error if already gone
        return {"message": f"File {file_id} not present on {NODE_ID} (already deleted)"}

    file_path.unlink()
    return {
        "node_id":    NODE_ID,
        "file_id":    safe_id,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/checksum/{file_id}")
async def get_checksum(file_id: str):
    """Return SHA-256 checksum of a stored file (for integrity verification)."""
    if is_disabled():
        raise HTTPException(status_code=503, detail="Node is administratively disabled")

    safe_id = "".join(c for c in file_id if c.isalnum() or c in "-_")
    file_path = STORAGE_DIR / safe_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {file_id} not found on {NODE_ID}")

    checksum = sha256_file(file_path)
    return {"node_id": NODE_ID, "file_id": safe_id, "checksum": checksum}


@app.get("/")
async def root():
    return {"node_id": NODE_ID, "name": NODE_NAME, "status": "running"}
