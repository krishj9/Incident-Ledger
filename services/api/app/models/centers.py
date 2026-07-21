"""
Center model.

create table centers (
  id uuid primary key, code text not null unique, name text not null, timezone text not null,
  is_demo_enabled boolean not null default true, max_active_mobile_installations int not null default 20,
  synthetic_marker boolean not null default true, created_at timestamptz not null default now()
);
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7, utc_now


class Center(Base):
    __tablename__ = "centers"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)
    is_demo_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_active_mobile_installations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20
    )
    synthetic_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
