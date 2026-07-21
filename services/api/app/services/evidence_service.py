from __future__ import annotations

import uuid
from typing import Any
import structlog
from datetime import datetime, timedelta, UTC

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.domain.enums import IncidentStatus
from app.domain.policies import is_photo_permitted
from app.repositories import evidence as evidence_repo
from app.repositories import incidents as incident_repo
from app.repositories.audit import record_audit_event
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import ValidationFailedError, InvalidStateError, UnauthorizedError
from app.integrations import storage

logger = structlog.get_logger(__name__)

async def create_upload_intent(
    session: AsyncSession,
    user: User,
    device_id: uuid.UUID,
    incident_id: uuid.UUID,
    media_type: str,
    byte_size: int,
) -> dict[str, Any]:
    """
    Validate conditions and create an upload intent for evidence.
    """
    # 1. Fetch incident
    result = await incident_repo.get_incident_with_etag(session, incident_id, user.center_id)
    if not result:
        raise EntityNotFoundError("Incident not found")
    
    incident, _ = result

    # 2. Validate Authorization
    if incident.created_by_user_id != user.id and incident.submitted_by_user_id != user.id:
        raise UnauthorizedError("Not authorized to add evidence to this incident")

    # 3. Validate Status
    if IncidentStatus(incident.status.value) not in (IncidentStatus.draft, IncidentStatus.changes_requested):
        raise InvalidStateError("Incident is not in an editable state")

    # 4. Validate Policy (Category check)
    if not is_photo_permitted(incident.category, center_policy_other_enabled=True):
        raise ValidationFailedError("Photos are not permitted for this incident category", [])

    # 5. Validate Limits
    count = await evidence_repo.count_by_incident(session, incident_id)
    if count >= 5:
        raise ValidationFailedError("Maximum evidence limit of 5 reached", [])

    # Create evidence record in DB
    # Generate unique storage URI for staging
    evidence_uuid = uuid.uuid4()
    storage_uri = f"staging/{incident_id}/{evidence_uuid}"
    
    evidence = await evidence_repo.create_evidence(
        session=session,
        incident_id=incident_id,
        storage_object_uri=storage_uri,
        media_type=media_type,
        byte_size=byte_size,
        capture_user_id=user.id,
        capture_device_id=device_id,
        upload_status="pending",
    )

    # Generate Signed URL
    # Assuming intent is valid for 15 minutes
    upload_url = storage.generate_signed_upload_url(
        bucket="evidence-staging",
        object_path=storage_uri,
        content_type=media_type,
        max_size=byte_size,
    )

    return {
        "evidence_id": str(evidence.id),
        "upload_url": upload_url,
        "expires_in": 900,  # 15 minutes
    }


async def finalize_evidence(
    session: AsyncSession,
    user: User,
    device_id: uuid.UUID,
    incident_id: uuid.UUID,
    evidence_id: uuid.UUID,
    client_sha256: str,
) -> dict[str, Any]:
    """
    Finalize an evidence upload, verifying hash and moving it to retention storage.
    """
    evidence = await evidence_repo.get_evidence(session, evidence_id, incident_id)
    if not evidence:
        raise EntityNotFoundError("Evidence not found")

    # 1. Validate session matches capture origin
    if evidence.capture_user_id != user.id or evidence.capture_device_id != device_id:
        raise UnauthorizedError("Session does not match capture origin")

    # 2. Verify hash
    try:
        server_sha256 = storage.verify_object_hash("evidence-staging", evidence.storage_object_uri)
    except FileNotFoundError:
        raise ValidationFailedError("Uploaded file not found in staging", [])

    if server_sha256 != client_sha256:
        await evidence_repo.update_evidence_status(session, evidence_id, "failed")
        raise ValidationFailedError("SHA-256 hash mismatch", [])

    # 3. Move object to retention bucket
    final_uri = f"finalized/{incident_id}/{evidence_id}"
    storage.move_object(
        src_bucket="evidence-staging",
        src_path=evidence.storage_object_uri,
        dest_bucket="evidence-retention",
        dest_path=final_uri,
    )

    # 4. Update evidence record
    await evidence_repo.update_evidence_status(session, evidence_id, "ready", sha256=client_sha256)
    evidence.storage_object_uri = final_uri
    await session.flush()

    # 5. Write audit event
    await record_audit_event(
        session=session,
        center_id=user.center_id,
        action="evidence_finalized",
        correlation_id="",  # Usually passed from request, empty for now
        actor_user_id=user.id,
        incident_id=incident_id,
        metadata={"evidence_id": str(evidence_id)}
    )

    return {
        "evidence_id": str(evidence_id),
        "status": "ready"
    }
