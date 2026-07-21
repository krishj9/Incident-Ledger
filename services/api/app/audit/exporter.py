import uuid
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_events import AuditEvent
from app.models.incidents import Incident, IncidentChild
from app.models.report_versions import ReportVersion
from app.models.evidence import EvidenceItem
from app.models.guardian_packets import GuardianPacket
from app.models.outbox import OutboxEvent, AssistantInteraction
from app.repositories.audit import record_audit_event
from app.models.enums import IncidentStatus

async def build_audit_packet(session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID, actor_id: uuid.UUID, correlation_id: str) -> dict[str, Any]:
    # 1. Fetch incident
    stmt = select(Incident).where(
        Incident.id == incident_id, Incident.center_id == center_id
    )
    result = await session.execute(stmt)
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise ValueError("Incident not found")
        
    # 1b. Fetch incident children
    stmt_children = select(IncidentChild).where(IncidentChild.incident_id == incident_id)
    incident_children = (await session.execute(stmt_children)).scalars().all()

    # 2. Fetch all audit events
    stmt = select(AuditEvent).where(
        AuditEvent.incident_id == incident_id, AuditEvent.center_id == center_id
    ).order_by(AuditEvent.occurred_at)
    audit_events = (await session.execute(stmt)).scalars().all()

    # 3. Fetch all report versions
    stmt = select(ReportVersion).where(
        ReportVersion.incident_id == incident_id, ReportVersion.center_id == center_id
    ).order_by(ReportVersion.version_number)
    versions = (await session.execute(stmt)).scalars().all()

    # 4. Fetch evidence manifest
    stmt = select(EvidenceItem).where(
        EvidenceItem.incident_id == incident_id, EvidenceItem.center_id == center_id
    ).order_by(EvidenceItem.created_at)
    evidence = (await session.execute(stmt)).scalars().all()
    
    # 5. Fetch guardian packets
    stmt = select(GuardianPacket).where(
        GuardianPacket.incident_id == incident_id, GuardianPacket.center_id == center_id
    ).order_by(GuardianPacket.created_at)
    packets = (await session.execute(stmt)).scalars().all()
    
    # 6. Fetch assistant interactions (if any)
    stmt = select(AssistantInteraction).where(
        AssistantInteraction.incident_id == incident_id, AssistantInteraction.center_id == center_id
    ).order_by(AssistantInteraction.occurred_at)
    interactions = (await session.execute(stmt)).scalars().all()

    packet = {
        "incident_id": str(incident.id),
        "center_id": str(incident.center_id),
        "status": incident.status.value,
        "category": incident.category,
        "severity": incident.current_severity.value,
        "event_at": incident.event_at.isoformat(),
        "location": incident.location,
        "restricted": incident.restricted,
        "legal_hold": incident.legal_hold,
        "created_at": incident.created_at.isoformat(),
        "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
        
        "children": [
            {
                "child_id": str(c.child_id),
                "involvement_role": c.involvement_role
            }
            for c in incident_children
        ],
        
        "timeline": [
            {
                "id": str(e.id),
                "action": e.action,
                "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                "occurred_at": e.occurred_at.isoformat(),
                "metadata": e.metadata
            }
            for e in audit_events
        ],
        
        "report_versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "kind": v.version_kind.value,
                "rendered_narrative": v.rendered_narrative,
                "created_at": v.created_at.isoformat()
            }
            for v in versions
        ],
        
        "evidence_manifest": [
            {
                "id": str(ev.id),
                "content_type": ev.content_type,
                "byte_size": ev.byte_size,
                "payload_sha256": ev.payload_sha256,
                "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
                "finalized_at": ev.finalized_at.isoformat() if ev.finalized_at else None
            }
            for ev in evidence
        ],
        
        "guardian_packets": [
            {
                "id": str(p.id),
                "child_id": str(p.child_id),
                "primary_guardian_id": str(p.primary_guardian_id),
                "status": p.status.value,
                "acknowledgement_outcome": p.acknowledgement_outcome,
                "created_at": p.created_at.isoformat(),
                "acknowledged_at": p.acknowledged_at.isoformat() if p.acknowledged_at else None
            }
            for p in packets
        ],
        
        "writing_assistance": [
            {
                "suggestion_type": ai.suggestion_type,
                "disposition": ai.disposition,
                "actor_id": str(ai.actor_user_id),
                "occurred_at": ai.occurred_at.isoformat()
            }
            for ai in interactions
        ],
        
        "exported_at": datetime.now().isoformat()
    }
    
    # Write audit event for export
    await record_audit_event(
        session,
        center_id=center_id,
        action="audit_packet_exported",
        correlation_id=correlation_id,
        actor_user_id=actor_id,
        incident_id=incident_id
    )
    
    # Save to local filesystem for demo
    import os
    os.makedirs(".local-storage/audit-packets", exist_ok=True)
    with open(f".local-storage/audit-packets/{incident_id}.json", "w") as f:
        json.dump(packet, f, indent=2)
        
    return packet
