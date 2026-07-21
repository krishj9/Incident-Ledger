"""
Operations router — health and operational endpoints.

GET /v1/operations/health — no auth required; used by load balancers and CI.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_center_scope
from app.db import get_db_session
from app.models.users import User
from app.models.enums import UserRole
from app.services.exceptions import UnauthorizedError
from app.services.operations_service import get_health_stats

router = APIRouter(prefix="/v1/operations", tags=["operations"])

@router.get(
    "/health",
    summary="Operations health and stats",
    description="Returns detailed operations stats. Accessible to operations_support role only.",
)
async def health(
    current_user: Annotated[User, Depends(require_center_scope)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    if UserRole(current_user.role.value) != UserRole.operations_support:
        raise UnauthorizedError("Access restricted to operations_support role")
        
    return await get_health_stats(db)
