import uuid
import pytest
import pytest_asyncio
from datetime import datetime, UTC, timedelta
from fastapi import HTTPException
from sqlalchemy import select, and_

from app.models.acknowledgements import Acknowledgement
from app.models.audit_events import AuditEvent
from app.models.centers import Center
from app.models.children import Child, ChildGuardian, Guardian
from app.models.contact_attempts import ContactAttempt
from app.models.guardian_packets import GuardianPacket
from app.models.incidents import Incident, IncidentChild
from app.models.outbox import EmailLinkToken, NotificationDelivery, OutboxEvent
from app.models.report_versions import ReportVersion
from app.models.users import User, UserRole
from app.services import guardian_service

def create_valid_incident(center_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Incident:
    return Incident(
        id=kwargs.get("id", uuid.uuid4()),
        center_id=center_id,
        category=kwargs.get("category", "injury"),
        staff_selected_severity=kwargs.get("staff_selected_severity", "moderate"),
        current_severity=kwargs.get("current_severity", "moderate"),
        event_at=kwargs.get("event_at", datetime.now(UTC)),
        event_time_precision=kwargs.get("event_time_precision", "exact"),
        location=kwargs.get("location", "playground"),
        original_factual_notes=kwargs.get("original_factual_notes", "notes"),
        actions_taken=kwargs.get("actions_taken", "first aid"),
        witnesses_known=kwargs.get("witnesses_known", False),
        restricted=kwargs.get("restricted", False),
        created_by_user_id=user_id,
        status=kwargs.get("status", "approved")
    )

@pytest_asyncio.fixture
async def mock_director(db_session):
    center = Center(id=uuid.uuid4(), code=str(uuid.uuid4())[:10], name="Test Center", timezone="UTC")
    user = User(id=uuid.uuid4(), center_id=center.id, external_subject=str(uuid.uuid4()), display_name="Mock Director", role=UserRole.director)
    db_session.add_all([center, user])
    await db_session.commit()
    return user

@pytest_asyncio.fixture
async def mock_staff(db_session):
    center = Center(id=uuid.uuid4(), code=str(uuid.uuid4())[:10], name="Test Center", timezone="UTC")
    user = User(id=uuid.uuid4(), center_id=center.id, external_subject=str(uuid.uuid4()), display_name="Mock Staff", role=UserRole.staff)
    db_session.add_all([center, user])
    await db_session.commit()
    return user

@pytest.mark.asyncio
class TestGeneratePackets:
    async def test_generate_packets_multi_child(self, db_session, mock_director):
        # Setup incident
        incident = create_valid_incident(mock_director.center_id, mock_director.id, restricted=False)
        db_session.add(incident)

        # Child 1 & Guardian
        c1 = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Child 1")
        g1 = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="G1", email="g1@example.com")
        db_session.add_all([c1, g1])
        await db_session.flush()
        cg1 = ChildGuardian(child_id=c1.id, guardian_id=g1.id, is_primary=True)
        ic1 = IncidentChild(incident_id=incident.id, child_id=c1.id, involvement_role="primary_affected")

        # Child 2 & Guardian (Not primary) -> should skip
        c2 = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Child 2")
        g2 = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="G2", email="g2@example.com")
        db_session.add_all([c2, g2])
        await db_session.flush()
        cg2 = ChildGuardian(child_id=c2.id, guardian_id=g2.id, is_primary=False)
        ic2 = IncidentChild(incident_id=incident.id, child_id=c2.id, involvement_role="involved")

        # Child 3 & Guardian
        c3 = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Child 3")
        g3 = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="G3", email="g3@example.com")
        db_session.add_all([c3, g3])
        await db_session.flush()
        cg3 = ChildGuardian(child_id=c3.id, guardian_id=g3.id, is_primary=True)
        ic3 = IncidentChild(incident_id=incident.id, child_id=c3.id, involvement_role="witness")

        db_session.add_all([cg1, ic1, cg2, ic2, cg3, ic3])
        await db_session.commit()

        version = ReportVersion(
            id=uuid.uuid4(), incident_id=incident.id, version_number=1, version_kind="approved",
            created_by_user_id=mock_director.id, original_staff_notes="", rendered_narrative="",
            structured_snapshot={}, content_sha256="hash"
        )
        db_session.add(version)
        await db_session.commit()
        
        await guardian_service.generate_packets_on_approval(db_session, mock_director, incident, version.id)

        # Verify packets
        res = await db_session.execute(select(GuardianPacket).where(GuardianPacket.incident_id == incident.id))
        packets = res.scalars().all()

        assert len(packets) == 2
        packet_child_ids = {p.child_id for p in packets}
        assert c1.id in packet_child_ids
        assert c3.id in packet_child_ids
        assert c2.id not in packet_child_ids

        for p in packets:
            assert p.notification_allowed is True
            assert p.status == "pending"


    async def test_generate_packets_restricted(self, db_session, mock_director):
        incident = create_valid_incident(mock_director.center_id, mock_director.id, category="suspected_abuse_neglect", restricted=True)
        db_session.add(incident)

        c1 = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Child 1")
        g1 = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="G1", email="g1@example.com")
        db_session.add_all([c1, g1])
        await db_session.flush()
        cg1 = ChildGuardian(child_id=c1.id, guardian_id=g1.id, is_primary=True)
        ic1 = IncidentChild(incident_id=incident.id, child_id=c1.id, involvement_role="primary_affected")

        db_session.add_all([cg1, ic1])
        await db_session.commit()

        version = ReportVersion(
            id=uuid.uuid4(), incident_id=incident.id, version_number=1, version_kind="approved",
            created_by_user_id=mock_director.id, original_staff_notes="", rendered_narrative="",
            structured_snapshot={}, content_sha256="hash"
        )
        db_session.add(version)
        await db_session.commit()

        await guardian_service.generate_packets_on_approval(db_session, mock_director, incident, version.id)

        res = await db_session.execute(select(GuardianPacket).where(GuardianPacket.incident_id == incident.id))
        packet = res.scalars().first()
        assert packet.notification_allowed is False


