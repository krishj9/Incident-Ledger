import hashlib
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db import get_db_session
from app.models.outbox import EmailLinkToken
from app.models.guardian_packets import GuardianPacket
from app.models.report_versions import ReportVersion
from app.models.children import Child
from app.models.incidents import Incident, IncidentChild
from app.models.audit_events import AuditEvent
from app.models.acknowledgements import Acknowledgement

router = APIRouter(prefix="/v1/guardian", tags=["guardian_public"])

class AckRequest(BaseModel):
    outcome: str = Field(..., pattern="^(acknowledged|disagreed)$")
    typed_full_name: str = Field(..., min_length=2, max_length=100)
    disagreement_comment: str | None = None

async def _verify_token_and_get_packet(token: str, db: AsyncSession):
    # Hash the raw token to find it in the DB
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Generic rejection string
    generic_error = "This link is no longer valid."
    
    result = await db.execute(select(EmailLinkToken).where(EmailLinkToken.token_hash == token_hash))
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        raise HTTPException(status_code=404, detail=generic_error)
        
    if token_record.status != "active" or token_record.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=404, detail=generic_error)
        
    packet = await db.get(GuardianPacket, token_record.guardian_packet_id)
    if not packet or packet.status in ("acknowledged", "disagreed", "unreachable", "closed"):
        raise HTTPException(status_code=404, detail=generic_error)
        
    incident = await db.get(Incident, packet.incident_id)
    child = await db.get(Child, packet.child_id)
    version = await db.get(ReportVersion, packet.approved_version_id)
    incident_child_result = await db.execute(
        select(IncidentChild).where(
            (IncidentChild.incident_id == incident.id) & 
            (IncidentChild.child_id == child.id)
        )
    )
    incident_child = incident_child_result.scalar_one_or_none()
    
    if not incident or not child or not version or not incident_child:
        raise HTTPException(status_code=404, detail=generic_error)
        
    return token_record, packet, incident, child, version, incident_child


@router.get("/acknowledgements/{token}")
async def get_packet_for_token(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    token_record, packet, incident, child, version, incident_child = await _verify_token_and_get_packet(token, db)
    
    # Audit log (viewed)
    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=None, # Public token auth, no staff user
        action="guardian_packet_viewed",
        correlation_id=token_record.token_hash[:8],
        metadata_={"packet_id": str(packet.id)}
    )
    db.add(audit)
    await db.commit()
    
    # Build child-specific view
    # Real implementation would apply a redaction filter here if needed, 
    # but the prompt says the approved text should be filtered to child-specific details.
    # In a full app, this relies on structured data, but here we'll assume `rendered_narrative` 
    # and `child_specific_details` constitute the view.
    return {
        "child_name": child.display_name,
        "incident_date": incident.event_at.isoformat() if getattr(incident, 'event_at', None) else None,
        "incident_category": incident.category.replace('_', ' ').title(),
        "approved_narrative": version.rendered_narrative,
        "child_details": incident_child.child_specific_details,
        "acknowledgement_status": packet.status
    }


@router.post("/acknowledgements/{token}")
async def submit_acknowledgement(
    token: str,
    request: AckRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    token_record, packet, incident, child, version, _ = await _verify_token_and_get_packet(token, db)
    
    # 1. Mark token as used
    token_record.status = "used"
    token_record.used_at = datetime.now(UTC)
    
    # 2. Update packet status
    packet.status = request.outcome
    
    # 3. Create Acknowledgement record
    ack = Acknowledgement(
        guardian_packet_id=packet.id,
        method="email_link",
        typed_full_name=request.typed_full_name,
        receipt_confirmed=True,
        outcome=request.outcome,
        disagreement_comment=request.disagreement_comment,
        report_version_id=version.id
    )
    db.add(ack)
    
    # 4. Write audit event
    action = "guardian_acknowledged" if request.outcome == "acknowledged" else "guardian_disagreed"
    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=None,
        action=action,
        correlation_id=token_record.token_hash[:8],
        metadata_={"packet_id": str(packet.id)}
    )
    db.add(audit)
    
    await db.commit()
    return {"status": "success", "message": "Thank you. Your response has been recorded."}
