from __future__ import annotations

import uuid
from typing import Any
from datetime import datetime, UTC

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceItem

async def count_by_incident(session: AsyncSession, incident_id: uuid.UUID) -> int:
    """Count the number of evidence items for an incident."""
    stmt = select(func.count(EvidenceItem.id)).where(EvidenceItem.incident_id == incident_id)
    result = await session.execute(stmt)
    return result.scalar() or 0

async def create_evidence(
    session: AsyncSession,
    incident_id: uuid.UUID,
    storage_object_uri: str,
    media_type: str,
    byte_size: int,
    capture_user_id: uuid.UUID,
    capture_device_id: uuid.UUID,
    upload_status: str = "pending",
    sha256: str = "",
) -> EvidenceItem:
    """Create a new evidence item in pending status."""
    evidence = EvidenceItem(
        incident_id=incident_id,
        storage_object_uri=storage_object_uri,
        media_type=media_type,
        byte_size=byte_size,
        capture_user_id=capture_user_id,
        capture_device_id=capture_device_id,
        upload_status=upload_status,
        captured_at=datetime.now(UTC),
        sha256=sha256,
    )
    session.add(evidence)
    await session.flush()
    return evidence

async def get_evidence(session: AsyncSession, evidence_id: uuid.UUID, incident_id: uuid.UUID) -> EvidenceItem | None:
    """Get an evidence item belonging to an incident."""
    stmt = select(EvidenceItem).where(
        EvidenceItem.id == evidence_id,
        EvidenceItem.incident_id == incident_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def update_evidence_status(
    session: AsyncSession,
    evidence_id: uuid.UUID,
    upload_status: str,
    sha256: str | None = None,
) -> EvidenceItem | None:
    """Update evidence status and optionally sha256."""
    stmt = select(EvidenceItem).where(EvidenceItem.id == evidence_id)
    result = await session.execute(stmt)
    evidence = result.scalar_one_or_none()
    
    if evidence:
        evidence.upload_status = upload_status
        if upload_status == "ready":
            evidence.finalized_at = datetime.now(UTC)
        if sha256 is not None:
            evidence.sha256 = sha256
        await session.flush()
        
    return evidence
