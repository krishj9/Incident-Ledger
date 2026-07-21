"""
FastAPI dependencies for authentication, authorization, and center scoping.

Security rules (security-privacy.md):
  - No self-registration: if external_subject doesn't map to a users row → 401
  - Never identify a user solely by device or PIN
  - Render no roster, report, guardian, or evidence content before valid session
  - RBAC enforced at service layer as well as router (defense-in-depth)

All auth errors use RFC 9457 format with:
  - 401 for unauthenticated
  - 403 for authenticated-but-unauthorized (role/center mismatch)
"""

from __future__ import annotations

from functools import wraps
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.integrations.oidc import OIDCError, extract_claims
from app.models.enums import UserRole
from app.models.users import User
from app.repositories import users as user_repo

logger = structlog.get_logger(__name__)

# HTTP Bearer scheme — auto-generates 401 on missing/malformed Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


# ── RFC 9457 HTTP exception helpers ────────────────────────────────────────────

def _http_401(code: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "type": "https://incident-ledger.dev/errors/unauthenticated",
            "title": "Authentication required",
            "status": 401,
            "code": code,
            "detail": detail,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def _http_403(code: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "type": "https://incident-ledger.dev/errors/forbidden",
            "title": "Access denied",
            "status": 403,
            "code": code,
            "detail": detail,
        },
    )


# ── Core auth dependency ───────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Validate bearer JWT and return the matching User from the database.

    Steps:
      1. Require Authorization: Bearer <token>
      2. Validate token (OIDC or mock) → extract external_subject
      3. Look up user in DB by external_subject → 401 if not found (no self-registration)
      4. Check user.active → 401 if deactivated

    Never return user data before completing all four steps.
    """
    if credentials is None:
        raise _http_401("MISSING_TOKEN", "Authorization: Bearer <token> is required")

    raw_token = credentials.credentials

    try:
        claims = await extract_claims(raw_token)
    except OIDCError as exc:
        # Log code only, never log the token or exc message detail
        logger.warning("token_validation_failed", code=exc.code)
        raise _http_401(exc.code, exc.detail)

    # Database lookup — no self-registration
    user = await user_repo.get_user_by_external_subject(db, claims.external_subject)
    if user is None:
        # Do NOT reveal whether the subject exists in any other system
        logger.warning(
            "user_not_found_for_subject",
            # Never log the raw subject — only a boolean presence flag
            subject_present=True,
        )
        raise _http_401("USER_NOT_FOUND", "No account found for the provided credentials")

    if not user.active:
        raise _http_401("USER_INACTIVE", "This account has been deactivated")

    # Bind user context to structlog for the rest of this request
    structlog.contextvars.bind_contextvars(
        user_id=str(user.id),
        user_role=user.role.value,
        center_id=str(user.center_id),
    )

    return user


# ── Role enforcement dependency factory ───────────────────────────────────────

def require_role(*roles: UserRole):  # type: ignore[no-untyped-def]
    """
    Returns a FastAPI dependency that ensures the current user has one of the given roles.

    Usage:
        @router.post("/some-director-action", dependencies=[Depends(require_role(UserRole.director))])

    Raises 403 if the role check fails.
    """
    async def _checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise _http_403(
                "INSUFFICIENT_ROLE",
                f"This action requires one of: {[r.value for r in roles]}",
            )
        return current_user

    return _checker


# ── Center scope dependency ────────────────────────────────────────────────────

async def require_center_scope(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that confirms the user belongs to a center.

    Attach to any endpoint that reads/writes center-scoped data.
    Routers extract center_id from current_user.center_id — never from request body.
    """
    # Center membership is guaranteed by the users table FK; this is a
    # documentation/enforcement hook for future multi-center scenarios.
    return current_user


# ── Idempotency-Key header dependency ─────────────────────────────────────────

async def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    """
    Every mutation endpoint must include an Idempotency-Key header (api-contracts.md).

    Returns the key value; raises 422 if missing.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://incident-ledger.dev/errors/missing_idempotency_key",
                "title": "Idempotency-Key header is required",
                "status": 422,
                "code": "MISSING_IDEMPOTENCY_KEY",
                "detail": "All mutation requests must include an Idempotency-Key header.",
            },
        )
    return idempotency_key
