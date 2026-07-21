from enum import Enum


class IncidentCategory(str, Enum):
    injury_accident = "injury_accident"
    illness_medical = "illness_medical"
    behavioral = "behavioral"
    suspected_abuse_neglect = "suspected_abuse_neglect"
    missing_child = "missing_child"
    medication_error = "medication_error"
    property_damage = "property_damage"
    other = "other"


class SeverityLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    changes_requested = "changes_requested"
    under_review = "under_review"
    approved = "approved"
    guardian_ack_pending = "guardian_ack_pending"
    acknowledged = "acknowledged"
    ack_unreachable = "ack_unreachable"
    closed = "closed"
    restricted_review = "restricted_review"


class VersionKind(str, Enum):
    staff_submission = "staff_submission"
    director_edit = "director_edit"
    approved = "approved"
    addendum = "addendum"


class InvolvementRole(str, Enum):
    primary_affected = "primary_affected"
    involved = "involved"
    witness = "witness"


class TimePrecision(str, Enum):
    exact = "exact"
    estimated = "estimated"


class EvidenceUploadStatus(str, Enum):
    pending = "pending"
    uploading = "uploading"
    ready = "ready"
    failed = "failed"
    unavailable = "unavailable"


class AcknowledgementMethod(str, Enum):
    in_person = "in_person"
    email_link = "email_link"


class AcknowledgementOutcome(str, Enum):
    acknowledged = "acknowledged"
    disagreed = "disagreed"
