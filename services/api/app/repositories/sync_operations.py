from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_operations import SyncOperation

async def find_by_idempotency_key(
    session: AsyncSession, device_id: uuid.UUID, idempotency_key: str
) -> SyncOperation | None:
    """Find an existing sync operation by device_id and idempotency_key."""
    stmt = select(SyncOperation).where(
        SyncOperation.device_id == device_id,
        SyncOperation.idempotency_key == idempotency_key,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_sync_operation(
    session: AsyncSession,
    device_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    idempotency_key: str,
    operation_type: str,
    payload_sha256: str,
    response_json: dict[str, Any] | None,
) -> SyncOperation:
    """Create a new sync operation record to enforce future idempotency."""
    sync_op = SyncOperation(
        device_id=device_id,
        incident_id=incident_id,
        idempotency_key=idempotency_key,
        operation_type=operation_type,
        payload_sha256=payload_sha256,
        response_json=response_json,
    )
    session.add(sync_op)
    # We do not commit here, the caller manages the transaction
    return sync_op
