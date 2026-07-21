"""
Escalation worker — processes escalation_check outbox events.

Logic per infra-and-operations.md §Worker jobs:
  - Backup escalation: 30 minutes unacknowledged high/critical
  - Regional escalation: 60 minutes unacknowledged (critical only per product-scope.md §Severity)

Idempotency key: {incident_id}-{escalation_stage}
If the incident has already been acknowledged (status != submitted/under_review),
the worker skips gracefully — this is a no-op (idempotent).
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incidents import Incident
from app.models.outbox import OutboxEvent
from app.models.users import User
from app.repositories.notification_deliveries import record_notification

logger = structlog.get_logger(__name__)

_UNACKNOWLEDGED_STATUSES = {"submitted", "under_review"}


async def process_escalation_check(event: OutboxEvent, session: AsyncSession) -> None:
    """
    Process an escalation_check outbox event.

    Checks if a high/critical incident has not been acknowledged within
    the escalation window. If not, logs an escalation alert and records
    a notification delivery.

    Idempotency: The outbox idempotency_key ({incident_id}-{escalation_stage})
    ensures this handler runs at most once per incident+stage combination.
    """
    payload = event.payload
    incident_id_str = payload.get("incident_id")
    escalation_stage = payload.get("escalation_stage")  # "backup" or "regional"
    submitted_at_str = payload.get("submitted_at")

    if not incident_id_str or not escalation_stage:
        logger.error("escalation_check_invalid_payload", payload=payload)
        return

    incident_id = uuid.UUID(incident_id_str)

    # Fetch incident
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        logger.warning("escalation_check_incident_not_found", incident_id=incident_id_str)
        return

    # Idempotent skip: if already acknowledged or beyond submitted/under_review, no action
    if incident.status.value not in _UNACKNOWLEDGED_STATUSES:
        logger.info(
            "escalation_check_skipped",
            incident_id=incident_id_str,
            current_status=incident.status.value,
            reason="Already acknowledged or advanced past review stage",
        )
        return

    # Verify time elapsed
    now = datetime.now(UTC)
    submitted_at = incident.submitted_at
    if not submitted_at:
        logger.warning("escalation_check_no_submitted_at", incident_id=incident_id_str)
        return

    elapsed_minutes = (now - submitted_at).total_seconds() / 60

    if escalation_stage == "backup" and elapsed_minutes < 30:
        logger.info("escalation_check_not_yet_due", stage="backup", elapsed_minutes=elapsed_minutes)
        return

    if escalation_stage == "regional" and elapsed_minutes < 60:
        logger.info("escalation_check_not_yet_due", stage="regional", elapsed_minutes=elapsed_minutes)
        return

    # Find target recipient
    notification_type = f"{escalation_stage}_escalation"
    recipient_role = "backup_director" if escalation_stage == "backup" else "regional_admin"

    logger.warning(
        "escalation_alert",
        incident_id=incident_id_str,
        severity=str(incident.current_severity),
        escalation_stage=escalation_stage,
        elapsed_minutes=round(elapsed_minutes, 1),
        recipient_role=recipient_role,
        message=f"{escalation_stage.capitalize()} director escalation: incident {incident_id_str} "
                f"unacknowledged for {round(elapsed_minutes)} minutes.",
    )

    # Find a user with the required escalation role in the same center
    recipient_user: User | None = None
    try:
        user_result = await session.execute(
            select(User).where(
                User.center_id == incident.center_id,
                User.role == recipient_role,
            ).limit(1)
        )
        recipient_user = user_result.scalar_one_or_none()
    except Exception:
        pass  # Best-effort; notification is still logged

    await record_notification(
        session,
        center_id=incident.center_id,
        notification_type=notification_type,
        status="logged",
        incident_id=incident_id,
        recipient_user_id=recipient_user.id if recipient_user else None,
        outbox_event_id=event.id,
    )
