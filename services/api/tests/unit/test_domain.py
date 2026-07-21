from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.enums import IncidentCategory, IncidentStatus, InvolvementRole, SeverityLevel
from app.domain.policies import (
    is_photo_permitted,
    is_restricted_category,
    requires_escalation,
    requires_immediate_alert,
)
from app.domain.rules import validate_submission_requirements, validate_unreachable_closure
from app.domain.state_machine import (
    CMD_ACK_GUARDIAN,
    CMD_ACK_REVIEW,
    CMD_APPROVE,
    CMD_CLOSE,
    CMD_CLOSE_UNREACHABLE,
    CMD_CREATE_ADDENDUM,
    CMD_DISAGREE_GUARDIAN,
    CMD_REQ_CHANGES,
    CMD_SUBMIT,
    CMD_UPDATE_SUBMIT,
    InvalidTransition,
    transition,
)


def test_state_machine_valid_transitions():
    # Submit
    assert transition(IncidentStatus.draft, CMD_SUBMIT, "staff") == IncidentStatus.submitted

    # Acknowledge review
    for role in ["director", "backup_director", "regional_admin"]:
        assert transition(IncidentStatus.submitted, CMD_ACK_REVIEW, role) == IncidentStatus.under_review

    # Request changes
    for role in ["director", "backup_director", "regional_admin", "compliance_reviewer"]:
        assert transition(IncidentStatus.submitted, CMD_REQ_CHANGES, role) == IncidentStatus.changes_requested
        assert transition(IncidentStatus.under_review, CMD_REQ_CHANGES, role) == IncidentStatus.changes_requested

    # Update and submit
    assert transition(IncidentStatus.changes_requested, CMD_UPDATE_SUBMIT, "staff") == IncidentStatus.submitted

    # Approve
    assert transition(IncidentStatus.under_review, CMD_APPROVE, "director") == IncidentStatus.guardian_ack_pending

    # Guardian Acknowledge/Disagree
    for role in ["guardian", "staff"]:
        assert transition(IncidentStatus.guardian_ack_pending, CMD_ACK_GUARDIAN, role) == IncidentStatus.acknowledged
        assert transition(IncidentStatus.guardian_ack_pending, CMD_DISAGREE_GUARDIAN, role) == IncidentStatus.acknowledged

    # Close Unreachable
    assert transition(IncidentStatus.guardian_ack_pending, CMD_CLOSE_UNREACHABLE, "director") == IncidentStatus.ack_unreachable

    # Close
    assert transition(IncidentStatus.acknowledged, CMD_CLOSE, "director") == IncidentStatus.closed
    assert transition(IncidentStatus.ack_unreachable, CMD_CLOSE, "system") == IncidentStatus.closed

    # Create Addendum
    for role in ["staff", "director"]:
        for status in [IncidentStatus.approved, IncidentStatus.acknowledged, IncidentStatus.ack_unreachable, IncidentStatus.closed]:
            assert transition(status, CMD_CREATE_ADDENDUM, role) == status


def test_state_machine_invalid_transitions():
    with pytest.raises(InvalidTransition):
        transition(IncidentStatus.draft, CMD_APPROVE, "director")
        
    with pytest.raises(InvalidTransition):
        transition(IncidentStatus.draft, CMD_SUBMIT, "guardian")

    with pytest.raises(InvalidTransition):
        transition(IncidentStatus.submitted, CMD_APPROVE, "director")

    with pytest.raises(InvalidTransition):
        transition(IncidentStatus.under_review, CMD_CREATE_ADDENDUM, "director")


def test_submission_requirements():
    valid_data = {
        "children": [{"role": InvolvementRole.primary_affected}],
        "category": IncidentCategory.injury_accident,
        "severity": SeverityLevel.low,
        "event_at": datetime.now(),
        "event_time_precision": "exact",
        "location": "Playground",
        "original_factual_notes": "A scraped knee.",
        "actions_taken": "Applied bandage.",
        "witnesses_known": False,
        "staff_attestation": True,
    }
    
    assert not validate_submission_requirements(valid_data)
    
    # Missing fields
    missing_data = valid_data.copy()
    missing_data.pop("location")
    assert "Missing required field: location" in validate_submission_requirements(missing_data)
    
    # Invalid boolean
    bad_bool_data = valid_data.copy()
    bad_bool_data["witnesses_known"] = "maybe"
    assert "witnesses_known must be explicitly true or false." in validate_submission_requirements(bad_bool_data)
    
    # Missing staff attestation
    no_attest_data = valid_data.copy()
    no_attest_data["staff_attestation"] = False
    assert "Staff attestation is required for submission." in validate_submission_requirements(no_attest_data)
    
    # No primary affected child
    no_primary_data = valid_data.copy()
    no_primary_data["children"] = [{"role": InvolvementRole.involved}]
    assert "At least one child must be designated as 'primary_affected'." in validate_submission_requirements(no_primary_data)


def test_photo_policy():
    assert is_photo_permitted(IncidentCategory.injury_accident)
    assert is_photo_permitted(IncidentCategory.property_damage)
    
    assert not is_photo_permitted(IncidentCategory.behavioral)
    assert not is_photo_permitted(IncidentCategory.suspected_abuse_neglect)
    
    assert not is_photo_permitted(IncidentCategory.other, center_policy_other_enabled=False)
    assert is_photo_permitted(IncidentCategory.other, center_policy_other_enabled=True)


def test_restricted_category():
    assert is_restricted_category(IncidentCategory.suspected_abuse_neglect)
    assert not is_restricted_category(IncidentCategory.behavioral)


def test_unreachable_closure():
    tz = "America/New_York"
    utc = ZoneInfo("UTC")
    
    base = datetime(2026, 7, 20, 10, 0, tzinfo=utc)
    
    # Less than 3 attempts
    assert not validate_unreachable_closure([base, base + timedelta(days=1)], tz)
    
    # 3 attempts, same day (in America/New_York)
    # base is 10:00 UTC = 06:00 EDT
    attempt2 = base + timedelta(hours=4) # 10:00 EDT
    attempt3 = base + timedelta(hours=8) # 14:00 EDT
    assert not validate_unreachable_closure([base, attempt2, attempt3], tz)
    
    # 3 attempts, across 2 dates
    attempt_next_day = base + timedelta(days=1, hours=2)
    assert validate_unreachable_closure([base, attempt2, attempt_next_day], tz)


def test_severity_alert_escalation():
    assert not requires_immediate_alert(SeverityLevel.low)
    assert not requires_immediate_alert(SeverityLevel.moderate)
    assert requires_immediate_alert(SeverityLevel.high)
    assert requires_immediate_alert(SeverityLevel.critical)
    
    assert not requires_escalation(SeverityLevel.high)
    assert requires_escalation(SeverityLevel.critical)
