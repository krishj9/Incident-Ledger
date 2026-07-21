from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.enums import InvolvementRole


def validate_submission_requirements(incident_data: dict[str, Any]) -> list[str]:
    """
    Validates if a drafted incident meets the requirements for submission.
    Returns a list of error messages for missing or invalid fields.
    """
    errors: list[str] = []

    # Children requirements
    children = incident_data.get("children", [])
    if not isinstance(children, list) or len(children) == 0:
        errors.append("At least one child must be involved.")
    else:
        has_primary = any(
            c.get("role") == InvolvementRole.primary_affected for c in children if isinstance(c, dict)
        )
        if not has_primary:
            errors.append("At least one child must be designated as 'primary_affected'.")

    # Required scalar fields
    required_fields = [
        "category",
        "severity",
        "event_at",
        "event_time_precision",
        "location",
        "original_factual_notes",
        "actions_taken",
    ]
    for field in required_fields:
        val = incident_data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing required field: {field}")

    # Explicit booleans
    witnesses_known = incident_data.get("witnesses_known")
    if not isinstance(witnesses_known, bool):
        errors.append("witnesses_known must be explicitly true or false.")

    staff_attestation = incident_data.get("staff_attestation")
    if staff_attestation is not True:
        errors.append("Staff attestation is required for submission.")

    return errors


def validate_unreachable_closure(contact_attempts: list[datetime], center_timezone: str) -> bool:
    """
    Validates if an incident can be closed as unreachable.
    Rule: ≥3 attempts across ≥2 calendar dates (using center timezone for date boundaries).
    """
    if len(contact_attempts) < 3:
        return False

    try:
        tz = ZoneInfo(center_timezone)
    except Exception:
        # Fallback to UTC if timezone is invalid
        tz = ZoneInfo("UTC")

    # Extract distinct local calendar dates
    unique_dates: set[str] = set()
    for attempt_dt in contact_attempts:
        local_dt = attempt_dt.astimezone(tz)
        unique_dates.add(local_dt.date().isoformat())

    return len(unique_dates) >= 2
