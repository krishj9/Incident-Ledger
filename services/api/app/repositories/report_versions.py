import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import VersionKind
from app.models.report_versions import ReportVersion


async def create_version(
    session: AsyncSession,
    incident_id: uuid.UUID,
    version_kind: VersionKind,
    created_by: uuid.UUID,
    parent_version_id: uuid.UUID | None,
    original_staff_notes: str,
    rendered_narrative: str,
    structured_snapshot: dict[str, Any],
    edit_reason: str | None = None,
) -> ReportVersion:
    """
    Create an immutable report version.
    Automatically increments version_number and computes content_sha256.
    """
    # Auto-increment version_number
    stmt = select(func.max(ReportVersion.version_number)).where(
        ReportVersion.incident_id == incident_id
    )
    result = await session.execute(stmt)
    max_v = result.scalar()
    next_v = 1 if max_v is None else max_v + 1

    # Compute deterministic JSON hash
    json_bytes = json.dumps(structured_snapshot, sort_keys=True).encode("utf-8")
    content_sha256 = hashlib.sha256(json_bytes).hexdigest()

    version = ReportVersion(
        incident_id=incident_id,
        version_number=next_v,
        version_kind=version_kind.value,
        parent_version_id=parent_version_id,
        original_staff_notes=original_staff_notes,
        rendered_narrative=rendered_narrative,
        structured_snapshot=structured_snapshot,
        content_sha256=content_sha256,
        created_by_user_id=created_by,
        edit_reason=edit_reason,
    )
    session.add(version)
    await session.flush()
    return version
