"""
ORM model registry — import all models so SQLAlchemy metadata is fully populated.

Alembic env.py imports Base.metadata from here to enable autogenerate.
Application code imports individual models directly from their modules.
"""

from app.models.base import Base  # noqa: F401
from app.models.enums import IncidentStatus, SeverityLevel, UserRole  # noqa: F401
from app.models.centers import Center  # noqa: F401
from app.models.users import User  # noqa: F401
from app.models.devices import Device  # noqa: F401
from app.models.children import Child, ChildGuardian, Guardian  # noqa: F401
from app.models.incidents import Incident, IncidentChild  # noqa: F401
from app.models.report_versions import ReportVersion  # noqa: F401
from app.models.evidence import EvidenceItem  # noqa: F401
from app.models.guardian_packets import GuardianPacket  # noqa: F401
from app.models.acknowledgements import Acknowledgement  # noqa: F401
from app.models.contact_attempts import ContactAttempt  # noqa: F401
from app.models.sync_operations import SyncOperation  # noqa: F401
from app.models.audit_events import AuditEvent  # noqa: F401
from app.models.outbox import (  # noqa: F401
    AssistantInteraction,
    CategoryResponse,
    EmailLinkToken,
    LegalHold,
    NotificationDelivery,
    OutboxEvent,
    ReportView,
    RetentionDisposal,
    ReviewAction,
)

__all__ = [
    "Base",
    "IncidentStatus",
    "SeverityLevel",
    "UserRole",
    "Center",
    "User",
    "Device",
    "Child",
    "Guardian",
    "ChildGuardian",
    "Incident",
    "IncidentChild",
    "ReportVersion",
    "EvidenceItem",
    "GuardianPacket",
    "Acknowledgement",
    "ContactAttempt",
    "SyncOperation",
    "AuditEvent",
    "CategoryResponse",
    "ReviewAction",
    "EmailLinkToken",
    "NotificationDelivery",
    "OutboxEvent",
    "LegalHold",
    "RetentionDisposal",
    "AssistantInteraction",
    "ReportView",
]
