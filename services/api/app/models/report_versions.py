"""
ReportVersion model — IMMUTABLE after creation (enforced by DB trigger).

create table report_versions (
  id uuid primary key, incident_id uuid not null references incidents(id),
  version_number int not null,
  version_kind text not null check(version_kind in ('staff_submission','director_edit','approved','addendum')),
  parent_version_id uuid references report_versions(id),
  original_staff_notes text not null, rendered_narrative text not null,
  structured_snapshot jsonb not null, content_sha256 text not null,
  created_by_user_id uuid not null references users(id),
  edit_reason text, created_at timestamptz not null default now(),
  unique(incident_id, version_number)
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class ReportVersion(Base):
    """
    Immutable version snapshot. Never updated after creation.
    The DB trigger enforced in migration prevents UPDATE/DELETE.
    """

    __tablename__ = "report_versions"
    __table_args__ = (
        CheckConstraint(
            "version_kind IN ('staff_submission', 'director_edit', 'approved', 'addendum')",
            name="ck_report_versions_kind",
        ),
        UniqueConstraint("incident_id", "version_number", name="uq_report_versions_incident_num"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_kind: Mapped[str] = mapped_column(String, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=True
    )
    original_staff_notes: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    structured_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    edit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
