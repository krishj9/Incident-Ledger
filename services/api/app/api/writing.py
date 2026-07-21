import uuid
from typing import Annotated, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user, require_center_scope
from app.db import get_db_session
from app.models.users import User
from app.services import writing_service
from app.integrations.gemini import GeminiResponse

router = APIRouter(prefix="/v1/writing-assistance", tags=["writing"])

class SuggestionRequest(BaseModel):
    category: str | None = None
    severity: str | None = None
    event_time_precision: str | None = None
    event_at: str | None = None
    location: str | None = None
    witnesses_known: bool | None = None
    original_factual_notes: str | None = None
    actions_taken: str | None = None
    treatment_response: str | None = None

@router.post("/suggestions")
async def get_suggestions(
    body: SuggestionRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> GeminiResponse:
    return await writing_service.get_suggestions(body.model_dump())

@router.post("/suggestions/{incident_id}/disposition/{suggestion_id}")
async def record_disposition(
    incident_id: uuid.UUID,
    suggestion_id: str,
    body: writing_service.DispositionRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    res = await writing_service.record_disposition(db, current_user, incident_id, suggestion_id, body)
    await db.commit()
    return res
