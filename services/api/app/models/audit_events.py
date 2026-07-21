"""
AuditEvent model — IMMUTABLE / append-only (enforced by DB trigger).

create table audit_events (
  id uuid primary key, center_id uuid not null references centers(id),
  incident_id uuid references incidents(id),
  actor_user_id uuid references users(id), device_id uuid references devices(id),
  action text not null,
  report_version_id uuid references report_versions(id),
  correlation_id text not null, occurred_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class AuditEvent(Base):
    """
    Append-only audit record. The DB trigger prevents UPDATE/DELETE.
    Never log sensitive content (tokens, JWTs, narrative) at info level.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    report_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=True
    )
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
