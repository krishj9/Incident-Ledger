import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.incidents import Incident
from app.models.guardian_packets import GuardianPacket
from app.models.outbox import OutboxEvent, NotificationDelivery
from app.models.devices import Device
from app.models.enums import IncidentStatus, SeverityLevel

async def get_health_stats(session: AsyncSession) -> dict[str, Any]:
    # Incidents by status count
    stmt = select(Incident.status, func.count(Incident.id)).group_by(Incident.status)
    status_counts = dict(await session.execute(stmt))
    
    # High/critical awaiting review count
    stmt = select(func.count(Incident.id)).where(
        Incident.status == IncidentStatus.submitted,
        Incident.current_severity.in_([SeverityLevel.high, SeverityLevel.critical])
    )
    high_critical_awaiting_review = (await session.execute(stmt)).scalar() or 0
    
    # Pending acknowledgements count
    stmt = select(func.count(GuardianPacket.id)).where(GuardianPacket.status == "pending")
    pending_acknowledgements = (await session.execute(stmt)).scalar() or 0
    
    # Active/revoked device counts
    stmt = select(Device.status, func.count(Device.id)).group_by(Device.status)
    device_counts = dict(await session.execute(stmt))
    
    # Worker failure count (outbox events in failed state)
    stmt = select(func.count(OutboxEvent.id)).where(OutboxEvent.status == "failed")
    worker_failures = (await session.execute(stmt)).scalar() or 0
    
    # Notification delivery failure count
    stmt = select(func.count(NotificationDelivery.id)).where(NotificationDelivery.status == "failed")
    notification_failures = (await session.execute(stmt)).scalar() or 0

    return {
        "status": "ok",
        "incidents_by_status": {k.value if hasattr(k, "value") else str(k): v for k, v in status_counts.items()},
        "high_critical_awaiting_review": high_critical_awaiting_review,
        "pending_acknowledgements": pending_acknowledgements,
        "device_counts": {k: v for k, v in device_counts.items()},
        "worker_failures": worker_failures,
        "notification_failures": notification_failures,
        "pending_sync_operations": 0, # Sync ops not fully mocked in schema yet for status
        "oldest_pending_sync_age_seconds": 0
    }
