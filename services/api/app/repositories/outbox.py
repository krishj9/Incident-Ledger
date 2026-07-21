"""
Outbox repository — atomic claim/process operations for the transactional outbox.
Uses SELECT FOR UPDATE SKIP LOCKED for concurrent safe claiming.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent

logger = structlog.get_logger(__name__)


async def insert_outbox_event(
    session: AsyncSession,
    *,
    center_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    idempotency_key: str,
) -> OutboxEvent | None:
    """
    Insert a new pending outbox event in the current transaction.
    Returns None if the idempotency_key already exists (duplicate suppressed).
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = (
        pg_insert(OutboxEvent)
        .values(
            center_id=center_id,
            event_type=event_type,
            payload=payload,
            idempotency_key=idempotency_key,
            status="pending",
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(OutboxEvent.id)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        logger.info("outbox_event_duplicate_suppressed", idempotency_key=idempotency_key)
        return None

    # Fetch and return the full object
    event = await session.get(OutboxEvent, row[0])
    return event


async def claim_pending_events(
    session: AsyncSession,
    *,
    limit: int = 10,
    claim_id: str,
) -> list[OutboxEvent]:
    """
    Atomically claim up to `limit` pending outbox events.
    Uses FOR UPDATE SKIP LOCKED for concurrent worker safety.
    """
    now = datetime.now(UTC)

    # Select pending events (or failed with retry_count < 5) for update
    stmt = (
        select(OutboxEvent)
        .where(
            OutboxEvent.status.in_(["pending", "failed"]),
            OutboxEvent.retry_count < 5,
        )
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    # Mark as claimed
    for ev in events:
        ev.status = "claimed"
        ev.claimed_at = now
        ev.claim_id = claim_id

    await session.flush()
    return list(events)


async def mark_event_processed(session: AsyncSession, event_id: uuid.UUID) -> None:
    """Mark an outbox event as successfully processed."""
    result = await session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event:
        event.status = "processed"
        event.processed_at = datetime.now(UTC)
        await session.flush()


async def mark_event_failed(session: AsyncSession, event_id: uuid.UUID, error: str) -> None:
    """Increment retry count and mark an outbox event as failed."""
    result = await session.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event:
        event.status = "failed"
        event.retry_count = (event.retry_count or 0) + 1
        event.last_error = error[:1000]  # Trim to avoid large error payloads
        await session.flush()
