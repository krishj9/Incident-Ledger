"""
SQLAlchemy Enum types matching the PostgreSQL custom enum definitions in db-schema.md.

create type user_role as enum (...)
create type incident_status as enum (...)
create type severity_level as enum (...)
"""

from __future__ import annotations

import enum

import sqlalchemy as sa


class UserRole(str, enum.Enum):
    staff = "staff"
    director = "director"
    backup_director = "backup_director"
    regional_admin = "regional_admin"
    compliance_reviewer = "compliance_reviewer"
    operations_support = "operations_support"


class IncidentStatus(str, enum.Enum):
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


class SeverityLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


# SQLAlchemy Enum column types — these map to the PostgreSQL native enum types.
# The name= parameter must match the PostgreSQL type name exactly so that
# Alembic does not try to recreate them as check-constraint enums.
UserRoleType = sa.Enum(
    UserRole,
    name="user_role",
    create_constraint=True,
    validate_strings=True,
)

IncidentStatusType = sa.Enum(
    IncidentStatus,
    name="incident_status",
    create_constraint=True,
    validate_strings=True,
)

SeverityLevelType = sa.Enum(
    SeverityLevel,
    name="severity_level",
    create_constraint=True,
    validate_strings=True,
)
