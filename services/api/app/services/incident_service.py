import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.incidents import SubmitResponse
from app.domain.enums import IncidentStatus, VersionKind
from app.domain.policies import is_restricted_category, requires_immediate_alert
from app.domain.rules import validate_submission_requirements
from app.domain.state_machine import CMD_SUBMIT, CMD_UPDATE_SUBMIT, transition
from app.models.outbox import OutboxEvent
from app.models.users import User
from app.repositories.audit import record_audit_event
from app.repositories.incidents import create_incident, get_incident, get_incident_with_etag, update_draft as repo_update_draft
from app.repositories.report_versions import create_version
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import InvalidStateError, UnauthorizedError, ValidationFailedError


async def create_draft(
    session: AsyncSession,
    user: User,
    center_id: uuid.UUID,
    category: str,
    severity: str,
    children: list[dict[str, Any]],
    correlation_id: str,
    idempotency_key: str,
    **fields: Any
) -> Any:
    """Create a new drafted incident."""
    restricted = is_restricted_category(category)

    kwargs = fields.copy()
    if restricted:
        kwargs["notification_decision"] = "blocked"

    incident = await create_incident(
        session,
        center_id=center_id,
        created_by_user_id=user.id,
        status=IncidentStatus.draft,
        category=category,
        staff_selected_severity=severity,
        current_severity=severity,
        restricted=restricted,
        children=children,
        **kwargs
    )

    await record_audit_event(
        session,
        center_id=center_id,
        action="incident_create",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        metadata={"idempotency_key": idempotency_key}
    )

    return incident


async def get_incident_detail(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID
) -> dict[str, Any]:
    """
    Get incident detail with version history.
    Enforces RBAC in the service layer.
    """
    from app.models.enums import UserRole
    from app.models.report_versions import ReportVersion
    from sqlalchemy import select

    incident = await get_incident(session, incident_id, user.center_id)
    if not incident:
        raise EntityNotFoundError("Incident not found")

    # Authorization logic
    can_view = False
    if user.role == UserRole.staff:
        if incident.created_by_user_id == user.id or incident.submitted_by_user_id == user.id:
            can_view = True
    elif user.role in (UserRole.director, UserRole.backup_director, UserRole.regional_admin):
        can_view = True
    elif user.role == UserRole.compliance_reviewer:
        can_view = True
    elif user.role == UserRole.operations_support:
        if not incident.restricted:
            can_view = True

    if not can_view:
        raise EntityNotFoundError("Incident not found") # non-disclosing

    # Fetch versions
    stmt = select(ReportVersion).where(ReportVersion.incident_id == incident.id).order_by(ReportVersion.version_number.asc())
    versions = (await session.execute(stmt)).scalars().all()
    
    # ETag
    etag_result = await get_incident_with_etag(session, incident.id, user.center_id)
    etag = etag_result[1] if etag_result else ""

    # Dump incident data
    from app.api.schemas.incidents import IncidentResponse
    response_data = IncidentResponse.model_validate(incident).model_dump()
    response_data["etag"] = etag
    
    # Redact narrative for operations_support
    if user.role == UserRole.operations_support:
        response_data["original_factual_notes"] = "[REDACTED]"
        response_data["actions_taken"] = "[REDACTED]"
        # No evidence array to redact here, but if there was, we'd clear it.

    response_data["versions"] = [
        {
            "id": v.id,
            "version_number": v.version_number,
            "version_kind": v.version_kind,
            "created_by_user_id": v.created_by_user_id,
            "created_at": v.created_at,
        }
        for v in versions
    ]
    return response_data


async def update_draft(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    etag: str,
    correlation_id: str,
    idempotency_key: str,
    **changes: Any
) -> Any:
    """Optimistic update of a draft incident."""
    result = await get_incident_with_etag(session, incident_id, user.center_id)
    if not result:
        raise EntityNotFoundError("Incident not found")
        
    incident, _ = result

    # Check authorization
    if incident.created_by_user_id != user.id and incident.submitted_by_user_id != user.id:
        raise UnauthorizedError("Not authorized to edit this incident")

    # Check state
    if IncidentStatus(incident.status.value) not in (IncidentStatus.draft, IncidentStatus.changes_requested):
        raise InvalidStateError("Incident is not in an editable state")

    if "category" in changes:
        changes["restricted"] = is_restricted_category(changes["category"])
        if changes["restricted"]:
            changes["notification_decision"] = "blocked"
        
    if "severity" in changes:
        changes["staff_selected_severity"] = changes["severity"]
        changes["current_severity"] = changes["severity"]

    updated_incident = await repo_update_draft(
        session, incident_id, user.center_id, etag, **changes
    )

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="incident_edit",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        metadata={"idempotency_key": idempotency_key}
    )

    return updated_incident


