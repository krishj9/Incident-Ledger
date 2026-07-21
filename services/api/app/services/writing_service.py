import uuid
import hashlib
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from pydantic import BaseModel

from app.models.users import User
from app.models.incidents import Incident
from app.models.outbox import AssistantInteraction
from app.domain.enums import IncidentStatus
from app.repositories.incidents import get_incident
from app.integrations.gemini import get_writing_suggestions, PROMPT_VERSION, MODEL_ID
from app.services.exceptions import InvalidStateError, UnauthorizedError

class DispositionRequest(BaseModel):
    suggestion_type: str
    disposition: str # "accepted", "rejected", "edited"
    edited_text: str | None = None
    model_version: str
    prompt_version: str
    field_hashes: dict[str, str]

async def _get_incident_or_raise(session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID) -> Incident:
    incident = await get_incident(session, incident_id, center_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

async def get_suggestions(incident_data: dict[str, Any]) -> dict[str, Any]:
    if incident_data.get("category") == "suspected_abuse_neglect":
        return {"available": False, "reason": "ASSISTANCE_UNAVAILABLE_FOR_RESTRICTED_INCIDENT"}

    try:
        response = await get_writing_suggestions(incident_data)
        response["available"] = True
        return response
    except Exception as e:
        return {"available": False, "reason": "ASSISTANCE_TEMPORARILY_UNAVAILABLE"}


async def record_disposition(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    suggestion_id: str,
    request: DispositionRequest
) -> dict[str, Any]:
    incident = await _get_incident_or_raise(session, incident_id, user.center_id)

    if incident.created_by_user_id != user.id and incident.submitted_by_user_id != user.id:
        raise UnauthorizedError("Not authorized")
        
    if request.disposition not in ("accepted", "rejected", "edited"):
        raise HTTPException(status_code=422, detail="Invalid disposition")
        
    interaction = AssistantInteraction(
        center_id=user.center_id,
        incident_id=incident.id,
        actor_user_id=user.id,
        suggestion_id=suggestion_id,
        suggestion_type=request.suggestion_type,
        disposition=request.disposition,
        model_version=request.model_version,
        prompt_version=request.prompt_version,
        field_hashes=request.field_hashes
    )
    
    session.add(interaction)
    await session.flush()
    return {"status": "recorded"}
