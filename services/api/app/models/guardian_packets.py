"""
GuardianPacket model.

create table guardian_packets (
  id uuid primary key, incident_id uuid not null references incidents(id),
  child_id uuid not null references children(id),
  approved_version_id uuid not null references report_versions(id),
  primary_guardian_id uuid not null references guardians(id),
  status text not null check(status in ('pending','sent','opened','acknowledged','disagreed','unreachable','closed')),
  notification_allowed boolean not null default true,
  created_at timestamptz not null default now(),
  unique(incident_id, child_id, approved_version_id)
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class GuardianPacket(Base):
    __tablename__ = "guardian_packets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'opened', 'acknowledged', 'disagreed', 'unreachable', 'closed')",
            name="ck_guardian_packets_status",
        ),
        UniqueConstraint(
            "incident_id", "child_id", "approved_version_id",
            name="uq_guardian_packets_incident_child_version",
        ),
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
    approved_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=False
    )
    primary_guardian_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardians.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    notification_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
