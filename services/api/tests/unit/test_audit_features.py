import uuid
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.audit.exporter import build_audit_packet
from app.services.legal_hold_service import apply_legal_hold
from app.workers.retention import process_retention_disposals
from app.services.operations_service import get_health_stats
from app.models.enums import IncidentStatus


def _make_user(role: str = "director") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.center_id = uuid.uuid4()
    user.role = MagicMock()
    user.role.value = role
    return user


def _make_incident(legal_hold: bool = False, status: IncidentStatus = IncidentStatus.closed) -> MagicMock:
    incident = MagicMock()
    incident.id = uuid.uuid4()
    incident.center_id = uuid.uuid4()
    incident.status = status
    incident.legal_hold = legal_hold
    incident.children = []
    return incident


class TestAuditExporter:
    @pytest.mark.asyncio
    async def test_build_audit_packet_not_found(self) -> None:
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Incident not found"):
            await build_audit_packet(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "corr-id")


class TestLegalHoldService:
    @pytest.mark.asyncio
    async def test_apply_legal_hold_requires_reason(self) -> None:
        session = AsyncMock()
        user = _make_user()
        
        with pytest.raises(ValueError, match="Legal hold reason is required"):
            await apply_legal_hold(session, user, uuid.uuid4(), "", "corr-id")
            
    @pytest.mark.asyncio
    async def test_apply_legal_hold_success(self) -> None:
        session = AsyncMock()
        user = _make_user()
        incident = _make_incident(legal_hold=False)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = incident
        session.execute.return_value = mock_result
        
        with patch("app.services.legal_hold_service.record_audit_event", new_callable=AsyncMock) as mock_audit:
            result = await apply_legal_hold(session, user, incident.id, "Pending litigation", "corr-id")
            
            assert result["status"] == "applied"
            assert incident.legal_hold is True
            session.add.assert_called()
            mock_audit.assert_called_once()


class TestRetentionWorker:
    @pytest.mark.asyncio
    async def test_process_retention_skips_legal_hold(self) -> None:
        session = AsyncMock()
        
        # Two incidents, one on hold
        inc1 = _make_incident(legal_hold=True)
        inc2 = _make_incident(legal_hold=False)
        
        mock_incidents_result = MagicMock()
        mock_incidents_result.scalars.return_value.all.return_value = [inc1, inc2]
        
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = None
        
        session.execute.side_effect = [
            mock_incidents_result, # query incidents
            mock_check_result, # check inc1
            mock_check_result, # check inc2
        ]
        
        with patch("app.workers.retention.record_audit_event", new_callable=AsyncMock):
            count = await process_retention_disposals(session, uuid.uuid4(), "corr-id")
            assert count == 2
            
            # verify session.add was called with RetentionDisposal
            adds = session.add.call_args_list
            assert len(adds) == 2
            
            # first add is inc1 (hold)
            assert adds[0][0][0].blocked_by_legal_hold is True
            assert adds[0][0][0].eligible_for_disposal is False
            
            # second add is inc2 (no hold)
            assert adds[1][0][0].blocked_by_legal_hold is False
            assert adds[1][0][0].eligible_for_disposal is True
