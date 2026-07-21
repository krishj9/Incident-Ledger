import uuid
from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incidents import Incident
from app.models.outbox import RetentionDisposal
from app.models.enums import IncidentStatus
from app.repositories.audit import record_audit_event


async def process_retention_disposals(
    session: AsyncSession, center_id: uuid.UUID, correlation_id: str
) -> int:
    """
    Evaluate closed incidents for retention disposal.
    Retention period is 7 years from closure.
    """
    now = datetime.now(UTC)
    seven_years_ago = now - timedelta(days=365 * 7)

    # Find closed incidents > 7 years old
    stmt = select(Incident).where(
        Incident.center_id == center_id,
        Incident.status == IncidentStatus.closed,
        Incident.closed_at < seven_years_ago,
    )
    result = await session.execute(stmt)
    incidents = result.scalars().all()

    evaluated_count = 0
    
    # We use a synthetic UUID for the system actor in this demo
    system_actor_id = uuid.uuid4()

    for incident in incidents:
        # Check if already evaluated recently (skip for demo simplicity if already marked)
        check_stmt = select(RetentionDisposal).where(RetentionDisposal.incident_id == incident.id)
        if (await session.execute(check_stmt)).scalar_one_or_none():
            continue
            
        eligible = not incident.legal_hold
        
        disposal = RetentionDisposal(
            center_id=center_id,
            incident_id=incident.id,
            retention_years=7,
            eligible_for_disposal=eligible,
            blocked_by_legal_hold=incident.legal_hold,
            disposal_note="Legal hold active" if incident.legal_hold else "Eligible for disposal"
        )
        session.add(disposal)

        await record_audit_event(
            session,
            center_id=center_id,
            action="retention_disposal_evaluated",
            correlation_id=correlation_id,
            actor_user_id=system_actor_id,
            incident_id=incident.id,
            metadata={"eligible": eligible, "legal_hold": incident.legal_hold}
        )
        evaluated_count += 1

    await session.commit()
    return evaluated_count
