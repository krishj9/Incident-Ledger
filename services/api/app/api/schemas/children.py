from __future__ import annotations

import uuid
from pydantic import BaseModel, ConfigDict

class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    classroom: str | None = None
    active: bool

class ChildrenListResponse(BaseModel):
    children: list[ChildResponse]
