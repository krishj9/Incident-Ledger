import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incidents import Incident
from app.models.outbox import LegalHold
from app.models.users import User
from app.repositories.audit import record_audit_event
from app.services.exceptions import UnauthorizedError


async def apply_legal_hold(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    reason: str,
    correlation_id: str,
) -> dict[str, Any]:
    # Require reason
    if not reason or not reason.strip():
        raise ValueError("Legal hold reason is required")

    stmt = select(Incident).where(Incident.id == incident_id, Incident.center_id == user.center_id)
    result = await session.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise ValueError("Incident not found")

    if incident.legal_hold:
        return {"status": "already_on_hold"}

    # Update incident
    incident.legal_hold = True
    session.add(incident)

    # Record legal hold application
    hold = LegalHold(
        center_id=user.center_id,
        incident_id=incident.id,
        applied_by_user_id=user.id,
        reason=reason
    )
    session.add(hold)

    # Record audit event
    await record_audit_event(
        session,
        center_id=user.center_id,
        action="legal_hold_applied",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        metadata={"reason": reason}
    )

    await session.commit()
    
    return {"status": "applied", "incident_id": str(incident.id)}
