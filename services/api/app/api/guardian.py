import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models.users import User
from app.services import guardian_service
from app.api.deps import require_center_scope

router = APIRouter(prefix="/v1", tags=["guardian"])

class InPersonAckRequest(BaseModel):
    typed_full_name: str = Field(..., min_length=2, max_length=100)
    receipt_confirmed: bool = True
    outcome: str = Field(..., pattern="^(acknowledged|disagreed)$")

class ContactAttemptRequest(BaseModel):
    guardian_id: uuid.UUID
    method: str = Field(..., min_length=1, max_length=50)
    outcome: str = Field(..., min_length=1, max_length=50)
    notes: str | None = None

class CloseUnreachableRequest(BaseModel):
    packet_id: uuid.UUID

@router.post("/guardian-packets/{packet_id}/in-person-acknowledgements")
async def record_in_person_acknowledgement(
    packet_id: uuid.UUID,
    request: InPersonAckRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    ack = await guardian_service.record_in_person_ack(
        db=db,
        user=current_user,
        packet_id=packet_id,
        typed_full_name=request.typed_full_name,
        receipt_confirmed=request.receipt_confirmed,
        outcome=request.outcome,
    )
    await db.commit()
    return {"status": "success", "acknowledgement_id": ack.id}

@router.post("/guardian-packets/{packet_id}/email-links")
async def send_email_link(
    packet_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    # Sends email link, logs to console, outbox, etc.
    await guardian_service.send_email_link(db, current_user, packet_id)
    await db.commit()
    return {"status": "success", "message": "Email link generated and queued"}

@router.post("/incidents/{incident_id}/contact-attempts")
async def record_contact_attempt(
    incident_id: uuid.UUID,
    request: ContactAttemptRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    attempt = await guardian_service.record_contact_attempt(
        db=db,
        user=current_user,
        incident_id=incident_id,
        guardian_id=request.guardian_id,
        method=request.method,
        outcome=request.outcome,
        notes=request.notes,
    )
    await db.commit()
    return {"status": "success", "contact_attempt_id": attempt.id}

@router.post("/incidents/{incident_id}/acknowledgement/close-unreachable")
async def close_unreachable(
    incident_id: uuid.UUID,
    request: CloseUnreachableRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    await guardian_service.close_unreachable(
        db=db,
        user=current_user,
        incident_id=incident_id,
        packet_id=request.packet_id,
    )
    await db.commit()
    return {"status": "success", "message": "Packet marked as unreachable"}
