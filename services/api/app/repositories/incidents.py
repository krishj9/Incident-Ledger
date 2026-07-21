import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import String, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incidents import Incident, IncidentChild
from app.repositories.exceptions import EntityNotFoundError, StaleVersionError


async def create_incident(
    session: AsyncSession, center_id: uuid.UUID, created_by_user_id: uuid.UUID, **fields: Any
) -> Incident:
    """Create a new drafted incident."""
    children_data = fields.pop("children", [])
    
    incident = Incident(
        center_id=center_id,
        created_by_user_id=created_by_user_id,
        **fields
    )
    session.add(incident)
    await session.flush()
    
    # Process children
    for child in children_data:
        ic = IncidentChild(
            incident_id=incident.id,
            child_id=child["child_id"],
            involvement_role=child["role"].value if hasattr(child["role"], "value") else child["role"]
        )
        session.add(ic)

    await session.flush()
    return incident


async def get_incident(session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID) -> Incident | None:
    """Get an incident scoped by center."""
    stmt = (
        select(Incident)
        .where(Incident.id == incident_id, Incident.center_id == center_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_incident_with_etag(session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID) -> tuple[Incident, str] | None:
    """Get an incident and its system xmin for optimistic concurrency."""
    stmt = (
        select(Incident, literal_column("xmin").cast(String).label("etag"))
        .where(Incident.id == incident_id, Incident.center_id == center_id)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def list_incidents(
    session: AsyncSession, center_id: uuid.UUID, user_role: str, user_id: uuid.UUID, filters: dict[str, Any] | None = None
) -> list[Incident]:
    """
    List incidents with authorization scoping.
    Staff see own + handed-off. Director+ see all in center.
    """
    from app.models.children import Child
    from app.models.incidents import IncidentChild

    # Subquery for first child name
    first_child_sq = (
        select(Child.display_name)
        .join(IncidentChild, Child.id == IncidentChild.child_id)
        .where(
            IncidentChild.incident_id == Incident.id,
            IncidentChild.involvement_role == "primary_affected"
        )
        .limit(1)
        .scalar_subquery()
    )

    stmt = select(Incident, first_child_sq.label("first_child_name")).where(Incident.center_id == center_id)
    
    # Apply role scoping
    if user_role == "staff":
        stmt = stmt.where(
            (Incident.created_by_user_id == user_id) | 
            (Incident.submitted_by_user_id == user_id)
        )
    elif user_role == "operations_support":
        stmt = stmt.where(Incident.restricted == False)
    
    # Apply filters
    if filters:
        if "status" in filters:
            stmt = stmt.where(Incident.status == filters["status"])
    
    # Sort newest first
    stmt = stmt.order_by(Incident.event_at.desc())
    
    result = await session.execute(stmt)
    rows = result.all()
    
    incidents = []
    for inc, child_name in rows:
        inc.first_child_name = child_name
        incidents.append(inc)
        
    return incidents


async def update_draft(
    session: AsyncSession, incident_id: uuid.UUID, center_id: uuid.UUID, etag: str, **fields: Any
) -> Incident:
    """
    Optimistic update of a draft incident using PostgreSQL xmin as an ETag.
    Raises StaleVersionError if the provided etag does not match the database state.
    """
    result = await get_incident_with_etag(session, incident_id, center_id)
    if not result:
        raise EntityNotFoundError("Incident not found")
    
    incident, current_etag = result
    
    # ETag check (bypass if etag is explicitly empty or '*' for force update, though usually strict)
    if etag and current_etag != etag:
        raise StaleVersionError("The incident has been modified since it was loaded.")
        
    children_data = fields.pop("children", None)

    for key, value in fields.items():
        if value is not None:
            setattr(incident, key, value)
            
    # Note: Full update of children involves clearing old and inserting new,
    # or a merge. Since it's a draft update, we drop and recreate for simplicity.
    if children_data is not None:
        # Delete existing children
        del_stmt = select(IncidentChild).where(IncidentChild.incident_id == incident.id)
        existing_children = (await session.execute(del_stmt)).scalars().all()
        for child in existing_children:
            await session.delete(child)
            
        for child in children_data:
            ic = IncidentChild(
                incident_id=incident.id,
                child_id=child["child_id"],
                involvement_role=child["role"].value if hasattr(child["role"], "value") else child["role"]
            )
            session.add(ic)

    await session.flush()
    return incident


async def get_review_queue(
    session: AsyncSession,
    center_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Returns all submitted or under_review incidents for a center,
    annotated with elapsed_seconds since submission and escalation_state.
    Ordered by submitted_at ASC (oldest first for urgency).
    """
    from app.models.enums import IncidentStatus
    from sqlalchemy import case

    stmt = (
        select(Incident)
        .where(
            Incident.center_id == center_id,
            Incident.status.in_([IncidentStatus.submitted, IncidentStatus.under_review])
        )
        .order_by(Incident.submitted_at.asc())
    )
    result = await session.execute(stmt)
    incidents = result.scalars().all()

    now = datetime.now(UTC)
    items = []
    for inc in incidents:
        elapsed = int((now - inc.submitted_at).total_seconds()) if inc.submitted_at else 0
        escalation_state = None
        if inc.current_severity in ("critical",):
            if elapsed >= 3600:
                escalation_state = "regional"
            elif elapsed >= 1800:
                escalation_state = "backup"
        elif inc.current_severity in ("high",):
            if elapsed >= 1800:
                escalation_state = "backup"

        items.append({
            "incident_id": inc.id,
            "status": inc.status,
            "category": inc.category,
            "severity": inc.current_severity,
            "location": inc.location,
            "submitted_at": inc.submitted_at,
            "elapsed_seconds": elapsed,
            "escalation_state": escalation_state,
            "assigned_director_id": inc.assigned_director_id,
        })

    return items
