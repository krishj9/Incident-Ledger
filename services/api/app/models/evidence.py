"""
EvidenceItem model.

create table evidence_items (
  id uuid primary key, incident_id uuid not null references incidents(id),
  storage_object_uri text not null unique, sha256 text not null,
  media_type text not null check(media_type in ('image/jpeg','image/heic')),
  byte_size bigint not null check(byte_size <= 10485760),
  capture_user_id uuid not null references users(id),
  capture_device_id uuid not null references devices(id),
  captured_at timestamptz not null,
  other_child_possible boolean not null default false,
  upload_status text not null check(upload_status in ('pending','uploading','ready','failed','unavailable')),
  finalized_at timestamptz
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('image/jpeg', 'image/heic')",
            name="ck_evidence_media_type",
        ),
        CheckConstraint(
            "byte_size <= 10485760",
            name="ck_evidence_byte_size",
        ),
        CheckConstraint(
            "upload_status IN ('pending', 'uploading', 'ready', 'failed', 'unavailable')",
            name="ck_evidence_upload_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    storage_object_uri: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    capture_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    capture_device_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    other_child_possible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    upload_status: Mapped[str] = mapped_column(String, nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
