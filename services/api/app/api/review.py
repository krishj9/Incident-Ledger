"""
Review router — director review workflow endpoints.

All mutations require Idempotency-Key header.
All responses include X-Correlation-ID (via middleware).

Roles:
  GET /review-queue                         → director/backup/regional
  POST /incidents/{id}/review/acknowledge   → director/backup/regional
  POST /incidents/{id}/review/edits         → director only
  POST /incidents/{id}/review/request-changes → director only
  POST /incidents/{id}/review/severity      → director only
  POST /incidents/{id}/review/approve       → director only
  POST /incidents/{id}/addenda              → staff + director
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_center_scope, require_idempotency_key
from app.db import get_db_session
from app.models.enums import UserRole
from app.models.users import User
from app.services import review_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["review"])


# ── Request / Response models ─────────────────────────────────────────────────

class ReviewQueueItem(BaseModel):
    incident_id: uuid.UUID
    status: str
    category: str
    severity: str
    location: str
    submitted_at: datetime | None
    elapsed_seconds: int
    escalation_state: str | None
    assigned_director_id: uuid.UUID | None

    class Config:
        from_attributes = True


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int


class AcknowledgeResponse(BaseModel):
    incident_id: uuid.UUID
    status: str


class DirectorEditRequest(BaseModel):
    rendered_narrative: str = Field(min_length=1)
    edit_reason: str = Field(min_length=1)


class DirectorEditResponse(BaseModel):
    incident_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    version_kind: str


class RequestChangesRequest(BaseModel):
    reason: str = Field(min_length=1)


class RequestChangesResponse(BaseModel):
    incident_id: uuid.UUID
    status: str


class ChangeSeverityRequest(BaseModel):
    new_severity: str
    reason: str = Field(min_length=1)


class ChangeSeverityResponse(BaseModel):
    incident_id: uuid.UUID
    current_severity: str
    staff_selected_severity: str


class ApproveResponse(BaseModel):
    incident_id: uuid.UUID
    status: str
    approved_version_id: uuid.UUID
    approved_at: datetime


class AddendumRequest(BaseModel):
    content: str = Field(min_length=1)


class AddendumResponse(BaseModel):
    incident_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    version_kind: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReviewQueueResponse:
    """Get the review queue of submitted and under-review incidents."""
    items_data = await review_service.get_review_queue(db, current_user)
    items = [ReviewQueueItem(**item) for item in items_data]
    return ReviewQueueResponse(items=items, total=len(items))


@router.post("/incidents/{incident_id}/review/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_review(
    incident_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> AcknowledgeResponse:
    """Acknowledge review ownership; transitions submitted → under_review."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    incident = await review_service.acknowledge_review(db, current_user, incident_id, correlation_id)
    await db.commit()
    return AcknowledgeResponse(incident_id=incident.id, status=incident.status.value)


@router.post("/incidents/{incident_id}/review/edits", response_model=DirectorEditResponse)
async def create_director_edit(
    incident_id: uuid.UUID,
    body: DirectorEditRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> DirectorEditResponse:
    """
    Create a minor wording edit on an incident under review.
    Edits MUST be limited to grammar, spelling, formatting, neutrality, or clarity only.
    Requires edit_reason.
    """
    if current_user.role != UserRole.director:
        raise HTTPException(status_code=403, detail="Only directors can edit narratives")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    version = await review_service.create_director_edit(
        db,
        current_user,
        incident_id,
        body.rendered_narrative,
        body.edit_reason,
        correlation_id,
    )
    await db.commit()
    return DirectorEditResponse(
        incident_id=incident_id,
        version_id=version.id,
        version_number=version.version_number,
        version_kind=version.version_kind,
    )


@router.post("/incidents/{incident_id}/review/request-changes", response_model=RequestChangesResponse)
async def request_changes(
    incident_id: uuid.UUID,
    body: RequestChangesRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> RequestChangesResponse:
    """Return incident to staff for factual clarification."""
    if current_user.role != UserRole.director:
        raise HTTPException(status_code=403, detail="Only directors can request changes")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    incident = await review_service.request_changes(db, current_user, incident_id, body.reason, correlation_id)
    await db.commit()
    return RequestChangesResponse(incident_id=incident.id, status=incident.status.value)


@router.post("/incidents/{incident_id}/review/severity", response_model=ChangeSeverityResponse)
async def change_severity(
    incident_id: uuid.UUID,
    body: ChangeSeverityRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> ChangeSeverityResponse:
    """Change incident severity. Staff-selected severity is preserved. Reason required."""
    if current_user.role != UserRole.director:
        raise HTTPException(status_code=403, detail="Only directors can change severity")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    incident = await review_service.change_severity(
        db, current_user, incident_id, body.new_severity, body.reason, correlation_id
    )
    await db.commit()
    cs = incident.current_severity
    ss = incident.staff_selected_severity
    return ChangeSeverityResponse(
        incident_id=incident.id,
        current_severity=cs.value if hasattr(cs, "value") else str(cs),
        staff_selected_severity=ss.value if hasattr(ss, "value") else str(ss),
    )


@router.post("/incidents/{incident_id}/review/approve", response_model=ApproveResponse)
async def approve_incident(
    incident_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> ApproveResponse:
    """Approve an incident; creates frozen approved version and triggers guardian notification."""
    if current_user.role != UserRole.director:
        raise HTTPException(status_code=403, detail="Only directors can approve incidents")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    version = await review_service.approve(db, current_user, incident_id, correlation_id)

    # Re-fetch incident to get approved_at and status
    from sqlalchemy import select
    from app.models.incidents import Incident
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one()

    await db.commit()
    return ApproveResponse(
        incident_id=incident_id,
        status=incident.status.value,
        approved_version_id=version.id,
        approved_at=incident.approved_at,
    )


@router.post("/incidents/{incident_id}/addenda", response_model=AddendumResponse)
async def create_addendum(
    incident_id: uuid.UUID,
    body: AddendumRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    idempotency_key: str = Depends(require_idempotency_key),
) -> AddendumResponse:
    """Create a post-approval addendum. Original approved version remains immutable."""
    correlation_id = request.headers.get("X-Correlation-ID", "")
    version = await review_service.create_addendum(
        db, current_user, incident_id, body.content, correlation_id
    )
    await db.commit()
    return AddendumResponse(
        incident_id=incident_id,
        version_id=version.id,
        version_number=version.version_number,
        version_kind=version.version_kind,
    )
