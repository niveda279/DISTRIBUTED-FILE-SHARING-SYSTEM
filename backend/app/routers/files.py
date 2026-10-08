"""Files router – upload, list, download, delete, search with dedup + versioning."""
import re
import uuid
from datetime import datetime, timezone
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
from app.models.file_version import FileVersion
from app.models.storage_node import StorageNode
from app.models.user import User
from app.schemas.file import FileResponse, FileLocationResponse
from app.security.jwt import get_current_user
from app.services import storage_client
from app.services.audit import log_event
from app.services.deduplication import find_existing_by_checksum, create_dedup_reference
from app.services.integrity import compute_sha256, verify_integrity
from app.services.node_selector import select_primary_node, select_replica_nodes
from app.services.placement_engine import get_placement_scores
from app.services.replication import create_replicas
from app.services.versioning import find_current_version, supersede_current_version

settings = get_settings()
router = APIRouter(prefix="/api/files", tags=["Files"])


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\s.\-]", "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:200]


def _build_response(file: FileModel, user: User) -> dict:
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
        "version_number": file.version_number,
        "is_current_version": file.is_current_version,
        "is_deduplicated": file.is_deduplicated,
        "access_count": file.access_count or 0,
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
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = compute_sha256(file_bytes)
    original_filename = file.filename or "upload"
    safe_name = _safe_filename(original_filename)

    # ── Deduplication Check ───────────────────────────────
    if settings.DEDUPLICATION_ENABLED:
        existing = await find_existing_by_checksum(db, checksum)
        if existing and existing.owner_id != current_user.id:
            # Another user's file has same bytes — create dedup reference
            dedup_file = await create_dedup_reference(
                db, existing, current_user.id, original_filename, file.content_type
            )
            # Check versioning for this user's filename
            current_ver = await find_current_version(db, current_user.id, original_filename)
            if current_ver:
                new_ver_num = await supersede_current_version(db, current_ver)
                dedup_file.version_number = new_ver_num
                dedup_file.parent_file_id = current_ver.id
            else:
                dedup_file.version_number = 1

            db.add(FileVersion(file_id=dedup_file.id, version_number=dedup_file.version_number,
                               created_by_id=current_user.id))
            await log_event(
                db, "UPLOAD",
                user_id=current_user.id,
                file_id=dedup_file.id,
                details=f"Deduplicated upload {original_filename} — reusing physical file from user {existing.owner_id}",
            )
            await db.commit()
            await db.refresh(dedup_file)
            return {
                "id": dedup_file.id,
                "filename": original_filename,
                "storage_id": dedup_file.filename,
                "size": dedup_file.size,
                "checksum": checksum,
                "primary_node": dedup_file.primary_node_id,
                "replica_nodes": [],
                "integrity": "verified",
                "deduplicated": True,
                "version": dedup_file.version_number,
            }

    # ── Versioning Check ──────────────────────────────────
    version_number = 1
    parent_file_id = None
    current_ver = await find_current_version(db, current_user.id, original_filename)
    if current_ver:
        version_number = await supersede_current_version(db, current_ver)
        parent_file_id = current_ver.id

    # ── Node Selection (intelligent placement) ────────────
    placement_scores = await get_placement_scores(db, len(file_bytes))
    primary_score = next(
        (s for s in placement_scores if s.health_score == 100.0 and s.storage_score > 0), None
    )
    if not primary_score:
        raise HTTPException(status_code=503, detail="No healthy storage nodes available")
    primary = primary_score.node

    # Store on primary
    storage_file_id = str(uuid.uuid4()).replace("-", "")
    try:
        await storage_client.store_file_on_node(primary.node_id, storage_file_id, file_bytes, safe_name)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Primary node storage failed: {e}")

    # Create file record
    db_file = FileModel(
        filename=storage_file_id,
        original_filename=original_filename,
        size=len(file_bytes),
        mime_type=file.content_type,
        owner_id=current_user.id,
        checksum=checksum,
        primary_node_id=primary.node_id,
        version_number=version_number,
        parent_file_id=parent_file_id,
        is_current_version=True,
    )
    db.add(db_file)
    await db.flush()

    # Primary location
    db.add(FileLocation(file_id=db_file.id, node_id=primary.node_id,
                        location_type="PRIMARY", status="ACTIVE"))
    primary.file_count = (primary.file_count or 0) + 1

    # Owner permission
    db.add(FilePermission(file_id=db_file.id, user_id=current_user.id, permission="OWNER"))

    # Version record
    db.add(FileVersion(file_id=db_file.id, version_number=version_number,
                       created_by_id=current_user.id))

    # Replicas
    replica_nodes = await select_replica_nodes(db, primary.node_id,
                                               count=settings.REPLICATION_FACTOR - 1,
                                               file_size=len(file_bytes))
    replica_ids = []
    if replica_nodes:
        replica_ids = await create_replicas(db, db_file.id, storage_file_id,
                                            file_bytes, safe_name, replica_nodes)

    # Emit system event
    from app.models.system_event import SystemEvent
    db.add(SystemEvent(
        event_type="FILE_UPLOADED",
        severity="INFO",
        node_id=primary.node_id,
        file_id=db_file.id,
        payload=f"File {original_filename} uploaded (v{version_number}), primary={primary.node_id}, replicas={replica_ids}",
    ))

    await log_event(
        db, "UPLOAD",
        user_id=current_user.id,
        file_id=db_file.id,
        node_id=primary.node_id,
        details=(f"Uploaded {original_filename} v{version_number}, size={len(file_bytes)}, "
                 f"primary={primary.node_id}, replicas={replica_ids}, "
                 f"score={primary_score.final_score:.1f}"),
    )
    await db.commit()
    await db.refresh(db_file)

    # Build placement info for response
    placement_info = [s.to_dict() for s in placement_scores]

    return {
        "id": db_file.id,
        "filename": original_filename,
        "storage_id": storage_file_id,
        "size": db_file.size,
        "checksum": checksum,
        "primary_node": primary.node_id,
        "replica_nodes": replica_ids,
        "integrity": "verified",
        "deduplicated": False,
        "version": version_number,
        "placement_scores": placement_info,
    }


