"""
Worker runner — polls the outbox_events table for pending events, claims and processes them.

For local dev: run as a separate process via `make worker`.
In production: deployed as Cloud Run job consuming Cloud Tasks.

Graceful shutdown on SIGTERM — finishes current batch then exits.
"""
from __future__ import annotations

import asyncio
import signal
import uuid
from typing import Callable, Coroutine, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models.outbox import OutboxEvent
from app.repositories.outbox import claim_pending_events, mark_event_failed, mark_event_processed
from app.workers.director_alert import process_director_alert
from app.workers.escalation import process_escalation_check

logger = structlog.get_logger(__name__)

# Dispatch table: event_type → handler
HANDLERS: dict[str, Callable[[OutboxEvent, AsyncSession], Coroutine[Any, Any, None]]] = {
    "director_alert": process_director_alert,
    "escalation_check": process_escalation_check,
    # guardian_notification: stub — not implemented in this phase
}

_shutdown = False


def _handle_sigterm(signum: int, frame: Any) -> None:
    global _shutdown
    logger.info("worker_sigterm_received", message="Graceful shutdown initiated")
    _shutdown = True


async def process_batch(batch_size: int = 10) -> int:
    """Claim and process one batch of outbox events. Returns count of events processed."""
    claim_id = str(uuid.uuid4())
    processed = 0

    # Use a single DB session per batch — each event is committed independently
    from app.db import async_session_factory
    async with async_session_factory() as session:
        async with session.begin():
            events = await claim_pending_events(session, limit=batch_size, claim_id=claim_id)

        if not events:
            return 0

        for event in events:
            handler = HANDLERS.get(event.event_type)
            if handler is None:
                logger.warning("worker_unknown_event_type", event_type=event.event_type, event_id=str(event.id))
                async with session.begin():
                    await mark_event_failed(session, event.id, f"No handler for event_type: {event.event_type}")
                continue

            try:
                async with session.begin():
                    await handler(event, session)
                    await mark_event_processed(session, event.id)
                processed += 1
                logger.info(
                    "worker_event_processed",
                    event_type=event.event_type,
                    event_id=str(event.id),
                )
            except Exception as exc:
                logger.error(
                    "worker_event_failed",
                    event_type=event.event_type,
                    event_id=str(event.id),
                    error=str(exc),
                )
                try:
                    async with session.begin():
                        await mark_event_failed(session, event.id, str(exc)[:500])
                except Exception:
                    pass

    return processed


async def run_worker(poll_interval: float = 5.0, batch_size: int = 10) -> None:
    """
    Main worker loop.
    Polls every `poll_interval` seconds. Processes up to `batch_size` events per tick.
    """
    signal.signal(signal.SIGTERM, _handle_sigterm)
    logger.info("worker_started", poll_interval=poll_interval, batch_size=batch_size)

    idle_log_interval = 60  # Log heartbeat every 60s when idle
    idle_seconds: float = 0.0

    while not _shutdown:
        try:
            count = await process_batch(batch_size=batch_size)

            if count > 0:
                idle_seconds = 0
                logger.info("worker_batch_complete", events_processed=count)
            else:
                idle_seconds += poll_interval
                if idle_seconds >= idle_log_interval:
                    logger.info("worker_heartbeat", status="idle", poll_interval=poll_interval)
                    idle_seconds = 0

        except Exception as exc:
            logger.error("worker_loop_error", error=str(exc))

        await asyncio.sleep(poll_interval)

    logger.info("worker_shutdown_complete")


if __name__ == "__main__":
    import logging
    from app.main import _configure_logging

    # Ensure structlog is configured
    try:
        _configure_logging()
    except Exception:
        logging.basicConfig(level=logging.INFO)

    asyncio.run(run_worker())
