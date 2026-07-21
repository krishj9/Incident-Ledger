import uuid
from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi import HTTPException

from app.models.enums import UserRole
from app.domain.enums import IncidentStatus
from app.services import writing_service
from app.services.exceptions import InvalidStateError, UnauthorizedError


def _make_user(role: str = "staff") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.center_id = uuid.uuid4()
    user.role = MagicMock()
    user.role.value = role
    return user


def _make_incident(status: str = "draft", restricted: bool = False, creator_id: uuid.UUID = None) -> MagicMock:
    incident = MagicMock()
    incident.id = uuid.uuid4()
    incident.center_id = uuid.uuid4()
    incident.status = MagicMock()
    incident.status.value = status
    incident.restricted = restricted
    incident.created_by_user_id = creator_id or uuid.uuid4()
    incident.submitted_by_user_id = incident.created_by_user_id
    
    incident.category = "injury"
    incident.current_severity = "low"
    incident.event_time_precision = "exact"
    incident.event_at = None
    incident.location = "Playground"
    incident.witnesses_known = False
    incident.original_factual_notes = "Child fell."
    incident.actions_taken = "Ice applied."
    incident.treatment_response = "Child stopped crying."
    
    return incident


class TestGetSuggestions:
    @pytest.mark.asyncio
    async def test_restricted_incident(self) -> None:
        incident_data = {"category": "suspected_abuse_neglect"}
        result = await writing_service.get_suggestions(incident_data)
        assert not result["available"]
        assert result["reason"] == "ASSISTANCE_UNAVAILABLE_FOR_RESTRICTED_INCIDENT"

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        incident_data = {"category": "injury"}
        mock_response = {
            "suggestions": [],
            "model_version": "gemini-2.5-flash",
            "prompt_version": "v1"
        }
        
        with patch("app.services.writing_service.get_writing_suggestions", new_callable=AsyncMock, return_value=mock_response):
            result = await writing_service.get_suggestions(incident_data)
            
            assert result["available"]
            assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_gemini_error(self) -> None:
        incident_data = {"category": "injury"}
        
        with patch("app.services.writing_service.get_writing_suggestions", new_callable=AsyncMock, side_effect=Exception("API Error")):
            result = await writing_service.get_suggestions(incident_data)
            
            assert not result["available"]
            assert result["reason"] == "ASSISTANCE_TEMPORARILY_UNAVAILABLE"


class TestRecordDisposition:
    @pytest.mark.asyncio
    async def test_invalid_disposition(self) -> None:
        session = AsyncMock()
        user = _make_user()
        incident = _make_incident(creator_id=user.id)
        
        request = writing_service.DispositionRequest(
            suggestion_type="clarity_suggestion",
            disposition="invalid_type",
            model_version="gemini",
            prompt_version="v1",
            field_hashes={}
        )
        
        with patch("app.services.writing_service._get_incident_or_raise", return_value=incident):
            with pytest.raises(HTTPException) as exc:
                await writing_service.record_disposition(session, user, incident.id, "sug_01", request)
            assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        session = AsyncMock()
        user = _make_user()
        incident = _make_incident(creator_id=user.id)
        
        request = writing_service.DispositionRequest(
            suggestion_type="clarity_suggestion",
            disposition="accepted",
            model_version="gemini",
            prompt_version="v1",
            field_hashes={"field1": "hash1"}
        )
        
        with patch("app.services.writing_service._get_incident_or_raise", return_value=incident):
            result = await writing_service.record_disposition(session, user, incident.id, "sug_01", request)
            
            assert result["status"] == "recorded"
            session.add.assert_called_once()
            session.flush.assert_called_once()