@router.get("")
async def list_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all current-version files owned by or shared with the current user."""
    owned_q = (
        select(FileModel)
        .options(selectinload(FileModel.owner), selectinload(FileModel.locations),
                 selectinload(FileModel.permissions))
        .where(FileModel.owner_id == current_user.id)
        .where(FileModel.is_current_version == True)  # noqa: E712
    )
    owned_result = await db.execute(owned_q)
    owned_files = owned_result.scalars().all()

    shared_q = (
        select(FileModel)
        .join(FilePermission, FilePermission.file_id == FileModel.id)
        .options(selectinload(FileModel.owner), selectinload(FileModel.locations),
                 selectinload(FileModel.permissions))
        .where(FilePermission.user_id == current_user.id)
        .where(FileModel.owner_id != current_user.id)
        .where(FileModel.is_current_version == True)  # noqa: E712
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
    shared_q = (
        select(FileModel)
        .join(FilePermission, FilePermission.file_id == FileModel.id)
        .options(selectinload(FileModel.owner), selectinload(FileModel.locations),
                 selectinload(FileModel.permissions))
        .where(FilePermission.user_id == current_user.id)
        .where(FileModel.owner_id != current_user.id)
        .where(FileModel.is_current_version == True)  # noqa: E712
    )
    result = await db.execute(shared_q)
    return [_build_response(f, current_user) for f in result.scalars().all()]


@router.get("/search")
async def search_files(
    q: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    size_min: Optional[int] = Query(None),
    size_max: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    node_id: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),  # newest|oldest|largest|smallest|accessed
    integrity_ok: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extended file search with size, sort, node, and integrity filters."""
    accessible_ids_q = select(FilePermission.file_id).where(FilePermission.user_id == current_user.id)
    accessible_result = await db.execute(accessible_ids_q)
    accessible_ids = [row[0] for row in accessible_result.all()]

    query = (
        select(FileModel)
        .options(selectinload(FileModel.owner), selectinload(FileModel.locations),
                 selectinload(FileModel.permissions))
        .where(or_(FileModel.owner_id == current_user.id, FileModel.id.in_(accessible_ids)))
        .where(FileModel.is_current_version == True)  # noqa: E712
    )

    if q:
        query = query.where(FileModel.original_filename.ilike(f"%{q}%"))
    if file_type:
        query = query.where(FileModel.mime_type.ilike(f"%{file_type}%"))
    if size_min is not None:
        query = query.where(FileModel.size >= size_min)
    if size_max is not None:
        query = query.where(FileModel.size <= size_max)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(FileModel.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(FileModel.created_at <= dt)
        except ValueError:
            pass

    # Sort
    sort_map = {
        "newest": FileModel.created_at.desc(),
        "oldest": FileModel.created_at.asc(),
        "largest": FileModel.size.desc(),
        "smallest": FileModel.size.asc(),
        "accessed": FileModel.access_count.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, FileModel.created_at.desc()))

    result = await db.execute(query)
    files = result.scalars().all()

    # Post-filter: node_id
    if node_id:
        files = [f for f in files if any(loc.node_id == node_id for loc in (f.locations or []))]

    return [_build_response(f, current_user) for f in files]


