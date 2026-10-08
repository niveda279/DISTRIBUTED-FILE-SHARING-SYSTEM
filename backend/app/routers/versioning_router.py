"""File versioning router."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.file import File
from app.models.file_location import FileLocation
from app.models.file_permission import FilePermission
from app.models.storage_node import StorageNode
from app.models.user import User
from app.security.jwt import get_current_user
from app.services import storage_client
from app.services.audit import log_event
from app.services.versioning import get_all_versions, restore_version

router = APIRouter(prefix="/api/files", tags=["Versioning"])


def _check_access(file: File, user: User):
    if file.owner_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("/{file_id}/versions")
async def list_versions(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all versions in a file's lineage."""
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    _check_access(f, current_user)

    versions = await get_all_versions(db, file_id)
    response = []
    for v in versions:
        locs_result = await db.execute(
            select(FileLocation)
            .where(FileLocation.file_id == v.id)
            .where(FileLocation.status == "ACTIVE")
        )
        locs = locs_result.scalars().all()
        response.append({
            "id": v.id,
            "version_number": v.version_number,
            "original_filename": v.original_filename,
            "size": v.size,
            "checksum": v.checksum,
            "is_current_version": v.is_current_version,
            "is_deduplicated": v.is_deduplicated,
            "created_at": v.created_at.isoformat(),
            "locations": [{"node_id": l.node_id, "type": l.location_type} for l in locs],
        })
    return response


@router.get("/{file_id}/versions/{version_id}/download")
async def download_version(
    file_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a specific version of a file."""
    result = await db.execute(
        select(File)
        .options(selectinload(File.locations))
        .where(File.id == version_id)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")

    # Check access via original file
    original_result = await db.execute(select(File).where(File.id == file_id))
    original = original_result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="File not found")
    _check_access(original, current_user)

    # Try to download from active location
    active_locs = [loc for loc in v.locations if loc.status == "ACTIVE"]
    if not active_locs:
        raise HTTPException(status_code=503, detail="No active copies for this version")

    file_bytes = None
    served_from = None
    for loc in active_locs:
        node_result = await db.execute(
            select(StorageNode).where(StorageNode.node_id == loc.node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node or node.status != "ONLINE":
            continue
        try:
            file_bytes = await storage_client.retrieve_file_from_node(loc.node_id, v.filename)
            served_from = loc.node_id
            break
        except Exception:
            continue

    if file_bytes is None:
        raise HTTPException(status_code=503, detail="Cannot download this version")

    import io
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=v.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="v{v.version_number}_{v.original_filename}"',
            "X-Served-From": served_from or "",
            "X-Version": str(v.version_number),
        },
    )


@router.post("/{file_id}/restore/{version_id}")
async def restore_file_version(
    file_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore a previous version as the current version."""
    # Get the current version
    current_result = await db.execute(
        select(File)
        .options(selectinload(File.locations))
        .where(File.id == file_id)
    )
    current = current_result.scalar_one_or_none()
    if not current:
        raise HTTPException(status_code=404, detail="File not found")
    _check_access(current, current_user)

    # Get target version
    target_result = await db.execute(
        select(File)
        .options(selectinload(File.locations))
        .where(File.id == version_id)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target version not found")

    restored = await restore_version(db, target, current, current_user.id)
    await log_event(
        db, "VERSION_RESTORE",
        user_id=current_user.id,
        file_id=restored.id,
        details=f"Restored version {target.version_number} of {current.original_filename} as v{restored.version_number}",
    )
    await db.commit()
    return {
        "message": "Version restored",
        "new_file_id": restored.id,
        "restored_version": target.version_number,
        "new_version": restored.version_number,
    }
