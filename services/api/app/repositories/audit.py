import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.writer import write_audit_event
from app.models.audit_events import AuditEvent


async def record_audit_event(
    session: AsyncSession,
    *,
    center_id: uuid.UUID,
    action: str,
    correlation_id: str,
    actor_user_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    incident_id: uuid.UUID | None = None,
    report_version_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """
    Wrap the audit writer for repository-level use.
    """
    return await write_audit_event(
        session,
        center_id=center_id,
        action=action,
        correlation_id=correlation_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        incident_id=incident_id,
        report_version_id=report_version_id,
        metadata=metadata,
    )
