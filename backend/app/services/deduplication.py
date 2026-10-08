"""
Deduplication Service.

Uses the SHA-256 checksum already computed on upload to detect
identical file content. If a duplicate is found, instead of uploading
bytes to a storage node again, a lightweight metadata reference is
created pointing at the same physical file.

Ownership is always preserved — User A's dedup record is independent
of User B's. Deletion of one never affects the other.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.models.file_location import FileLocation
from app.models.file_permission import FilePermission

logger = logging.getLogger(__name__)


async def find_existing_by_checksum(
    db: AsyncSession, checksum: str
) -> Optional[File]:
    """
    Return an existing file with the same SHA-256 checksum that has
    at least one ACTIVE location (i.e. its bytes are still on a node).
    Returns None if no suitable original exists.
    """
    result = await db.execute(
        select(File)
        .where(File.checksum == checksum)
        .where(File.is_deduplicated == False)  # noqa: E712 — only originals
        .where(File.is_current_version == True)  # noqa: E712
        .limit(1)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        return None

    # Verify it has at least one ACTIVE location
    loc_result = await db.execute(
        select(FileLocation)
        .where(FileLocation.file_id == candidate.id)
        .where(FileLocation.status == "ACTIVE")
        .limit(1)
    )
    if loc_result.scalar_one_or_none() is None:
        return None

    return candidate


async def create_dedup_reference(
    db: AsyncSession,
    original: File,
    new_owner_id: int,
    original_filename: str,
    mime_type: Optional[str],
) -> File:
    """
    Create a deduplicated File record that shares physical storage
    with `original` but belongs to `new_owner_id`.

    Physical file on storage nodes is NOT re-uploaded.
    Locations are copied as virtual references.
    """
    dedup_file = File(
        filename=original.filename,              # same physical ID on nodes
        original_filename=original_filename,
        size=original.size,
        mime_type=mime_type or original.mime_type,
        owner_id=new_owner_id,
        checksum=original.checksum,
        primary_node_id=original.primary_node_id,
        version_number=1,
        is_current_version=True,
        is_deduplicated=True,
        dedup_source_file_id=original.id,
    )
    db.add(dedup_file)
    await db.flush()

    # Copy active location records (virtual — no bytes moved)
    orig_locs_result = await db.execute(
        select(FileLocation)
        .where(FileLocation.file_id == original.id)
        .where(FileLocation.status == "ACTIVE")
    )
    orig_locs = orig_locs_result.scalars().all()

    for loc in orig_locs:
        new_loc = FileLocation(
            file_id=dedup_file.id,
            node_id=loc.node_id,
            location_type=loc.location_type,
            status="ACTIVE",
        )
        db.add(new_loc)

    # Owner permission
    perm = FilePermission(
        file_id=dedup_file.id,
        user_id=new_owner_id,
        permission="OWNER",
    )
    db.add(perm)

    logger.info(
        f"Dedup: new file record {dedup_file.id} for owner {new_owner_id} "
        f"references physical file {original.filename}"
    )
    return dedup_file


async def get_dedup_savings(db: AsyncSession) -> dict:
    """
    Calculate storage savings from deduplication.
    Returns original_bytes_required, actual_bytes_stored, bytes_saved.
    """
    # Sum of all file sizes (what storage WOULD be if naive)
    from sqlalchemy import func
    total_result = await db.execute(
        select(func.coalesce(func.sum(File.size), 0))
        .where(File.is_current_version == True)  # noqa: E712
    )
    total_logical = total_result.scalar_one()

    # Sum only non-deduplicated files (actual physical copies)
    physical_result = await db.execute(
        select(func.coalesce(func.sum(File.size), 0))
        .where(File.is_deduplicated == False)  # noqa: E712
        .where(File.is_current_version == True)  # noqa: E712
    )
    actual_physical = physical_result.scalar_one()

    # Count deduplicated files
    dedup_count_result = await db.execute(
        select(func.count(File.id))
        .where(File.is_deduplicated == True)  # noqa: E712
    )
    dedup_count = dedup_count_result.scalar_one()

    return {
        "total_logical_bytes": int(total_logical),
        "actual_physical_bytes": int(actual_physical),
        "bytes_saved": max(0, int(total_logical) - int(actual_physical)),
        "deduplicated_file_count": int(dedup_count),
    }
