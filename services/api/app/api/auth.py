"""
Auth router — user session and device endpoints.

Endpoints:
  GET  /v1/me                   — return active user profile (no content before auth)
  POST /v1/auth/session/switch  — end prior session, begin new session for authenticated user
  POST /v1/devices/register     — register device, enforce center device limit

Security rules (api-contracts.md + security-privacy.md):
  - Never return data before auth check completes
  - Every mutation requires Idempotency-Key header
  - Every response includes X-Correlation-ID (handled by middleware)
  - 401 for unauthenticated, 403 for policy/role denial, 409 for limit/conflict
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    require_center_scope,
    require_idempotency_key,
)
from app.audit.writer import write_audit_event
from app.db import get_db_session
from app.models.base import generate_uuid7
from app.models.centers import Center
from app.models.devices import Device
from app.models.users import User
from app.repositories import devices as device_repo

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["auth"])


# ── /me ───────────────────────────────────────────────────────────────────────

class MeResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    role: str
    center_id: uuid.UUID
    center_name: str
    center_code: str
    center_timezone: str


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user profile",
    description=(
        "Returns the authenticated user's profile. "
        "Returns 401 if unauthenticated. "
        "No roster, report, or sensitive data is included — just identity fields."
    ),
)
async def get_me(
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MeResponse:
    """Return active user profile — no content before auth."""
    # Fetch center for name/code/timezone
    result = await db.execute(
        select(Center).where(Center.id == current_user.center_id).limit(1)
    )
    center = result.scalar_one_or_none()
    if center is None:
        # Should never happen — center_id FK guarantee — but guard defensively
        raise HTTPException(
            status_code=500,
            detail={
                "type": "https://incident-ledger.dev/errors/internal_server_error",
                "title": "Center data unavailable",
                "status": 500,
                "code": "CENTER_NOT_FOUND",
                "detail": "User center could not be resolved.",
            },
        )

    return MeResponse(
        user_id=current_user.id,
        display_name=current_user.display_name,
        role=current_user.role.value,
        center_id=current_user.center_id,
        center_name=center.name,
        center_code=center.code,
        center_timezone=center.timezone,
    )


# ── /auth/session/switch ──────────────────────────────────────────────────────

class SessionSwitchResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str
    role: str
    switched_at: datetime


@router.post(
    "/auth/session/switch",
    response_model=SessionSwitchResponse,
    summary="Switch active user session",
    description=(
        "Ends any prior active session on this device and begins a new session "
        "for the authenticated user. Writes an audit event. "
        "Requires Idempotency-Key header."
    ),
)
async def session_switch(
    request: Request,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> SessionSwitchResponse:
    """
    End prior active session (if any) and begin a new one.

    In this implementation, sessions are stateless JWT-based — there is no
    server-side session store. 'Switch' is implemented by:
    1. Auditing the switch event (append-only)
    2. Returning the new user's identity so the client can update its display

    The prior session token is rendered unusable when it expires;
    forced invalidation via a token blocklist is a post-demo enhancement.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "")
    switched_at = datetime.now(UTC)

    # Audit the session switch — append-only
    await write_audit_event(
        db,
        center_id=current_user.center_id,
        action="session_switch",
        correlation_id=correlation_id,
        actor_user_id=current_user.id,
        metadata={
            "idempotency_key": idempotency_key,
            "switched_at": switched_at.isoformat(),
        },
    )

    logger.info(
        "session_switched",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )

    return SessionSwitchResponse(
        user_id=current_user.id,
        display_name=current_user.display_name,
        role=current_user.role.value,
        switched_at=switched_at,
    )


# ── /devices/register ─────────────────────────────────────────────────────────

_VALID_PLATFORMS = {"ios", "ipados"}


class DeviceRegisterRequest(BaseModel):
    installation_id: str = Field(..., min_length=1, max_length=256)
    platform: str = Field(..., pattern="^(ios|ipados)$")
    device_label: str = Field(..., min_length=1, max_length=128)


class DeviceRegisterResponse(BaseModel):
    device_id: uuid.UUID
    installation_id: str
    platform: str
    status: str
    registered_at: datetime


@router.post(
    "/devices/register",
    response_model=DeviceRegisterResponse,
    status_code=201,
    summary="Register a mobile device",
    description=(
        "Register a device installation for the authenticated user's center. "
        "Validates that the center has not exceeded max_active_mobile_installations (default 20). "
        "Platform must be 'ios' or 'ipados'. "
        "Requires Idempotency-Key header."
    ),
)
async def register_device(
    request: Request,
    body: DeviceRegisterRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> DeviceRegisterResponse:
    """
    Register a new device installation.

    Business rules:
    - If installation_id is already registered → return existing record (idempotent)
    - Center must not exceed max_active_mobile_installations → 409 if over limit
    - platform must be ios or ipados (enforced by Pydantic pattern + DB check constraint)
    """
    correlation_id = request.headers.get("X-Correlation-ID", "")

    # 1. Idempotency — if already registered, return existing record
    existing = await device_repo.get_device_by_installation_id(db, body.installation_id)
    if existing is not None:
        if existing.center_id != current_user.center_id:
            # installation_id registered to a different center — 409 conflict
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "https://incident-ledger.dev/errors/device_conflict",
                    "title": "Device already registered",
                    "status": 409,
                    "code": "DEVICE_ALREADY_REGISTERED",
                    "detail": "This installation_id is already registered to a different center.",
                },
            )
        logger.info("device_register_idempotent", device_id=str(existing.id))
        return DeviceRegisterResponse(
            device_id=existing.id,
            installation_id=existing.installation_id,
            platform=existing.platform,
            status=existing.status,
            registered_at=existing.registered_at,
        )

    # 2. Fetch center to get limit
    center_result = await db.execute(
        select(Center).where(Center.id == current_user.center_id).limit(1)
    )
    center = center_result.scalar_one_or_none()
    if center is None:
        raise HTTPException(status_code=500, detail="Center not found")

    # 3. Enforce device limit
    active_count = await device_repo.count_active_devices_for_center(
        db, current_user.center_id
    )
    if active_count >= center.max_active_mobile_installations:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "https://incident-ledger.dev/errors/device_limit_exceeded",
                "title": "Device limit exceeded",
                "status": 409,
                "code": "DEVICE_LIMIT_EXCEEDED",
                "detail": (
                    f"This center has reached the maximum of "
                    f"{center.max_active_mobile_installations} active device installations."
                ),
            },
        )

    # 4. Register device
    device_id = generate_uuid7()
    device = await device_repo.register_device(
        db,
        device_id=device_id,
        center_id=current_user.center_id,
        registered_user_id=current_user.id,
        installation_id=body.installation_id,
        platform=body.platform,
        device_label=body.device_label,
    )

    # Flush so the device row exists before the audit FK reference
    await db.flush()
    await db.refresh(device)

    # 5. Audit — device now exists in DB, FK is satisfied
    await write_audit_event(
        db,
        center_id=current_user.center_id,
        action="device_register",
        correlation_id=correlation_id,
        actor_user_id=current_user.id,
        device_id=device_id,
        metadata={
            "platform": body.platform,
            "idempotency_key": idempotency_key,
        },
    )

    logger.info(
        "device_registered",
        device_id=str(device_id),
        platform=body.platform,
        center_id=str(current_user.center_id),
    )

    return DeviceRegisterResponse(
        device_id=device.id,
        installation_id=device.installation_id,
        platform=device.platform,
        status=device.status,
        registered_at=device.registered_at,
    )
