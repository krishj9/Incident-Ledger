import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.domain.enums import IncidentStatus, IncidentCategory, SeverityLevel
from app.models.enums import UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import User
from app.models.centers import Center
from app.models.children import Child

@pytest.fixture
async def setup_db(db_session: AsyncSession) -> tuple[uuid.UUID, User, uuid.UUID]:
    center_id = uuid.uuid4()
    user_id = uuid.uuid4()
    child_id = uuid.uuid4()
    
    # Create required DB records using SQLAlchemy models to rely on defaults
    center = Center(id=center_id, code=f"TEST-C-{center_id.hex[:6]}", name="Test", timezone="UTC")
    db_session.add(center)
    await db_session.flush()

    user = User(id=user_id, center_id=center_id, external_subject=f"ext-{user_id.hex[:6]}", display_name="Test User", role=UserRole.staff)
    db_session.add(user)
    
    child = Child(id=child_id, center_id=center_id, display_name="Test Child")
    db_session.add(child)
    await db_session.commit()
    
    return center_id, user, child_id

@pytest.mark.asyncio
async def test_api_draft_update_submit(db_session: AsyncSession, setup_db: tuple[uuid.UUID, User, uuid.UUID]):
    center_id, user, child_id = setup_db
    
    # Needs authorization header to simulate staff
    headers = {
        "Authorization": "Bearer TEST_TOKEN", # Need a way to mock auth. But we might need to mock get_current_user
        "Idempotency-Key": "test-key-1"
    }
    
    # Wait, the app uses `app.api.deps.get_current_user` which validates OIDC. 
    # For testing, we can override the dependency.
    async def override_get_current_user():
        return user
    
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create draft
        response = await ac.post(
            "/v1/incidents",
            headers=headers,
            json={
                "category": "injury_accident",
                "severity": "low",
                "children": [{"child_id": str(child_id), "role": "primary_affected"}],
                "synthetic_marker": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        incident_id = data["id"]
        
        # 2. Get incident (needs etag)
        response = await ac.get(f"/v1/incidents/{incident_id}")
        assert response.status_code == 200
        data = response.json()
        etag = data["etag"]
        
        # 3. Update draft
        headers["Idempotency-Key"] = "test-key-2"
        headers["If-Match"] = f'"{etag}"'
        response = await ac.patch(
            f"/v1/incidents/{incident_id}/draft",
            headers=headers,
            json={
                "location": "Playground",
                "actions_taken": "First aid",
                "synthetic_marker": True
            }
        )
        assert response.status_code == 200
        
        # 4. Submit missing fields -> 422
        headers["Idempotency-Key"] = "test-key-3"
        response = await ac.post(
            f"/v1/incidents/{incident_id}/submit",
            headers=headers,
            json={
                "staff_attestation": {"accurate_to_best_of_knowledge": True, "confirmed_at": "2026-07-20T10:00:00Z"},
                "submitted_from": {"device_id": str(uuid.uuid4()), "offline_originated": False},
                "synthetic_marker": True
            }
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_FAILED"
        
        # 5. Fix missing fields
        response = await ac.get(f"/v1/incidents/{incident_id}")
        etag = response.json()["etag"]
        
        headers["Idempotency-Key"] = "test-key-4"
        headers["If-Match"] = f'"{etag}"'
        response = await ac.patch(
            f"/v1/incidents/{incident_id}/draft",
            headers=headers,
            json={
                "event_at": "2026-07-20T09:00:00Z",
                "event_time_precision": "exact",
                "original_factual_notes": "A simple note",
                "synthetic_marker": True
            }
        )
        assert response.status_code == 200
        
        # 6. Submit success -> 200
        headers["Idempotency-Key"] = "test-key-5"
        response = await ac.post(
            f"/v1/incidents/{incident_id}/submit",
            headers=headers,
            json={
                "staff_attestation": {"accurate_to_best_of_knowledge": True, "confirmed_at": "2026-07-20T10:00:00Z"},
                "submitted_from": {"device_id": str(uuid.uuid4()), "offline_originated": False},
                "synthetic_marker": True
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "submitted"
        
    app.dependency_overrides.clear()
