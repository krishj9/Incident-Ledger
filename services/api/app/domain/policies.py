from app.domain.enums import IncidentCategory, SeverityLevel


def is_restricted_category(category: IncidentCategory | str) -> bool:
    """Returns True if the category is suspected abuse/neglect."""
    return category == IncidentCategory.suspected_abuse_neglect


def is_photo_permitted(category: IncidentCategory | str, center_policy_other_enabled: bool = False) -> bool:
    """
    Checks if photos are permitted for the given category.
    Permitted only for: injury_accident, property_damage, and center-configured 'other'.
    """
    if category in (IncidentCategory.injury_accident, IncidentCategory.property_damage):
        return True
    if category == IncidentCategory.other and center_policy_other_enabled:
        return True
    return False


def requires_immediate_alert(severity: SeverityLevel | str) -> bool:
    """Returns True if severity is high or critical."""
    return severity in (SeverityLevel.high, SeverityLevel.critical)


def requires_escalation(severity: SeverityLevel | str) -> bool:
    """Returns True if severity is critical."""
    return severity == SeverityLevel.critical
