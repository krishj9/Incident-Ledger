"""
Acknowledgement model — IMMUTABLE after creation (enforced by DB trigger).

create table acknowledgements (
  id uuid primary key, guardian_packet_id uuid not null references guardian_packets(id),
  method text not null check(method in ('in_person','email_link')),
  typed_full_name text, receipt_confirmed boolean not null,
  outcome text not null check(outcome in ('acknowledged','disagreed')),
  disagreement_comment text,
  report_version_id uuid not null references report_versions(id),
  staff_present_user_id uuid references users(id),
  acknowledged_at timestamptz not null default now()
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class Acknowledgement(Base):
    """
    Immutable outcome record — disagreement stored here, never modifies the report.
    """

    __tablename__ = "acknowledgements"
    __table_args__ = (
        CheckConstraint(
            "method IN ('in_person', 'email_link')",
            name="ck_acknowledgements_method",
        ),
        CheckConstraint(
            "outcome IN ('acknowledged', 'disagreed')",
            name="ck_acknowledgements_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    guardian_packet_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardian_packets.id"), nullable=False
    )
    method: Mapped[str] = mapped_column(String, nullable=False)
    typed_full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    receipt_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    disagreement_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=False
    )
    staff_present_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
