"""
User repository — database access for the users table.

All queries are scoped by center_id at the service layer (not here);
repositories only perform the SQL fetch and return ORM objects.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def get_user_by_external_subject(session: AsyncSession, subject: str) -> User | None:
    """
    Look up a user by their OIDC external_subject claim.

    Returns None if no matching user exists (→ caller raises 401).
    Never log the subject value (may contain PII).
    """
    result = await session.execute(
        select(User).where(User.external_subject == subject).limit(1)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Look up a user by their primary key UUID."""
    result = await session.execute(
        select(User).where(User.id == user_id).limit(1)
    )
    return result.scalar_one_or_none()
