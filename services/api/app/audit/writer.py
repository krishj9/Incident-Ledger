"""
Audit event writer — append-only insert into audit_events.

Security rules (security-privacy.md §Logging):
  - Never log raw tokens, image bytes, full narrative, or complete email links
  - Audit records are append-only and retention-bound
  - The DB trigger on audit_events prevents UPDATE/DELETE (enforced at DB level)

This writer is the single insertion point for all audit_events rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_events import AuditEvent
from app.models.base import generate_uuid7

logger = structlog.get_logger(__name__)


async def write_audit_event(
    session: AsyncSession,
    *,
    center_id: uuid.UUID,
    action: str,
    correlation_id: str,
    actor_user_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    incident_id: uuid.UUID | None = None,
    report_version_id: uuid.UUID | None = None,
    metadata: dict | None = None,  # type: ignore[type-arg]
) -> AuditEvent:
    """
    Insert one audit event row.

    Callers must flush/commit the session after calling this function
    (or rely on the get_db_session dependency's auto-commit on success).

    The metadata dict must contain ONLY safe fields:
    opaque IDs, status codes, event types, action descriptors.
    NEVER include: raw tokens, passwords, narrative content, or PII.
    """
    event = AuditEvent(
        id=generate_uuid7(),
        center_id=center_id,
        action=action,
        correlation_id=correlation_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        incident_id=incident_id,
        report_version_id=report_version_id,
        occurred_at=datetime.now(UTC),
        metadata_=metadata or {},
    )
    session.add(event)

    logger.info(
        "audit_event_written",
        action=action,
        center_id=str(center_id),
        # Log opaque IDs only — never actor name, narrative, or PII
        has_incident=incident_id is not None,
    )
    return event
