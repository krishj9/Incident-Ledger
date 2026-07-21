import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_center_scope
from app.audit.exporter import build_audit_packet
from app.db import get_db_session
from app.models.enums import UserRole
from app.models.users import User
from app.services.exceptions import UnauthorizedError
from app.services.legal_hold_service import apply_legal_hold

router = APIRouter(prefix="/v1/incidents", tags=["audit"])

class LegalHoldRequest(BaseModel):
    reason: str


@router.get("/{incident_id}/audit-packet")
async def get_audit_packet(
    incident_id: Annotated[uuid.UUID, Path()],
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_correlation_id: Annotated[str, Header()] = "missing-correlation-id",
) -> dict[str, Any]:
    """
    Export the full audit packet for an incident.
    Requires director or compliance_reviewer role.
    """
    # Enforce role
    if UserRole(current_user.role.value) not in (UserRole.director, UserRole.compliance_reviewer):
        raise UnauthorizedError("Audit packet export requires director or compliance_reviewer role")
        
    try:
        packet = await build_audit_packet(
            session=db,
            incident_id=incident_id,
            center_id=current_user.center_id,
            actor_id=current_user.id,
            correlation_id=x_correlation_id
        )
        return packet
    except ValueError:
        raise HTTPException(status_code=404, detail="Incident not found")

@router.post("/{incident_id}/legal-hold")
async def create_legal_hold(
    incident_id: Annotated[uuid.UUID, Path()],
    body: LegalHoldRequest,
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_correlation_id: Annotated[str, Header()] = "missing-correlation-id",
) -> dict[str, Any]:
    """
    Apply a legal hold to an incident.
    Requires director or compliance_reviewer role.
    """
    # Enforce role
    if UserRole(current_user.role.value) not in (UserRole.director, UserRole.compliance_reviewer):
        raise UnauthorizedError("Legal hold requires director or compliance_reviewer role")
        
    try:
        return await apply_legal_hold(
            session=db,
            user=current_user,
            incident_id=incident_id,
            reason=body.reason,
            correlation_id=x_correlation_id
        )
    except ValueError as e:
        if "reason is required" in str(e).lower():
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=404, detail="Incident not found")