@pytest.mark.asyncio
class TestSendEmailLink:
    async def test_email_link_invalidates_previous_and_hashes(self, db_session, mock_director):
        incident = create_valid_incident(mock_director.center_id, mock_director.id)
        version = ReportVersion(
            id=uuid.uuid4(), incident_id=incident.id, version_number=1, version_kind="approved",
            created_by_user_id=mock_director.id, original_staff_notes="", rendered_narrative="",
            structured_snapshot={}, content_sha256="hash"
        )
        db_session.add_all([incident, version])
        await db_session.flush()

        child = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Test Child", active=True, synthetic_marker=True)
        guardian = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Test Guardian", email="test@example.com", synthetic_marker=True)
        db_session.add_all([child, guardian])
        await db_session.flush()

        packet = GuardianPacket(
            id=uuid.uuid4(), incident_id=incident.id, child_id=child.id,
            approved_version_id=version.id, primary_guardian_id=guardian.id,
            status="pending", notification_allowed=True
        )
        db_session.add(packet)

        # Pre-existing active token
        old_token = EmailLinkToken(
            center_id=incident.center_id, guardian_packet_id=packet.id, token_hash=uuid.uuid4().hex,
            status="active", expires_at=datetime.now(UTC) + timedelta(hours=10)
        )
        db_session.add(old_token)
        await db_session.commit()

        raw_token = await guardian_service.send_email_link(db_session, mock_director, packet.id)
        await db_session.flush()

        # Check old token invalidated
        await db_session.refresh(old_token)
        assert old_token.status == "invalidated"
        assert old_token.invalidated_at is not None

        # Check new token active and hashed correctly
        res = await db_session.execute(select(EmailLinkToken).where(EmailLinkToken.status == "active").where(EmailLinkToken.guardian_packet_id == packet.id))
        new_token = res.scalars().first()
        
        import hashlib
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert new_token.token_hash == expected_hash
        assert raw_token != expected_hash  # Raw token must not be the hash

        assert packet.status == "sent"

        # Check outbox event
        res = await db_session.execute(select(OutboxEvent).where(OutboxEvent.event_type == "guardian_email"))
        outbox = res.scalars().first()
        assert outbox is not None


@pytest.mark.asyncio
class TestCloseUnreachable:
    async def test_close_unreachable_requires_director(self, db_session, mock_staff):
        with pytest.raises(HTTPException) as exc:
            await guardian_service.close_unreachable(db_session, mock_staff, uuid.uuid4(), uuid.uuid4())
        assert exc.value.status_code == 403

    async def test_close_unreachable_requires_3_attempts_2_dates(self, db_session, mock_director):
        incident = create_valid_incident(mock_director.center_id, mock_director.id)
        version = ReportVersion(
            id=uuid.uuid4(), incident_id=incident.id, version_number=1, version_kind="approved",
            created_by_user_id=mock_director.id, original_staff_notes="", rendered_narrative="",
            structured_snapshot={}, content_sha256="hash"
        )
        db_session.add_all([incident, version])
        await db_session.flush()

        child = Child(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Test Child", active=True, synthetic_marker=True)
        guardian = Guardian(id=uuid.uuid4(), center_id=mock_director.center_id, display_name="Test Guardian", email="test@example.com", synthetic_marker=True)
        db_session.add_all([child, guardian])
        await db_session.flush()

        packet = GuardianPacket(
            id=uuid.uuid4(), incident_id=incident.id, child_id=child.id,
            approved_version_id=version.id, primary_guardian_id=guardian.id,
            status="sent", notification_allowed=True
        )
        db_session.add(packet)
        await db_session.commit()

        # Try with 0 attempts
        with pytest.raises(HTTPException) as exc:
            await guardian_service.close_unreachable(db_session, mock_director, incident.id, packet.id)
        assert exc.value.status_code == 422
        assert "3 contact attempts" in exc.value.detail

        # Add 3 attempts on SAME date
        today = datetime.now(UTC)
        a1 = ContactAttempt(incident_id=incident.id, guardian_id=packet.primary_guardian_id, method="phone", outcome="no_answer", attempted_by_user_id=mock_director.id, attempted_at=today)
        a2 = ContactAttempt(incident_id=incident.id, guardian_id=packet.primary_guardian_id, method="phone", outcome="no_answer", attempted_by_user_id=mock_director.id, attempted_at=today + timedelta(hours=1))
        a3 = ContactAttempt(incident_id=incident.id, guardian_id=packet.primary_guardian_id, method="phone", outcome="no_answer", attempted_by_user_id=mock_director.id, attempted_at=today + timedelta(hours=2))
        db_session.add_all([a1, a2, a3])
        await db_session.commit()

        # Try with 3 attempts on same date
        with pytest.raises(HTTPException) as exc:
            await guardian_service.close_unreachable(db_session, mock_director, incident.id, packet.id)
        assert exc.value.status_code == 422
        assert "2 different dates" in exc.value.detail

        # Add 4th attempt on different date
        a4 = ContactAttempt(incident_id=incident.id, guardian_id=packet.primary_guardian_id, method="phone", outcome="no_answer", attempted_by_user_id=mock_director.id, attempted_at=today - timedelta(days=1))
        db_session.add(a4)
        await db_session.commit()

        # Should succeed now
        await guardian_service.close_unreachable(db_session, mock_director, incident.id, packet.id)
        assert packet.status == "unreachable"
