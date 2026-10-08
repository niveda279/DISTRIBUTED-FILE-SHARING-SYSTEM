"""
Security Monitoring Service.

Analyzes audit_logs to detect suspicious behavioral patterns
and produces security_events with LOW / MEDIUM / HIGH risk levels.

This is an academic behavioral monitoring module — not enterprise IDS.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.security_event import SecurityEvent
from app.models.user import User

logger = logging.getLogger(__name__)


async def _emit_security_event(
    db: AsyncSession,
    user_id: int | None,
    event_type: str,
    risk_level: str,
    details: str,
):
    ev = SecurityEvent(
        user_id=user_id,
        event_type=event_type,
        risk_level=risk_level,
        details=details,
    )
    db.add(ev)


async def analyze_failed_logins(db: AsyncSession):
    """Detect users with repeated LOGIN_FAILED actions in a short window."""
    window = datetime.now(timezone.utc) - timedelta(minutes=10)
    result = await db.execute(
        select(AuditLog.user_id, func.count(AuditLog.id).label("cnt"))
        .where(AuditLog.action == "LOGIN_FAILED")
        .where(AuditLog.timestamp >= window)
        .group_by(AuditLog.user_id)
        .having(func.count(AuditLog.id) >= 3)
    )
    rows = result.all()
    for row in rows:
        user_id, cnt = row.user_id, row.cnt
        risk = "HIGH" if cnt >= 10 else "MEDIUM"
        details = f"{cnt} failed login attempts in the last 10 minutes"
        # Avoid duplicates — check if we already raised this recently
        recent_check = await db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.user_id == user_id)
            .where(SecurityEvent.event_type == "REPEATED_LOGIN_FAILURE")
            .where(SecurityEvent.timestamp >= window)
            .limit(1)
        )
        if not recent_check.scalar_one_or_none():
            await _emit_security_event(db, user_id, "REPEATED_LOGIN_FAILURE", risk, details)
            logger.warning(f"Security: {risk} — user {user_id}: {details}")


async def analyze_mass_downloads(db: AsyncSession):
    """Detect users downloading unusually many files in a short window."""
    window = datetime.now(timezone.utc) - timedelta(minutes=15)
    result = await db.execute(
        select(AuditLog.user_id, func.count(AuditLog.id).label("cnt"))
        .where(AuditLog.action == "DOWNLOAD")
        .where(AuditLog.timestamp >= window)
        .group_by(AuditLog.user_id)
        .having(func.count(AuditLog.id) >= 20)
    )
    rows = result.all()
    for row in rows:
        user_id, cnt = row.user_id, row.cnt
        risk = "HIGH" if cnt >= 50 else "MEDIUM"
        details = f"{cnt} downloads in 15 minutes — possible data exfiltration"
        recent_check = await db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.user_id == user_id)
            .where(SecurityEvent.event_type == "MASS_DOWNLOAD")
            .where(SecurityEvent.timestamp >= window)
            .limit(1)
        )
        if not recent_check.scalar_one_or_none():
            await _emit_security_event(db, user_id, "MASS_DOWNLOAD", risk, details)


async def analyze_integrity_failures(db: AsyncSession):
    """Detect recent integrity check failures."""
    window = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.action == "INTEGRITY_FAILURE")
        .where(AuditLog.timestamp >= window)
    )
    events = result.scalars().all()
    for ev in events:
        recent_check = await db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.event_type == "INTEGRITY_FAILURE")
            .where(SecurityEvent.user_id == ev.user_id)
            .where(SecurityEvent.timestamp >= window)
            .limit(1)
        )
        if not recent_check.scalar_one_or_none():
            details = f"SHA-256 integrity failure detected on file {ev.file_id} from node {ev.node_id}"
            await _emit_security_event(db, ev.user_id, "INTEGRITY_FAILURE", "HIGH", details)


async def analyze_disabled_user_access(db: AsyncSession):
    """Detect disabled accounts still generating login attempts."""
    window = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(AuditLog.user_id, func.count().label("cnt"))
        .where(AuditLog.action.in_(["LOGIN_FAILED", "LOGIN"]))
        .where(AuditLog.timestamp >= window)
        .group_by(AuditLog.user_id)
    )
    for row in result.all():
        user_id, cnt = row.user_id, row.cnt
        if not user_id:
            continue
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and not user.is_active:
            recent_check = await db.execute(
                select(SecurityEvent)
                .where(SecurityEvent.user_id == user_id)
                .where(SecurityEvent.event_type == "DISABLED_ACCOUNT_ACCESS")
                .where(SecurityEvent.timestamp >= window)
                .limit(1)
            )
            if not recent_check.scalar_one_or_none():
                details = f"Disabled account {user.email} attempted {cnt} login(s)"
                await _emit_security_event(db, user_id, "DISABLED_ACCOUNT_ACCESS", "HIGH", details)


async def run_security_analysis(db: AsyncSession):
    """Run all security checks. Called periodically."""
    try:
        await analyze_failed_logins(db)
        await analyze_mass_downloads(db)
        await analyze_integrity_failures(db)
        await analyze_disabled_user_access(db)
        await db.commit()
    except Exception as e:
        logger.error(f"Security analysis error: {e}")
        await db.rollback()
