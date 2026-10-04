"""Files router – upload, list, download, delete, search."""
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.file import File as FileModel
from app.models.file_location import FileLocation
from app.models.file_permission import FilePermission
from app.models.storage_node import StorageNode
from app.models.user import User
from app.schemas.file import FileResponse, FileLocationResponse
from app.security.jwt import get_current_user
from app.services import storage_client
from app.services.audit import log_event
from app.services.integrity import compute_sha256, verify_integrity
from app.services.node_selector import select_primary_node, select_replica_nodes
from app.services.replication import create_replicas

settings = get_settings()
router = APIRouter(prefix="/api/files", tags=["Files"])


def _safe_filename(name: str) -> str:
    """Strip unsafe characters from a filename."""
    name = re.sub(r"[^\w\s.\-]", "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:200]


def _build_response(file: FileModel, user: User) -> dict:
    """Construct a FileResponse-compatible dict."""
    # Determine permission
    perm = "OWNER" if file.owner_id == user.id else None
    for fp in (file.permissions or []):
        if fp.user_id == user.id:
            perm = fp.permission
            break

    return {
        "id": file.id,
        "filename": file.filename,
        "original_filename": file.original_filename,
        "size": file.size,
        "mime_type": file.mime_type,
        "owner_id": file.owner_id,
        "owner_name": file.owner.name if file.owner else "",
        "owner_email": file.owner.email if file.owner else "",
        "checksum": file.checksum,
        "primary_node_id": file.primary_node_id,
        "created_at": file.created_at,
        "updated_at": file.updated_at,
        "locations": [
            {"node_id": loc.node_id, "location_type": loc.location_type, "status": loc.status}
            for loc in (file.locations or [])
        ],
        "user_permission": perm,
    }


@router.post("/upload", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = compute_sha256(file_bytes)
    safe_name = _safe_filename(file.filename or "upload")
    storage_file_id = str(uuid.uuid4()).replace("-", "")

    # Select primary node
    primary = await select_primary_node(db)
    if not primary:
        raise HTTPException(status_code=503, detail="No healthy storage nodes available")

    # Store on primary
    try:
        await storage_client.store_file_on_node(
            primary.node_id, storage_file_id, file_bytes, safe_name
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Primary node storage failed: {e}")

    # Create file record
    db_file = FileModel(
        filename=storage_file_id,
        original_filename=file.filename or "upload",
        size=len(file_bytes),
        mime_type=file.content_type,
        owner_id=current_user.id,
        checksum=checksum,
        primary_node_id=primary.node_id,
    )
    db.add(db_file)
    await db.flush()

    # Primary location record
    primary_loc = FileLocation(
        file_id=db_file.id,
        node_id=primary.node_id,
        location_type="PRIMARY",
        status="ACTIVE",
    )
    db.add(primary_loc)
    primary.file_count = (primary.file_count or 0) + 1

    # Owner permission
    owner_perm = FilePermission(
        file_id=db_file.id,
        user_id=current_user.id,
        permission="OWNER",
    )
    db.add(owner_perm)

    # Select replica nodes
    replica_nodes = await select_replica_nodes(db, primary.node_id, count=1)
    replica_ids = []
    if replica_nodes:
        replica_ids = await create_replicas(
            db, db_file.id, storage_file_id, file_bytes, safe_name, replica_nodes
        )

    await log_event(
        db,
        "UPLOAD",
        user_id=current_user.id,
        file_id=db_file.id,
        node_id=primary.node_id,
        details=f"Uploaded {file.filename}, size={len(file_bytes)}, primary={primary.node_id}, replicas={replica_ids}",
    )
    await db.commit()
    await db.refresh(db_file)

    return {
        "id": db_file.id,
        "filename": db_file.original_filename,
        "storage_id": storage_file_id,
        "size": db_file.size,
        "checksum": checksum,
        "primary_node": primary.node_id,
        "replica_nodes": replica_ids,
        "integrity": "verified",
    }


@router.get("")
async def list_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all files owned by or shared with the current user."""
    # Owned files
    owned_q = (
        select(FileModel)
        .options(
            selectinload(FileModel.owner),
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(FileModel.owner_id == current_user.id)
    )
    owned_result = await db.execute(owned_q)
    owned_files = owned_result.scalars().all()

    # Shared files
    shared_q = (
        select(FileModel)
        .join(FilePermission, FilePermission.file_id == FileModel.id)
        .options(
            selectinload(FileModel.owner),
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(
            FilePermission.user_id == current_user.id,
            FileModel.owner_id != current_user.id,
        )
    )
    shared_result = await db.execute(shared_q)
    shared_files = shared_result.scalars().all()

    all_files = {f.id: f for f in list(owned_files) + list(shared_files)}
    return [_build_response(f, current_user) for f in all_files.values()]


@router.get("/shared")
async def list_shared_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all files shared with the current user."""
    shared_q = (
        select(FileModel)
        .join(FilePermission, FilePermission.file_id == FileModel.id)
        .options(
            selectinload(FileModel.owner),
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(
            FilePermission.user_id == current_user.id,
            FileModel.owner_id != current_user.id,
        )
    )
    result = await db.execute(shared_q)
    shared_files = result.scalars().all()

    return [_build_response(f, current_user) for f in shared_files]


@router.get("/search")
async def search_files(
    q: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search files accessible to the current user."""
    # Build accessible file set
    accessible_file_ids_q = (
        select(FilePermission.file_id)
        .where(FilePermission.user_id == current_user.id)
    )
    accessible_result = await db.execute(accessible_file_ids_q)
    accessible_ids = [row[0] for row in accessible_result.all()]

    query = (
        select(FileModel)
        .options(
            selectinload(FileModel.owner),
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(
            or_(
                FileModel.owner_id == current_user.id,
                FileModel.id.in_(accessible_ids),
            )
        )
    )

    if q:
        query = query.where(FileModel.original_filename.ilike(f"%{q}%"))
    if file_type:
        query = query.where(FileModel.mime_type.ilike(f"%{file_type}%"))

    result = await db.execute(query)
    files = result.scalars().all()
    return [_build_response(f, current_user) for f in files]


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileModel)
        .options(
            selectinload(FileModel.owner),
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(FileModel.id == file_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access
    if f.owner_id != current_user.id:
        perm_result = await db.execute(
            select(FilePermission).where(
                FilePermission.file_id == file_id,
                FilePermission.user_id == current_user.id,
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    return _build_response(f, current_user)


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileModel)
        .options(
            selectinload(FileModel.locations),
            selectinload(FileModel.permissions),
        )
        .where(FileModel.id == file_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Check access
    if f.owner_id != current_user.id:
        perm_result = await db.execute(
            select(FilePermission).where(
                FilePermission.file_id == file_id,
                FilePermission.user_id == current_user.id,
                FilePermission.permission.in_(["DOWNLOAD", "MANAGE", "OWNER"]),
            )
        )
        if not perm_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Download permission required")

    # Determine available locations (prefer primary)
    active_locs = [loc for loc in f.locations if loc.status == "ACTIVE"]
    if not active_locs:
        raise HTTPException(status_code=503, detail="No available file copies")

    # Try primary first, then replicas
    primary_locs = [l for l in active_locs if l.location_type == "PRIMARY"]
    replica_locs = [l for l in active_locs if l.location_type == "REPLICA"]
    ordered = primary_locs + replica_locs

    file_bytes = None
    served_from = None
    for loc in ordered:
        # Check if node is online
        node_result = await db.execute(
            select(StorageNode).where(StorageNode.node_id == loc.node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node or node.status not in ("ONLINE",):
            continue
        try:
            file_bytes = await storage_client.retrieve_file_from_node(loc.node_id, f.filename)
            served_from = loc.node_id
            break
        except Exception:
            continue

    if file_bytes is None:
        raise HTTPException(status_code=503, detail="All storage nodes holding this file are unavailable")

    # Integrity check
    if not verify_integrity(file_bytes, f.checksum):
        await log_event(
            db, "INTEGRITY_FAILURE", user_id=current_user.id, file_id=file_id, node_id=served_from,
            details="SHA-256 mismatch on download"
        )
        await db.commit()
        raise HTTPException(status_code=500, detail="File integrity check failed (SHA-256 mismatch)")

    await log_event(
        db, "DOWNLOAD", user_id=current_user.id, file_id=file_id, node_id=served_from,
        details=f"Downloaded from {served_from}"
    )
    await db.commit()

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=f.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{f.original_filename}"',
            "X-Served-From": served_from,
            "X-Checksum": f.checksum,
        },
    )


@router.delete("/{file_id}", status_code=200)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileModel)
        .options(selectinload(FileModel.locations))
        .where(FileModel.id == file_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Only owner or admin can delete
    if f.owner_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only the owner or admin can delete this file")

    # Delete from all nodes
    deletion_errors = []
    for loc in f.locations:
        try:
            await storage_client.delete_file_from_node(loc.node_id, f.filename)
        except Exception as e:
            deletion_errors.append(f"{loc.node_id}: {e}")

    await log_event(
        db, "DELETE", user_id=current_user.id, file_id=file_id,
        details=f"Deleted {f.original_filename}. Errors: {deletion_errors or 'none'}"
    )
    await db.delete(f)
    await db.commit()

    return {"message": "File deleted", "warnings": deletion_errors}
