"""
Device model.

create table devices (
  id uuid primary key, center_id uuid not null references centers(id),
  registered_user_id uuid not null references users(id),
  installation_id text not null unique, platform text not null check(platform in ('ios','ipados')),
  device_label text not null, status text not null check(status in ('active','revoked','blocked')),
  registered_at timestamptz not null default now(), revoked_at timestamptz
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("platform IN ('ios', 'ipados')", name="ck_devices_platform"),
        CheckConstraint(
            "status IN ('active', 'revoked', 'blocked')", name="ck_devices_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    registered_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    installation_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    device_label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
