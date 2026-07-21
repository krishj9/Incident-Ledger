"""
ContactAttempt model — IMMUTABLE after creation (enforced by DB trigger).

create table contact_attempts (
  id uuid primary key, incident_id uuid not null references incidents(id),
  guardian_id uuid not null references guardians(id),
  method text not null, outcome text not null, notes text,
  attempted_by_user_id uuid not null references users(id),
  attempted_at timestamptz not null
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class ContactAttempt(Base):
    """Immutable event record — contact method/result/actor/time."""

    __tablename__ = "contact_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    guardian_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardians.id"), nullable=False
    )
    method: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
