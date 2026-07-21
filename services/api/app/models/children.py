"""
Children and ChildGuardians models.

create table children (
  id uuid primary key, center_id uuid not null references centers(id),
  display_name text not null, classroom text,
  active boolean not null default true, synthetic_marker boolean not null default true
);
create table guardians (
  id uuid primary key, center_id uuid not null references centers(id),
  display_name text not null, email text, synthetic_marker boolean not null default true
);
create table child_guardians (
  child_id uuid not null references children(id),
  guardian_id uuid not null references guardians(id),
  is_primary boolean not null default false, primary key(child_id, guardian_id)
);
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    classroom: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    synthetic_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    synthetic_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ChildGuardian(Base):
    """Association table — child_id + guardian_id is the composite primary key."""

    __tablename__ = "child_guardians"

    child_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("children.id"), primary_key=True
    )
    guardian_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardians.id"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
