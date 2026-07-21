import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db_session
from app.api.schemas.children import ChildrenListResponse
from app.models.children import Child
from app.models.users import User

router = APIRouter(prefix="/v1/children", tags=["Children"])


@router.get("", response_model=ChildrenListResponse)
async def list_children(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChildrenListResponse:
    """
    List children. Scoped to user's center_id.
    """
    stmt = select(Child).where(Child.center_id == user.center_id, Child.active == True)
    result = await session.execute(stmt)
    children = result.scalars().all()

    return ChildrenListResponse(children=list(children))
