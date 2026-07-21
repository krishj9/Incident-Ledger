"""
User model.

create table users (
  id uuid primary key, center_id uuid not null references centers(id),
  external_subject text not null unique,
  display_name text not null, role user_role not null, active boolean not null default true,
  synthetic_marker boolean not null default true, created_at timestamptz not null default now()
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7
from app.models.enums import UserRole, UserRoleType


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    external_subject: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(UserRoleType, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    synthetic_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
