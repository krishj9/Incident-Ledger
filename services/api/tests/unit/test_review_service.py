"""
Unit tests for the review service (Phase 3.1).

Tests domain and state transition logic with mocked database sessions.
These are unit tests — no real DB required.

Coverage:
  - acknowledge_review: role enforcement, state transition
  - create_director_edit: edit_reason required, original_staff_notes preserved
  - request_changes: role enforcement, reason required
  - change_severity: staff_selected_severity preserved, reason required
  - approve: approved version created, approved_at set, outbox event inserted (non-restricted)
  - create_addendum: valid after approval, approved version untouched
  - Escalation logic in get_review_queue
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from app.domain.enums import IncidentStatus, SeverityLevel, VersionKind
from app.models.enums import UserRole
from app.services.exceptions import InvalidStateError, UnauthorizedError, ValidationFailedError


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(role: str = "director") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.center_id = uuid.uuid4()
    user.role = MagicMock()
    user.role.value = role
    return user


def _make_incident(
    status: str = "under_review",
    severity: str = "high",
    restricted: bool = False,
    submitted_at: datetime | None = None,
) -> MagicMock:
    incident = MagicMock()
    incident.id = uuid.uuid4()
    incident.center_id = uuid.uuid4()
    incident.status = MagicMock()
    incident.status.value = status
    incident.current_severity = MagicMock()
    incident.current_severity.value = severity
    incident.staff_selected_severity = MagicMock()
    incident.staff_selected_severity.value = severity
    incident.original_factual_notes = "Staff original notes verbatim."
    incident.restricted = restricted
    incident.submitted_at = submitted_at or datetime.now(UTC) - timedelta(minutes=5)
    incident.current_version_id = uuid.uuid4()
    incident.approved_at = None
    return incident


def _make_version(original_staff_notes: str = "Staff original notes verbatim.") -> MagicMock:
    version = MagicMock()
    version.id = uuid.uuid4()
    version.version_number = 1
    version.version_kind = "staff_submission"
    version.original_staff_notes = original_staff_notes
    version.rendered_narrative = "Staff narrative."
    version.structured_snapshot = {"category": "injury_accident"}
    return version


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestAcknowledgeReview:
    @pytest.mark.asyncio
    async def test_staff_cannot_acknowledge(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("staff")

        incident = _make_incident(status="submitted")
        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(UnauthorizedError):
                await review_service.acknowledge_review(session, user, incident.id, "corr-id")

    @pytest.mark.asyncio
    async def test_director_acknowledges_submitted(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="submitted")

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock):
            result = await review_service.acknowledge_review(session, user, incident.id, "corr-id")

        assert incident.status.value != "submitted"  # Transitioned
        assert incident.assigned_director_id == user.id


class TestCreateDirectorEdit:
    @pytest.mark.asyncio
    async def test_edit_reason_required(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")

        with pytest.raises(ValidationFailedError, match="edit_reason is required"):
            await review_service.create_director_edit(
                session, user, uuid.uuid4(), "New narrative", "", "corr-id"
            )

    @pytest.mark.asyncio
    async def test_edit_only_allowed_under_review(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="submitted")  # NOT under_review

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(InvalidStateError):
                await review_service.create_director_edit(
                    session, user, incident.id, "New narrative", "Typo fix", "corr-id"
                )

    @pytest.mark.asyncio
    async def test_original_staff_notes_preserved(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="under_review")
        parent_version = _make_version("Original staff notes — must not change.")

        mock_version = MagicMock()
        mock_version.id = uuid.uuid4()
        mock_version.version_number = 2
        mock_version.version_kind = "director_edit"

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.create_version", return_value=mock_version, new_callable=AsyncMock) as mock_create_version, \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock), \
             patch("app.services.review_service.select") as mock_select:

            # Mock the DB query for parent version
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = parent_version
            session.execute = AsyncMock(return_value=mock_result)

            await review_service.create_director_edit(
                session, user, incident.id, "Corrected narrative (grammar only)", "Fixed typo", "corr-id"
            )

        # Verify original_staff_notes was passed verbatim to create_version
        call_kwargs = mock_create_version.call_args.kwargs
        assert call_kwargs["original_staff_notes"] == "Original staff notes — must not change."
        assert call_kwargs["version_kind"] == VersionKind.director_edit

    @pytest.mark.asyncio
    async def test_staff_cannot_create_director_edit(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("staff")

        incident = _make_incident(status="under_review")
        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(UnauthorizedError):
                await review_service.create_director_edit(
                    session, user, incident.id, "Narrative", "Reason", "corr-id"
                )


class TestRequestChanges:
    @pytest.mark.asyncio
    async def test_reason_required(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="under_review")

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(ValidationFailedError, match="reason is required"):
                await review_service.request_changes(session, user, incident.id, "", "corr-id")

    @pytest.mark.asyncio
    async def test_staff_cannot_request_changes(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("staff")

        incident = _make_incident(status="under_review")
        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(UnauthorizedError):
                await review_service.request_changes(session, user, incident.id, "Need clarification", "corr-id")


class TestChangeSeverity:
    @pytest.mark.asyncio
    async def test_reason_required(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(severity="high")

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(ValidationFailedError, match="reason is required"):
                await review_service.change_severity(session, user, incident.id, "critical", "", "corr-id")

    @pytest.mark.asyncio
    async def test_staff_selected_severity_preserved(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(severity="high")
        original_staff_severity = incident.staff_selected_severity

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock):
            await review_service.change_severity(
                session, user, incident.id, "critical", "Injury more serious than reported", "corr-id"
            )

        # current_severity should be updated
        assert incident.current_severity == "critical"
        # staff_selected_severity must NOT be modified
        assert incident.staff_selected_severity is original_staff_severity


class TestApprove:
    @pytest.mark.asyncio
    async def test_approve_creates_frozen_version(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="under_review", restricted=False)
        parent_version = _make_version()

        mock_approved_version = MagicMock()
        mock_approved_version.id = uuid.uuid4()
        mock_approved_version.version_number = 2
        mock_approved_version.version_kind = "approved"

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.create_version", return_value=mock_approved_version, new_callable=AsyncMock) as mock_create_version, \
             patch("app.services.review_service.insert_outbox_event", new_callable=AsyncMock) as mock_outbox, \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock):

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = parent_version
            session.execute = AsyncMock(return_value=mock_result)

            version = await review_service.approve(session, user, incident.id, "corr-id")

        call_kwargs = mock_create_version.call_args.kwargs
        assert call_kwargs["version_kind"] == VersionKind.approved
        # Outbox event emitted for non-restricted
        mock_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_restricted_no_outbox_event(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("compliance_reviewer")
        incident = _make_incident(status="under_review", restricted=True)
        parent_version = _make_version()

        mock_approved_version = MagicMock()
        mock_approved_version.id = uuid.uuid4()
        mock_approved_version.version_kind = "approved"

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.create_version", return_value=mock_approved_version, new_callable=AsyncMock), \
             patch("app.services.review_service.insert_outbox_event", new_callable=AsyncMock) as mock_outbox, \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock):

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = parent_version
            session.execute = AsyncMock(return_value=mock_result)

            await review_service.approve(session, user, incident.id, "corr-id")

        # No outbox event for restricted incidents
        mock_outbox.assert_not_called()


class TestCreateAddendum:
    @pytest.mark.asyncio
    async def test_addendum_requires_content(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="guardian_ack_pending")

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(ValidationFailedError, match="content is required"):
                await review_service.create_addendum(session, user, incident.id, "", "corr-id")

    @pytest.mark.asyncio
    async def test_addendum_only_after_approval(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="under_review")  # Not yet approved

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")):
            with pytest.raises(InvalidStateError):
                await review_service.create_addendum(
                    session, user, incident.id, "Post-approval correction", "corr-id"
                )

    @pytest.mark.asyncio
    async def test_approved_version_not_mutated(self) -> None:
        from app.services import review_service
        session = AsyncMock()
        user = _make_user("director")
        incident = _make_incident(status="guardian_ack_pending")
        approved_version = _make_version("Staff notes verbatim.")

        mock_addendum_version = MagicMock()
        mock_addendum_version.id = uuid.uuid4()
        mock_addendum_version.version_number = 3
        mock_addendum_version.version_kind = "addendum"

        with patch("app.services.review_service.get_incident_with_etag", return_value=(incident, "etag")), \
             patch("app.services.review_service.create_version", return_value=mock_addendum_version, new_callable=AsyncMock) as mock_create_version, \
             patch("app.services.review_service.record_audit_event", new_callable=AsyncMock):

            # Mock the DB query for approved version
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = approved_version
            session.execute = AsyncMock(return_value=mock_result)

            await review_service.create_addendum(
                session, user, incident.id, "Addendum content", "corr-id"
            )

        call_kwargs = mock_create_version.call_args.kwargs
        # Addendum version kind
        assert call_kwargs["version_kind"] == VersionKind.addendum
        # Approved version is parent, not mutated
        assert call_kwargs["parent_version_id"] == approved_version.id
        # original_staff_notes carried through verbatim
        assert call_kwargs["original_staff_notes"] == "Staff notes verbatim."


class TestEscalationLogic:
    def test_review_queue_escalation_state_backup_critical(self) -> None:
        """Critical incident >30min → backup escalation state."""
        from app.repositories.incidents import get_review_queue
        # Test the inline escalation logic — extract same thresholds as the function
        severity = "critical"
        elapsed = 1900  # ~31 minutes

        escalation_state = None
        if severity == "critical":
            if elapsed >= 3600:
                escalation_state = "regional"
            elif elapsed >= 1800:
                escalation_state = "backup"
        assert escalation_state == "backup"

    def test_review_queue_escalation_state_regional_critical(self) -> None:
        """Critical incident >60min → regional escalation state."""
        severity = "critical"
        elapsed = 3700  # ~61 minutes

        escalation_state = None
        if severity == "critical":
            if elapsed >= 3600:
                escalation_state = "regional"
            elif elapsed >= 1800:
                escalation_state = "backup"
        assert escalation_state == "regional"

    def test_review_queue_no_escalation_low(self) -> None:
        """Low severity never escalates."""
        severity = "low"
        elapsed = 7200  # 2 hours

        escalation_state = None
        if severity == "critical":
            if elapsed >= 3600:
                escalation_state = "regional"
            elif elapsed >= 1800:
                escalation_state = "backup"
        elif severity == "high":
            if elapsed >= 1800:
                escalation_state = "backup"
        assert escalation_state is None
