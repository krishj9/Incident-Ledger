"""
Incident and IncidentChild models.

create table incidents (
  id uuid primary key, center_id uuid not null references centers(id),
  status incident_status not null, category text not null,
  staff_selected_severity severity_level not null, current_severity severity_level not null,
  event_at timestamptz not null,
  event_time_precision text not null check(event_time_precision in ('exact','estimated')),
  location text not null, original_factual_notes text not null,
  actions_taken text not null, treatment_response text,
  witnesses_known boolean not null, restricted boolean not null default false,
  notification_decision text,
  created_by_user_id uuid not null references users(id),
  submitted_by_user_id uuid references users(id),
  assigned_director_id uuid references users(id),
  current_version_id uuid,
  legal_hold boolean not null default false,
  created_at timestamptz not null default now(),
  submitted_at timestamptz, approved_at timestamptz, closed_at timestamptz
);
create table incident_children (
  id uuid primary key, incident_id uuid not null references incidents(id),
  child_id uuid not null references children(id),
  involvement_role text not null check(involvement_role in ('primary_affected','involved','witness')),
  child_specific_details text, unique(incident_id, child_id)
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7
from app.models.enums import IncidentStatus, IncidentStatusType, SeverityLevel, SeverityLevelType


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "event_time_precision IN ('exact', 'estimated')",
            name="ck_incidents_event_time_precision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(IncidentStatusType, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    staff_selected_severity: Mapped[SeverityLevel] = mapped_column(
        SeverityLevelType, nullable=False
    )
    current_severity: Mapped[SeverityLevel] = mapped_column(
        SeverityLevelType, nullable=False
    )
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    event_time_precision: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    original_factual_notes: Mapped[str] = mapped_column(Text, nullable=False)
    actions_taken: Mapped[str] = mapped_column(Text, nullable=False)
    treatment_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    witnesses_known: Mapped[bool] = mapped_column(Boolean, nullable=False)
    restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_director_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # FK to report_versions — added as deferred/nullable; populated after first version created
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def severity(self) -> SeverityLevel:
        return self.current_severity


class IncidentChild(Base):
    __tablename__ = "incident_children"
    __table_args__ = (
        CheckConstraint(
            "involvement_role IN ('primary_affected', 'involved', 'witness')",
            name="ck_incident_children_involvement_role",
        ),
        UniqueConstraint("incident_id", "child_id", name="uq_incident_children"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("children.id"), nullable=False
    )
    involvement_role: Mapped[str] = mapped_column(String, nullable=False)
    child_specific_details: Mapped[str | None] = mapped_column(Text, nullable=True)