@router.get("/{file_id}")
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileModel)
        .options(selectinload(FileModel.owner), selectinload(FileModel.locations),
                 selectinload(FileModel.permissions))
        .where(FileModel.id == file_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current_user.id:
        perm_result = await db.execute(
            select(FilePermission).where(FilePermission.file_id == file_id,
                                         FilePermission.user_id == current_user.id)
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
        .options(selectinload(FileModel.locations), selectinload(FileModel.permissions))
        .where(FileModel.id == file_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
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

    active_locs = [loc for loc in f.locations if loc.status == "ACTIVE"]
    if not active_locs:
        raise HTTPException(status_code=503, detail="No available file copies")

    primary_locs = [l for l in active_locs if l.location_type == "PRIMARY"]
    replica_locs = [l for l in active_locs if l.location_type == "REPLICA"]
    ordered = primary_locs + replica_locs

    file_bytes = None
    served_from = None
    failover = False
    for i, loc in enumerate(ordered):
        node_result = await db.execute(select(StorageNode).where(StorageNode.node_id == loc.node_id))
        node = node_result.scalar_one_or_none()
        if not node or node.status not in ("ONLINE",):
            continue
        try:
            file_bytes = await storage_client.retrieve_file_from_node(loc.node_id, f.filename)
            served_from = loc.node_id
            if i > 0:
                failover = True
            break
        except Exception:
            continue

    if file_bytes is None:
        raise HTTPException(status_code=503, detail="All storage nodes holding this file are unavailable")

    if not verify_integrity(file_bytes, f.checksum):
        await log_event(db, "INTEGRITY_FAILURE", user_id=current_user.id, file_id=file_id,
                        node_id=served_from, details="SHA-256 mismatch on download")
        from app.models.system_event import SystemEvent
        db.add(SystemEvent(event_type="INTEGRITY_FAILURE", severity="CRITICAL",
                           node_id=served_from, file_id=file_id,
                           payload=f"SHA-256 mismatch on file {file_id}"))
        await db.commit()
        raise HTTPException(status_code=500, detail="File integrity check failed")

    # Update access tracking
    f.access_count = (f.access_count or 0) + 1
    f.last_accessed_at = datetime.now(timezone.utc)

    event_type = "FILE_FAILOVER" if failover else "FILE_DOWNLOAD"
    from app.models.system_event import SystemEvent
    db.add(SystemEvent(
        event_type=event_type,
        severity="WARNING" if failover else "INFO",
        node_id=served_from,
        file_id=file_id,
        payload=f"{'Failover ' if failover else ''}Download of {f.original_filename} from {served_from}",
    ))

    await log_event(db, "DOWNLOAD", user_id=current_user.id, file_id=file_id,
                    node_id=served_from,
                    details=f"Downloaded from {served_from}" + (" (FAILOVER)" if failover else ""))
    await db.commit()

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=f.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{f.original_filename}"',
            "X-Served-From": served_from,
            "X-Checksum": f.checksum,
            "X-Failover": str(failover).lower(),
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
    if f.owner_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only the owner or admin can delete this file")

    # Only delete physical bytes if this is not a dedup reference and no other file uses same physical ID
    if not f.is_deduplicated:
        # Check if any other file references the same physical filename
        ref_count_result = await db.execute(
            select(func.count(FileModel.id))
            .where(FileModel.filename == f.filename)
            .where(FileModel.id != f.id)
        )
        ref_count = ref_count_result.scalar_one()

        if ref_count == 0:
            deletion_errors = []
            for loc in f.locations:
                try:
                    await storage_client.delete_file_from_node(loc.node_id, f.filename)
                except Exception as e:
                    deletion_errors.append(f"{loc.node_id}: {e}")
        else:
            deletion_errors = []  # keeping physical file for other references
    else:
        deletion_errors = []  # dedup reference — don't touch physical

    await log_event(db, "DELETE", user_id=current_user.id, file_id=file_id,
                    details=f"Deleted {f.original_filename}")
    await db.delete(f)
    await db.commit()
    return {"message": "File deleted", "warnings": deletion_errors}
