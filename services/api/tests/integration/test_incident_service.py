import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import IncidentCategory, IncidentStatus, InvolvementRole, SeverityLevel
from app.models.centers import Center
from app.models.children import Child
from app.models.users import User
from app.repositories.incidents import get_incident
from app.services.exceptions import ValidationFailedError
from app.services.incident_service import create_draft, submit, update_draft


@pytest.fixture
async def setup_db(db_session: AsyncSession) -> tuple[uuid.UUID, User, uuid.UUID]:
    center_id = uuid.uuid4()
    user_id = uuid.uuid4()
    child_id = uuid.uuid4()
    
    # Create required DB records using SQLAlchemy models to rely on defaults
    center = Center(id=center_id, code=f"TEST-C-{center_id.hex[:6]}", name="Test", timezone="UTC")
    db_session.add(center)
    await db_session.flush()

    user = User(id=user_id, center_id=center_id, external_subject=f"ext-{user_id.hex[:6]}", display_name="Test User", role="staff")
    db_session.add(user)
    
    child = Child(id=child_id, center_id=center_id, display_name="Child 1")
    db_session.add(child)
    
    await db_session.commit()
    return center_id, user, child_id


@pytest.mark.asyncio
async def test_draft_update_submit_flow(db_session: AsyncSession, setup_db: tuple[uuid.UUID, User, uuid.UUID]) -> None:
    center_id, user, child_id = setup_db
    
    # 1. Create draft
    draft = await create_draft(
        session=db_session,
        user=user,
        center_id=center_id,
        category=IncidentCategory.injury_accident,
        severity=SeverityLevel.low,
        children=[{"child_id": child_id, "role": InvolvementRole.primary_affected}],
        correlation_id="test-corr",
        idempotency_key="test-idem-1",
        event_at=datetime.now(UTC),
        event_time_precision="exact",
        location="Playground",
        original_factual_notes="Draft notes",
        actions_taken="Ice",
        witnesses_known=False,
    )
    
    assert draft.status == IncidentStatus.draft
    assert draft.category == IncidentCategory.injury_accident
    
    # Needs to be committed to be readable with xmin for update
    await db_session.commit()
    
    # 2. Update draft
    updated = await update_draft(
        session=db_session,
        user=user,
        incident_id=draft.id,
        etag="", # empty string to bypass xmin check for this simple test
        correlation_id="test-corr-2",
        idempotency_key="test-idem-2",
        original_factual_notes="Updated notes"
    )
    
    assert updated.original_factual_notes == "Updated notes"
    await db_session.commit()
    
    # 3. Submit
    attestation = {"accurate_to_best_of_knowledge": True, "confirmed_at": datetime.now(UTC)}
    device_info = {"device_id": uuid.uuid4(), "offline_originated": False}
    
    response = await submit(
        session=db_session,
        user=user,
        incident_id=draft.id,
        attestation=attestation,
        device_info=device_info,
        correlation_id="test-corr-3",
        idempotency_key="test-idem-3",
    )
    
    assert response.status == IncidentStatus.submitted
    
    # Verify in DB
    saved = await get_incident(db_session, draft.id, center_id)
    assert saved is not None
    assert saved.status.value == IncidentStatus.submitted.value
    assert saved.current_version_id is not None
    await db_session.commit()


@pytest.mark.asyncio
async def test_submit_missing_field_errors(db_session: AsyncSession, setup_db: tuple[uuid.UUID, User, uuid.UUID]) -> None:
    center_id, user, child_id = setup_db
    
    # Create draft with missing fields (e.g. location, actions_taken missing)
    draft = await create_draft(
        session=db_session,
        user=user,
        center_id=center_id,
        category=IncidentCategory.injury_accident,
        severity=SeverityLevel.low,
        children=[], # Missing primary child
        correlation_id="test-corr-fail",
        idempotency_key="test-idem-fail",
        event_at=datetime.now(UTC),
        event_time_precision="exact",
        location="", # Missing
        original_factual_notes="Draft notes",
        actions_taken="", # Missing
        witnesses_known=False,
    )
    
    await db_session.commit()
    
    attestation = {"accurate_to_best_of_knowledge": True, "confirmed_at": datetime.now(UTC)}
    device_info = {"device_id": uuid.uuid4(), "offline_originated": False}
    
    with pytest.raises(ValidationFailedError) as exc:
        await submit(
            session=db_session,
            user=user,
            incident_id=draft.id,
            attestation=attestation,
            device_info=device_info,
            correlation_id="test-corr-fail-2",
            idempotency_key="test-idem-fail-2",
        )
        
    errors = exc.value.errors
    assert any("location" in str(e).lower() for e in errors)
    assert any("actions_taken" in str(e).lower() for e in errors)
    assert any("child" in str(e).lower() for e in errors)
