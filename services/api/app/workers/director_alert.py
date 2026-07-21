"""
Director alert worker — processes director_alert outbox events.

In demo environment: console/DB logging only — no actual email/push sending.
Idempotency: uses outbox idempotency_key (derived from incident + version ID).

Per architecture.md:
  - Only the worker sends alerts; mobile and portal never call notification providers directly.
  - Use Cloud Tasks task names derived from event IDs for deduplication.
"""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.repositories.notification_deliveries import record_notification

logger = structlog.get_logger(__name__)


async def process_director_alert(event: OutboxEvent, session: AsyncSession) -> None:
    """
    Process a director_alert outbox event.
    Logs the alert to structured logs and records in notification_deliveries.
    """
    payload = event.payload
    incident_id = payload.get("incident_id")
    severity = payload.get("severity")

    logger.warning(
        "director_alert",
        incident_id=incident_id,
        severity=severity,
        outbox_event_id=str(event.id),
        message="High/Critical incident submitted — director review required immediately.",
    )

    import uuid
    await record_notification(
        session,
        center_id=event.center_id,
        notification_type="director_alert",
        status="logged",
        incident_id=uuid.UUID(incident_id) if incident_id else None,
        outbox_event_id=event.id,
    )
