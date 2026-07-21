"""
Notification deliveries repository — immutable records of all alert/email attempts.
In demo: console/DB logging only, no actual email sending.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import NotificationDelivery


async def record_notification(
    session: AsyncSession,
    *,
    center_id: uuid.UUID,
    notification_type: str,
    status: str,
    incident_id: uuid.UUID | None = None,
    guardian_packet_id: uuid.UUID | None = None,
    recipient_user_id: uuid.UUID | None = None,
    outbox_event_id: uuid.UUID | None = None,
    error_detail: str | None = None,
) -> NotificationDelivery:
    """
    Insert an immutable notification delivery record.
    Used by workers after logging/sending an alert or email.
    """
    delivery = NotificationDelivery(
        center_id=center_id,
        notification_type=notification_type,
        status=status,
        incident_id=incident_id,
        guardian_packet_id=guardian_packet_id,
        recipient_user_id=recipient_user_id,
        outbox_event_id=outbox_event_id,
        error_detail=error_detail,
    )
    session.add(delivery)
    await session.flush()
    return delivery
