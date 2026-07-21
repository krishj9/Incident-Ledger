"""
Review service — director review workflow for incident reports.

Implements:
  - get_review_queue: list submitted/under_review incidents with elapsed time and escalation state
  - acknowledge_review: transition submitted → under_review
  - create_director_edit: create director_edit version (grammar/spelling/formatting/neutrality/clarity only)
  - request_changes: transition to changes_requested
  - change_severity: update current_severity (staff_selected_severity preserved)
  - approve: freeze approved version, emit guardian notification outbox event
  - create_addendum: create addendum version after approval

Constraint: Director minor edits MUST be limited to grammar, spelling, formatting, neutrality,
or clarity corrections only. Factual changes require staff to update via request_changes,
or an addendum after approval. This constraint is documented and enforced by requiring
edit_reason but cannot be programmatically verified — compliance auditors review the diff.

Architecture rules (architecture.md):
  - API owns authorization, business transitions, versioning, and audit writes.
  - Outbox events are inserted in the SAME transaction as the triggering action.
  - Never auto-apply narrative changes; always create a new immutable version.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IncidentStatus, SeverityLevel, VersionKind
from app.domain.state_machine import (
    CMD_ACK_REVIEW,
    CMD_APPROVE,
    CMD_CREATE_ADDENDUM,
    CMD_REQ_CHANGES,
    transition,
    InvalidTransition,
)
from app.models.outbox import OutboxEvent
from app.models.report_versions import ReportVersion
from app.models.users import User
from app.repositories.audit import record_audit_event
from app.repositories.incidents import get_incident_with_etag, get_review_queue as repo_get_review_queue
from app.repositories.outbox import insert_outbox_event
from app.repositories.report_versions import create_version
from app.services import guardian_service
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import InvalidStateError, UnauthorizedError, ValidationFailedError

logger = structlog.get_logger(__name__)

_DIRECTOR_ROLES = {"director", "backup_director", "regional_admin", "compliance_reviewer"}
_DIRECTOR_ONLY = {"director", "compliance_reviewer"}


def _require_role(user: User, allowed: set[str], action: str) -> None:
    if user.role.value not in allowed:
        raise UnauthorizedError(f"Role '{user.role.value}' is not authorized for {action}")


def _require_reviewer_role_for_incident(user: User, incident: Any, action: str, allowed: set[str]) -> None:
    if incident.restricted:
        _require_role(user, {"compliance_reviewer"}, action)
    else:
        _require_role(user, allowed, action)


async def _get_incident_or_raise(
    session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID
) -> Any:
    result = await get_incident_with_etag(session, incident_id, center_id)
    if not result:
        raise EntityNotFoundError("Incident not found")
    incident, _ = result
    return incident


async def get_review_queue(
    session: AsyncSession,
    user: User,
) -> list[dict[str, Any]]:
    """Returns submitted/under_review incidents with elapsed time and escalation state."""
    _require_role(user, _DIRECTOR_ROLES, "get_review_queue")
    return await repo_get_review_queue(session, user.center_id)


async def acknowledge_review(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    correlation_id: str,
) -> Any:
    """Transition incident from submitted → under_review. Director/backup/regional only."""
    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    _require_reviewer_role_for_incident(user, incident, "acknowledge_review", _DIRECTOR_ROLES)

    current = IncidentStatus(incident.status.value)
    try:
        new_status = transition(current, CMD_ACK_REVIEW, user.role.value)
    except InvalidTransition as e:
        raise InvalidStateError(str(e)) from e

    from app.models.enums import IncidentStatus as ModelStatus
    incident.status = ModelStatus(new_status.value)
    incident.assigned_director_id = user.id

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="review_acknowledge",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
    )
    await session.flush()
    return incident


async def create_director_edit(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    rendered_narrative: str,
    edit_reason: str,
    correlation_id: str,
) -> ReportVersion:
    """
    Create a director_edit version.

    CONSTRAINT: Edits must be grammar, spelling, formatting, neutrality, or clarity only.
    Factual corrections require staff changes (via request_changes) or a post-approval addendum.
    edit_reason is REQUIRED — 422 without it.
    original_staff_notes is preserved verbatim from the parent version.
    """
    if not edit_reason or not edit_reason.strip():
        raise ValidationFailedError("edit_reason is required for director edits", [])

    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    _require_reviewer_role_for_incident(user, incident, "create_director_edit", _DIRECTOR_ONLY)
    current = IncidentStatus(incident.status.value)
    if current != IncidentStatus.under_review:
        raise InvalidStateError(f"Director edits only allowed when status is 'under_review'; current: {current.value}")

    # Fetch current version for parent linkage and to copy original_staff_notes verbatim
    parent_version: ReportVersion | None = None
    if incident.current_version_id:
        res = await session.execute(
            select(ReportVersion).where(ReportVersion.id == incident.current_version_id)
        )
        parent_version = res.scalar_one_or_none()

    if not parent_version:
        raise InvalidStateError("No existing version found; cannot create director edit")

    # Preserve original_staff_notes verbatim from the parent (staff submission)
    original_staff_notes = parent_version.original_staff_notes

    # Build structured snapshot inheriting parent's snapshot + edit metadata
    structured_snapshot = dict(parent_version.structured_snapshot)
    structured_snapshot["director_edit_reason"] = edit_reason
    structured_snapshot["director_edit_at"] = datetime.now(UTC).isoformat()
    structured_snapshot["editor_user_id"] = str(user.id)

    version = await create_version(
        session,
        incident_id=incident.id,
        version_kind=VersionKind.director_edit,
        created_by=user.id,
        parent_version_id=parent_version.id,
        original_staff_notes=original_staff_notes,
        rendered_narrative=rendered_narrative,
        structured_snapshot=structured_snapshot,
        edit_reason=edit_reason,
    )
    incident.current_version_id = version.id

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="director_edit",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        report_version_id=version.id,
        metadata={"edit_reason": edit_reason},
    )
    await session.flush()
    return version


async def request_changes(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    reason: str,
    correlation_id: str,
) -> Any:
    """Transition incident to changes_requested. Director only."""
    if not reason or not reason.strip():
        raise ValidationFailedError("reason is required when requesting changes", [])

    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    _require_reviewer_role_for_incident(user, incident, "request_changes", _DIRECTOR_ONLY)
    current = IncidentStatus(incident.status.value)
    try:
        new_status = transition(current, CMD_REQ_CHANGES, user.role.value)
    except InvalidTransition as e:
        raise InvalidStateError(str(e)) from e

    from app.models.enums import IncidentStatus as ModelStatus
    incident.status = ModelStatus(new_status.value)

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="request_changes",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        metadata={"reason": reason},
    )
    await session.flush()
    return incident


async def change_severity(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    new_severity: str,
    reason: str,
    correlation_id: str,
) -> Any:
    """
    Update current_severity. staff_selected_severity is preserved (never overwritten).
    Director only; reason is required.
    """
    if not reason or not reason.strip():
        raise ValidationFailedError("reason is required when changing severity", [])

    try:
        _ = SeverityLevel(new_severity)
    except ValueError:
        raise ValidationFailedError(f"Invalid severity level: {new_severity}", [])

    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    _require_reviewer_role_for_incident(user, incident, "change_severity", _DIRECTOR_ONLY)
    old_severity = incident.current_severity

    # Preserve staff_selected_severity — only update current_severity
    incident.current_severity = new_severity  # noqa: assignment to enum field

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="severity_change",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        metadata={
            "old_severity": str(old_severity),
            "new_severity": new_severity,
            "reason": reason,
            "staff_selected_severity": str(incident.staff_selected_severity),
        },
    )
    await session.flush()
    return incident


async def approve(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    correlation_id: str,
) -> ReportVersion:
    """
    Transition incident to guardian_ack_pending (or approved for restricted).
    Creates a frozen approved version. Emits guardian_notification outbox event
    if the incident is not restricted.
    """
    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    _require_reviewer_role_for_incident(user, incident, "approve", _DIRECTOR_ONLY)
    current = IncidentStatus(incident.status.value)
    try:
        new_status = transition(current, CMD_APPROVE, user.role.value)
    except InvalidTransition as e:
        raise InvalidStateError(str(e)) from e

    # Fetch current version to create approved snapshot from
    parent_version: ReportVersion | None = None
    if incident.current_version_id:
        res = await session.execute(
            select(ReportVersion).where(ReportVersion.id == incident.current_version_id)
        )
        parent_version = res.scalar_one_or_none()

    if not parent_version:
        raise InvalidStateError("Cannot approve incident without an existing version")

    # Build approved version — immutable frozen snapshot
    structured_snapshot = dict(parent_version.structured_snapshot)
    structured_snapshot["approved_at"] = datetime.now(UTC).isoformat()
    structured_snapshot["approver_user_id"] = str(user.id)

    version = await create_version(
        session,
        incident_id=incident.id,
        version_kind=VersionKind.approved,
        created_by=user.id,
        parent_version_id=parent_version.id,
        original_staff_notes=parent_version.original_staff_notes,
        rendered_narrative=parent_version.rendered_narrative,
        structured_snapshot=structured_snapshot,
    )
    incident.current_version_id = version.id

    from app.models.enums import IncidentStatus as ModelStatus
    incident.status = ModelStatus(new_status.value)
    incident.approved_at = datetime.now(UTC)

    # Generate guardian packets for all involved children
    await guardian_service.generate_packets_on_approval(session, user, incident, version.id)

    # Outbox event for guardian notification — skip if restricted
    if not incident.restricted:
        await insert_outbox_event(
            session,
            center_id=incident.center_id,
            event_type="guardian_notification",
            payload={
                "incident_id": str(incident.id),
                "approved_version_id": str(version.id),
            },
            idempotency_key=f"guardian-notify-{incident.id}-{version.id}",
        )

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="approve",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        report_version_id=version.id,
    )
    await session.flush()
    return version


async def create_addendum(
    session: AsyncSession,
    user: User,
    incident_id: uuid.UUID,
    content: str,
    correlation_id: str,
) -> ReportVersion:
    """
    Create an addendum version after approval.
    The original approved version remains immutable — addendum is a new linked version.
    Only valid after incident is approved or later.
    """
    allowed_roles = {"staff", "director", "backup_director", "regional_admin"}
    _require_role(user, allowed_roles, "create_addendum")

    if not content or not content.strip():
        raise ValidationFailedError("content is required for an addendum", [])

    incident = await _get_incident_or_raise(session, incident_id, user.center_id)
    current = IncidentStatus(incident.status.value)

    # Validate addendum is valid from current state
    try:
        transition(current, CMD_CREATE_ADDENDUM, user.role.value)
    except InvalidTransition as e:
        raise InvalidStateError(str(e)) from e

    # Find the approved version to use as parent
    res = await session.execute(
        select(ReportVersion)
        .where(
            ReportVersion.incident_id == incident.id,
            ReportVersion.version_kind == "approved",
        )
        .order_by(ReportVersion.version_number.desc())
        .limit(1)
    )
    approved_version = res.scalar_one_or_none()

    if not approved_version:
        raise InvalidStateError("No approved version found to create addendum against")

    structured_snapshot = {
        "addendum_content": content,
        "addendum_at": datetime.now(UTC).isoformat(),
        "addendum_author_user_id": str(user.id),
        "parent_approved_version_id": str(approved_version.id),
    }

    version = await create_version(
        session,
        incident_id=incident.id,
        version_kind=VersionKind.addendum,
        created_by=user.id,
        parent_version_id=approved_version.id,
        original_staff_notes=approved_version.original_staff_notes,
        rendered_narrative=content,
        structured_snapshot=structured_snapshot,
        edit_reason="Addendum",
    )

    await record_audit_event(
        session,
        center_id=user.center_id,
        action="addendum_create",
        correlation_id=correlation_id,
        actor_user_id=user.id,
        incident_id=incident.id,
        report_version_id=version.id,
    )
    await session.flush()
    return version