async def submit(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    attestation: dict[str, Any],
    device_info: dict[str, Any],
    correlation_id: str,
    idempotency_key: str,
) -> SubmitResponse:
    """Submit a draft incident for review."""
    result = await get_incident_with_etag(session, incident_id, user.center_id)
    if not result:
        raise EntityNotFoundError("Incident not found")
    
    incident, _ = result

    # Authorization
    if incident.created_by_user_id != user.id and incident.submitted_by_user_id != user.id:
        raise UnauthorizedError("Not authorized to submit this incident")

    # Domain validation rules
    # Reconstruct incident data as a dictionary for the domain validator
    incident_data = {
        "category": incident.category,
        "severity": incident.current_severity,
        "event_at": incident.event_at,
        "event_time_precision": incident.event_time_precision,
        "location": incident.location,
        "original_factual_notes": incident.original_factual_notes,
        "actions_taken": incident.actions_taken,
        "witnesses_known": incident.witnesses_known,
        "staff_attestation": attestation.get("accurate_to_best_of_knowledge", False),
    }
    
    # Wait, the incident relation for children might not be loaded.
    from app.models.incidents import IncidentChild
    from sqlalchemy import select
    children = (await session.execute(
        select(IncidentChild).where(IncidentChild.incident_id == incident.id)
    )).scalars().all()
    
    incident_data["children"] = [{"child_id": c.child_id, "role": c.involvement_role} for c in children]
    errors = validate_submission_requirements(incident_data)
    if errors:
        raise ValidationFailedError("Submission requirements not met", errors)

    # State transition
    domain_status = IncidentStatus(incident.status.value)
    cmd = CMD_SUBMIT if domain_status == IncidentStatus.draft else CMD_UPDATE_SUBMIT
    try:
        new_status = transition(domain_status, cmd, user.role)
    except Exception as e:
        raise InvalidStateError(str(e)) from e

    from app.models.enums import IncidentStatus as ModelIncidentStatus
    incident.status = ModelIncidentStatus(new_status.value)
    incident.submitted_at = datetime.now(UTC)
    incident.submitted_by_user_id = user.id

    # Create report version
    structured_snapshot = incident_data.copy()
    structured_snapshot["staff_attestation_timestamp"] = attestation.get("confirmed_at")
    structured_snapshot["submitted_from_device_id"] = str(device_info.get("device_id"))
    
    # Needs a JSON serializable dict (e.g. serialize datetime)
    if structured_snapshot["event_at"]:
        structured_snapshot["event_at"] = structured_snapshot["event_at"].isoformat()
    if structured_snapshot["staff_attestation_timestamp"]:
        if isinstance(structured_snapshot["staff_attestation_timestamp"], datetime):
            structured_snapshot["staff_attestation_timestamp"] = structured_snapshot["staff_attestation_timestamp"].isoformat()
    
    for c in structured_snapshot["children"]:
        c["child_id"] = str(c["child_id"])

    version = await create_version(
        session,
        incident_id=incident.id,
        version_kind=VersionKind.staff_submission,
        created_by=user.id,
        parent_version_id=incident.current_version_id,
        original_staff_notes=incident.original_factual_notes,
        rendered_narrative=incident.original_factual_notes,  # Same as notes for staff_submission
        structured_snapshot=structured_snapshot,
    )
    
    incident.current_version_id = version.id

    # Outbox event for immediate director alert
    if requires_immediate_alert(incident.current_severity):
        outbox = OutboxEvent(
            center_id=incident.center_id,
            event_type="director_alert",
            payload={
                "incident_id": str(incident.id),
                "severity": incident.current_severity,
                "version_id": str(version.id),
            },
            idempotency_key=f"alert-{incident.id}-{version.id}"
        )
        session.add(outbox)

    # Escalation check events for critical severity (30min backup, 60min regional)
    from app.domain.enums import SeverityLevel
    if IncidentStatus(incident.status.value) in (IncidentStatus.submitted,):
        severity_val = str(incident.current_severity.value) if hasattr(incident.current_severity, "value") else str(incident.current_severity)
        if severity_val == SeverityLevel.critical:
            for stage in ("backup", "regional"):
                escalation_outbox = OutboxEvent(
                    center_id=incident.center_id,
                    event_type="escalation_check",
                    payload={
                        "incident_id": str(incident.id),
                        "escalation_stage": stage,
                        "submitted_at": incident.submitted_at.isoformat() if incident.submitted_at else None,
                    },
                    idempotency_key=f"escalation-{incident.id}-{stage}"
                )
                session.add(escalation_outbox)

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="incident_submit",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        report_version_id=version.id,
        metadata={"idempotency_key": idempotency_key, "device_id": str(device_info.get("device_id"))}
    )

    await session.flush()

    return SubmitResponse(
        incident_id=incident.id,
        status=incident.status,
        server_received_at=incident.submitted_at,
        sync_state="synchronized",
    )
