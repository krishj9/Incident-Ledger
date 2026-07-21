from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_center_scope, require_idempotency_key
from app.api.schemas.incidents import (
    IncidentCreate,
    IncidentDraftUpdate,
    IncidentListResponse,
    IncidentResponse,
    IncidentSubmit,
    SubmitResponse,
    SyncOperationsRequest,
)
from app.db import get_db_session
from app.domain.enums import IncidentStatus
from app.models.enums import UserRole
from app.models.report_versions import ReportVersion
from app.models.users import User
from app.repositories import incidents as incident_repo
from app.services import incident_service, sync_service, evidence_service
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import (
    InvalidStateError,
    UnauthorizedError,
    ValidationFailedError,
)

router = APIRouter(prefix="/v1/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> IncidentListResponse:
    """
    List incidents. Scoped to user's center_id.
    Staff see own; director+ see all.
    """
    filters = {"status": status} if status else None
    results = await incident_repo.list_incidents(
        session=db,
        center_id=current_user.center_id,
        user_role=current_user.role.value,
        user_id=current_user.id,
        filters=filters,
    )
    # Basic pagination in-memory for now
    start = (page - 1) * per_page
    end = start + per_page
    paginated = results[start:end]

    return IncidentListResponse(
        incidents=[IncidentResponse.model_validate(inc) for inc in paginated]
    )


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_draft(
    request: Request,
    body: IncidentCreate,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> Any:
    """
    Create a new draft incident.
    Requires staff role.
    """
    if current_user.role != UserRole.staff:
        raise HTTPException(status_code=403, detail="Only staff can create incidents")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    
    # Children schema matching
    children = []
    if body.children is not None:
        for child in body.children:
            children.append({"child_id": child.child_id, "role": child.role})
        
    incident = await incident_service.create_draft(
        session=db,
        user=current_user,
        center_id=current_user.center_id,
        category=body.category.value if body.category else "other",
        severity=body.severity.value if body.severity else "low",
        children=children,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        event_at=datetime.now(UTC),
        event_time_precision="exact",
        location="",
        original_factual_notes="",
        actions_taken="",
        witnesses_known=False,
    )

    return IncidentResponse.model_validate(incident)


@router.get("/{incident_id}")
async def get_incident_detail(
    incident_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """
    Get incident detail with version history.
    Policy-scoped (staff see own; director+ see center; restricted needs compliance).
    Returns 404 (non-disclosing) if not accessible.
    """
    try:
        response_data = await incident_service.get_incident_detail(db, current_user, incident_id)
        return response_data
    except EntityNotFoundError:
        # Non-disclosing 404
        raise HTTPException(status_code=404, detail="Incident not found")


@router.patch("/{incident_id}/draft", response_model=IncidentResponse)
async def update_draft_endpoint(
    incident_id: uuid.UUID,
    request: Request,
    body: IncidentDraftUpdate,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
    if_match: str | None = Header(None, alias="If-Match"),
) -> Any:
    """
    Update draft fields.
    """
    if not if_match:
        raise HTTPException(status_code=400, detail="If-Match header is required for updates")

    correlation_id = request.headers.get("X-Correlation-ID", "")
    
    changes = body.model_dump(exclude_unset=True)
    if "children" in changes and changes["children"] is not None:
        # Convert enum for children
        changes["children"] = [{"child_id": c["child_id"], "role": c["role"]} for c in changes["children"]]
        
    if "category" in changes and changes["category"] is not None:
        changes["category"] = changes["category"].value
    if "severity" in changes and changes["severity"] is not None:
        changes["severity"] = changes["severity"].value
    if "event_time_precision" in changes and changes["event_time_precision"] is not None:
        changes["event_time_precision"] = changes["event_time_precision"].value

    incident = await incident_service.update_draft(
        session=db,
        user=current_user,
        incident_id=incident_id,
        etag=if_match.strip('"'),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        **changes
    )

    return IncidentResponse.model_validate(incident)


@router.post("/{incident_id}/submit", response_model=SubmitResponse)
async def submit_incident_endpoint(
    incident_id: uuid.UUID,
    request: Request,
    body: IncidentSubmit,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> Any:
    """
    Submit incident.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "")

    response = await incident_service.submit(
        session=db,
        user=current_user,
        incident_id=incident_id,
        attestation=body.staff_attestation.model_dump(),
        device_info=body.submitted_from.model_dump(),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )

    return response


@router.post("/{incident_id}/sync-operations")
async def sync_operations_endpoint(
    incident_id: uuid.UUID,
    request: Request,
    body: SyncOperationsRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    device_id: uuid.UUID = Header(alias="X-Device-Id"),
) -> list[dict[str, Any]]:
    """
    Idempotent offline operation batch sync.
    Requires staff role and device_id.
    """
    if current_user.role != UserRole.staff:
        raise HTTPException(status_code=403, detail="Only staff can sync operations")

    results = await sync_service.process_sync_batch(
        session=db,
        user=current_user,
        device_id=device_id,
        incident_id=incident_id,
        operations=body.operations,
    )
    
    return results

from app.api.schemas.evidence import (
    EvidenceIntentRequest,
    EvidenceIntentResponse,
    EvidenceFinalizeRequest,
    EvidenceFinalizeResponse,
)

@router.post("/{incident_id}/evidence/intents", response_model=EvidenceIntentResponse)
async def create_evidence_intent_endpoint(
    incident_id: uuid.UUID,
    body: EvidenceIntentRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    device_id: uuid.UUID = Header(alias="X-Device-Id"),
) -> Any:
    """
    Validate conditions and create an upload intent for evidence.
    """
    if current_user.role != UserRole.staff:
        raise HTTPException(status_code=403, detail="Only staff can capture evidence")

    response = await evidence_service.create_upload_intent(
        session=db,
        user=current_user,
        device_id=device_id,
        incident_id=incident_id,
        media_type=body.media_type,
        byte_size=body.byte_size,
    )
    
    return response


@router.post("/{incident_id}/evidence/{evidence_id}/finalize", response_model=EvidenceFinalizeResponse)
async def finalize_evidence_endpoint(
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    body: EvidenceFinalizeRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    device_id: uuid.UUID = Header(alias="X-Device-Id"),
) -> Any:
    """
    Finalize an evidence upload, verifying hash and moving it to retention storage.
    """
    if current_user.role != UserRole.staff:
        raise HTTPException(status_code=403, detail="Only staff can finalize evidence")

    response = await evidence_service.finalize_evidence(
        session=db,
        user=current_user,
        device_id=device_id,
        incident_id=incident_id,
        evidence_id=evidence_id,
        client_sha256=body.client_sha256,
    )
    
    return response
