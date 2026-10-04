"""File sharing / permissions router."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.file import File
from app.models.file_permission import FilePermission
from app.models.user import User
from app.schemas.file import PermissionCreate, PermissionResponse
from app.security.jwt import get_current_user
from app.services.audit import log_event

router = APIRouter(prefix="/api/files", tags=["Sharing"])


def _require_owner(file: File, user: User):
    if file.owner_id != user.id and user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not file owner")


@router.post("/{file_id}/share", response_model=PermissionResponse, status_code=201)
async def share_file(
    file_id: int,
    payload: PermissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant another user access to a file."""
    # Fetch file
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    _require_owner(file, current_user)

    # Resolve target user
    result = await db.execute(select(User).where(User.email == payload.shared_with_email.lower()))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.id == file.owner_id:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")

    # Check duplicate – model uses 'user_id'
    existing = await db.execute(
        select(FilePermission).where(
            FilePermission.file_id == file_id,
            FilePermission.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already shared with this user")

    perm = FilePermission(
        file_id=file_id,
        user_id=target_user.id,
        permission=payload.permission,
    )
    db.add(perm)
    await db.flush()
    await log_event(
        db,
        "SHARE",
        user_id=current_user.id,
        file_id=file_id,
        details=f"Shared file {file_id} with {target_user.email} ({payload.permission})",
    )
    await db.commit()
    await db.refresh(perm)

    return PermissionResponse(
        id=perm.id,
        file_id=perm.file_id,
        shared_with_id=perm.user_id,
        shared_with_email=target_user.email,
        shared_with_name=target_user.name,
        permission=perm.permission,
        created_at=perm.created_at,
    )


@router.get("/{file_id}/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all permissions for a file (owner or admin only)."""
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    _require_owner(file, current_user)

    result = await db.execute(
        select(FilePermission).where(FilePermission.file_id == file_id)
    )
    perms = result.scalars().all()

    out = []
    for p in perms:
        user_res = await db.execute(select(User).where(User.id == p.user_id))
        u = user_res.scalar_one_or_none()
        out.append(
            PermissionResponse(
                id=p.id,
                file_id=p.file_id,
                shared_with_id=p.user_id,
                shared_with_email=u.email if u else "",
                shared_with_name=u.name if u else "",
                permission=p.permission,
                created_at=p.created_at,
            )
        )
    return out


@router.delete("/{file_id}/permissions/{perm_id}", status_code=204)
async def revoke_permission(
    file_id: int,
    perm_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a permission (owner or admin)."""
    result = await db.execute(select(File).where(File.id == file_id))
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    _require_owner(file, current_user)

    result = await db.execute(
        select(FilePermission).where(
            FilePermission.id == perm_id,
            FilePermission.file_id == file_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(perm)
    await log_event(db, "UNSHARE", user_id=current_user.id, file_id=file_id)
    await db.commit()
