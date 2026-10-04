"""Audit logging service."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_event(
    db: AsyncSession,
    action: str,
    user_id: int | None = None,
    file_id: int | None = None,
    node_id: str | None = None,
    details: str | None = None,
):
    """Record an audit event in the database."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        file_id=file_id,
        node_id=node_id,
        details=details,
    )
    db.add(entry)
    # Caller is responsible for commit
