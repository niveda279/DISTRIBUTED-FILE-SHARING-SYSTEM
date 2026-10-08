"""
File Versioning Service.

When a user uploads a file with the same original_filename they previously
uploaded, this service:
  1. Marks the existing record as is_current_version=False
  2. Creates a new File record with version_number incremented
  3. Records both in file_versions history table

Existing files (pre-migration) default to version_number=1, is_current_version=True.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.models.file_version import FileVersion

logger = logging.getLogger(__name__)


async def find_current_version(
    db: AsyncSession,
    owner_id: int,
    original_filename: str,
) -> Optional[File]:
    """
    Return the current version of a file with the given name owned by owner_id.
    Returns None if no such file exists.
    """
    result = await db.execute(
        select(File)
        .where(File.owner_id == owner_id)
        .where(File.original_filename == original_filename)
        .where(File.is_current_version == True)  # noqa: E712
        .order_by(File.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_all_versions(db: AsyncSession, file_id: int) -> list:
    """
    Return all version records for a file lineage.
    Given any file_id (any version), trace to the root and return all versions.
    """
    # First get the root file (follow parent_file_id chain)
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        return []

    # Walk up to root
    root = f
    while root.parent_file_id:
        parent_result = await db.execute(
            select(File).where(File.id == root.parent_file_id)
        )
        parent = parent_result.scalar_one_or_none()
        if parent:
            root = parent
        else:
            break

    # Now walk DOWN: find all files in this lineage by owner + original_filename
    all_result = await db.execute(
        select(File)
        .where(File.owner_id == root.owner_id)
        .where(File.original_filename == root.original_filename)
        .order_by(File.version_number.asc())
    )
    return list(all_result.scalars().all())


async def supersede_current_version(
    db: AsyncSession,
    current_file: File,
) -> int:
    """
    Mark the given file as no longer the current version.
    Returns the new version number to assign.
    """
    current_file.is_current_version = False
    new_version_number = (current_file.version_number or 1) + 1
    logger.info(
        f"Superseding file {current_file.id} (v{current_file.version_number}), "
        f"new version will be v{new_version_number}"
    )
    return new_version_number


async def restore_version(
    db: AsyncSession,
    target_version: File,
    current_version: File,
    requester_id: int,
) -> File:
    """
    Restore `target_version` as the current version.
    Creates a NEW file record as the restored version (so the history is preserved).
    """
    from app.models.file_location import FileLocation
    from app.models.file_permission import FilePermission

    new_version_number = (current_version.version_number or 1) + 1

    # Mark current as not-current
    current_version.is_current_version = False

    # Create restored copy
    restored = File(
        filename=target_version.filename,
        original_filename=target_version.original_filename,
        size=target_version.size,
        mime_type=target_version.mime_type,
        owner_id=current_version.owner_id,
        checksum=target_version.checksum,
        primary_node_id=target_version.primary_node_id,
        version_number=new_version_number,
        parent_file_id=current_version.id,
        is_current_version=True,
        is_deduplicated=True,  # shares physical bytes with target_version
        dedup_source_file_id=target_version.id,
    )
    db.add(restored)
    await db.flush()

    # Copy locations
    locs_result = await db.execute(
        select(FileLocation)
        .where(FileLocation.file_id == target_version.id)
        .where(FileLocation.status == "ACTIVE")
    )
    for loc in locs_result.scalars().all():
        db.add(FileLocation(
            file_id=restored.id,
            node_id=loc.node_id,
            location_type=loc.location_type,
            status="ACTIVE",
        ))

    # Owner permission
    db.add(FilePermission(
        file_id=restored.id,
        user_id=current_version.owner_id,
        permission="OWNER",
    ))

    # Record version history
    db.add(FileVersion(
        file_id=restored.id,
        version_number=new_version_number,
        created_by_id=requester_id,
    ))

    logger.info(
        f"Restored file {target_version.id} (v{target_version.version_number}) "
        f"as new v{new_version_number} (id={restored.id})"
    )
    return restored
