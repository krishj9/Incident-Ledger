import uuid
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incidents import Incident
from app.models.users import User
from app.domain.enums import SeverityLevel, InvolvementRole, IncidentStatus
from app.services import incident_service, review_service, guardian_service, legal_hold_service

async def _submit(session, user, incident_id, corr_id, idemp_key, offline=False):
    return await incident_service.submit(
        session, user, incident_id,
        attestation={"accurate_to_best_of_knowledge": True, "confirmed_at": datetime.now(UTC).isoformat()},
        device_info={"device_id": str(uuid.uuid4()), "offline_originated": offline},
        correlation_id=corr_id, idempotency_key=idemp_key
    )

async def _scenario_exists(session: AsyncSession, incident_id: uuid.UUID) -> bool:
    stmt = select(Incident).where(Incident.id == incident_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None

async def _get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one()

async def seed_scenarios(session: AsyncSession, user_ids: dict[str, uuid.UUID], det_uuid, SEED_VERSION, CENTER_ID) -> None:
    print("\n  Seeding scenarios (S01-S12)...")
    
    # Common variables
    staff_alex = await _get_user(session, user_ids["alex-kim"])
    director_maya = await _get_user(session, user_ids["maya-chen"])
    compliance = await _get_user(session, user_ids["riley-morgan"])
    
    child1_id = det_uuid("child", "child-01")
    child2_id = det_uuid("child", "child-02")
    child3_id = det_uuid("child", "child-03")
    
    corr_id = f"seed-v{SEED_VERSION}"
    
    # S01: Low injury, one child, in-person receipt
    s01_id = det_uuid("incident", "S01")
    if not await _scenario_exists(session, s01_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "low", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s01-create-v{SEED_VERSION}",
            id=s01_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S01: Child fell and scraped knee.",
            actions_taken="Cleaned and applied bandage.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s01-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)
        
        # acknowledge in person
        from app.models.guardian_packets import GuardianPacket
        stmt = select(GuardianPacket).where(GuardianPacket.incident_id == inc.id)
        packet = (await session.execute(stmt)).scalar_one()
        await guardian_service.record_in_person_ack(session, director_maya, packet.id, "Demo Guardian", True, "acknowledged")
        
        # Close incident
        inc.status = IncidentStatus.closed
        inc.closed_at = datetime.now(UTC)
        session.add(inc)

    # S02: Moderate behavior, two children
    s02_id = det_uuid("incident", "S02")
    if not await _scenario_exists(session, s02_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "behavior", "moderate", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected},
             {"child_id": child2_id, "role": InvolvementRole.involved}],
            corr_id, f"s02-create-v{SEED_VERSION}",
            id=s02_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Classroom",
            original_factual_notes="SCENARIO S02: Two children involved in a behavior incident.",
            actions_taken="Separated and redirected.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s02-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)

    # S03: High illness
    s03_id = det_uuid("incident", "S03")
    if not await _scenario_exists(session, s03_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "illness", "high", 
            [{"child_id": child3_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s03-create-v{SEED_VERSION}",
            id=s03_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Classroom",
            original_factual_notes="SCENARIO S03: Child has high fever.",
            actions_taken="Moved to isolation area, called guardian.",
            witnesses_known=False
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s03-submit-v{SEED_VERSION}")

    # S04: Critical medication error
    s04_id = det_uuid("incident", "S04")
    if not await _scenario_exists(session, s04_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "medication_error", "critical", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s04-create-v{SEED_VERSION}",
            id=s04_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Clinic",
            original_factual_notes="SCENARIO S04: Wrong dosage administered.",
            actions_taken="Called poison control.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s04-submit-v{SEED_VERSION}")

    # S05: Offline injury with image
    s05_id = det_uuid("incident", "S05")
    if not await _scenario_exists(session, s05_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "low", 
            [{"child_id": child2_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s05-create-v{SEED_VERSION}",
            id=s05_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S05: Scraped elbow.",
            actions_taken="Applied bandage.",
            witnesses_known=True
        )
        # Mock evidence
        from app.models.evidence import EvidenceItem
        ev = EvidenceItem(
            incident_id=inc.id, capture_user_id=staff_alex.id,
            capture_device_id=det_uuid("device", "dev-alex-iphone"),
            media_type="image/jpeg", byte_size=1024,
            storage_object_uri=f"demo/{inc.id}/mock.jpg",
            sha256="mockhash", captured_at=datetime.now(UTC),
            upload_status="ready", finalized_at=datetime.now(UTC)
        )
        session.add(ev)
        await _submit(session, staff_alex, inc.id, corr_id, f"s05-submit-v{SEED_VERSION}", offline=True)

    # S06: Returned factual clarification
    s06_id = det_uuid("incident", "S06")
    if not await _scenario_exists(session, s06_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "low", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s06-create-v{SEED_VERSION}",
            id=s06_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S06: Clarification needed.",
            actions_taken="Bandage.",
            witnesses_known=False
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s06-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.request_changes(session, director_maya, inc.id, "Please add more details about location", corr_id)
        # Leave in changes_requested for demo

    # S07: Director neutral wording edit
    s07_id = det_uuid("incident", "S07")
    if not await _scenario_exists(session, s07_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "behavior", "moderate", 
            [{"child_id": child2_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s07-create-v{SEED_VERSION}",
            id=s07_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Classroom",
            original_factual_notes="SCENARIO S07: Child went crazy and broke a toy.",
            actions_taken="Time out.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s07-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.create_director_edit(session, director_maya, inc.id, "Child became upset and broke a toy.", "Removed subjective language", corr_id)

    # S08: Post-approval correction
    s08_id = det_uuid("incident", "S08")
    if not await _scenario_exists(session, s08_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "low", 
            [{"child_id": child3_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s08-create-v{SEED_VERSION}",
            id=s08_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S08: Child fell.",
            actions_taken="Ice pack.",
            witnesses_known=False
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s08-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)
        await review_service.create_addendum(session, director_maya, inc.id, "Corrected time of incident: Was 2PM, not 3PM.", corr_id)
        
        # Close incident to keep exactly 1 guardian_ack_pending (S02)
        inc.status = IncidentStatus.closed
        inc.closed_at = datetime.now(UTC)
        session.add(inc)

    # S09: Email link expiry/resend/disagreement
    s09_id = det_uuid("incident", "S09")
    if not await _scenario_exists(session, s09_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "behavior", "low", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s09-create-v{SEED_VERSION}",
            id=s09_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Classroom",
            original_factual_notes="SCENARIO S09: Disagreement test.",
            actions_taken="Talked with child.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s09-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)
        
        # Simulate disagreement on token
        from app.models.guardian_packets import GuardianPacket
        stmt = select(GuardianPacket).where(GuardianPacket.incident_id == inc.id)
        packet = (await session.execute(stmt)).scalar_one()
        
        await guardian_service.send_email_link(session, director_maya, packet.id)
        
        packet.status = "acknowledged"
        packet.acknowledgement_outcome = "disagreed"
        packet.acknowledged_at = datetime.now(UTC)
        session.add(packet)
        
        inc.status = IncidentStatus.acknowledged
        session.add(inc)

    # S10: Three attempts/two dates
    s10_id = det_uuid("incident", "S10")
    if not await _scenario_exists(session, s10_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "low", 
            [{"child_id": child2_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s10-create-v{SEED_VERSION}",
            id=s10_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S10: Three attempts test.",
            actions_taken="Bandage.",
            witnesses_known=False
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s10-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)
        
        from app.models.guardian_packets import GuardianPacket
        from app.models.contact_attempts import ContactAttempt
        stmt = select(GuardianPacket).where(GuardianPacket.incident_id == inc.id)
        packet = (await session.execute(stmt)).scalar_one()
        
        # 1. First attempt
        await guardian_service.record_contact_attempt(session, director_maya, inc.id, packet.primary_guardian_id, "email", "left_message", "Attempt 1")
        # 2. Second attempt (pretend different date by setting it back)
        import datetime as dt
        ca2 = ContactAttempt(incident_id=inc.id, guardian_id=packet.primary_guardian_id, attempted_by_user_id=director_maya.id, method="phone", outcome="left_message", notes="Attempt 2", attempted_at=datetime.now(UTC)-dt.timedelta(days=1))
        session.add(ca2)
        # 3. Third attempt
        ca3 = ContactAttempt(incident_id=inc.id, guardian_id=packet.primary_guardian_id, attempted_by_user_id=director_maya.id, method="phone", outcome="no_answer", notes="Attempt 3", attempted_at=datetime.now(UTC)-dt.timedelta(days=2))
        session.add(ca3)
        await session.flush()
        
        # Close unreachable
        await guardian_service.close_unreachable(session, director_maya, inc.id, packet.id)
        
        inc.status = IncidentStatus.ack_unreachable
        session.add(inc)

    # S11: Suspected abuse/neglect
    s11_id = det_uuid("incident", "S11")
    if not await _scenario_exists(session, s11_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "suspected_abuse_neglect", "critical", 
            [{"child_id": child1_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s11-create-v{SEED_VERSION}",
            id=s11_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Arrival",
            original_factual_notes="SCENARIO S11: Unexplained bruising.",
            actions_taken="Notified CPS.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s11-submit-v{SEED_VERSION}")

    # S12: Legal hold
    s12_id = det_uuid("incident", "S12")
    if not await _scenario_exists(session, s12_id):
        inc = await incident_service.create_draft(
            session, staff_alex, CENTER_ID, "injury", "high", 
            [{"child_id": child3_id, "role": InvolvementRole.primary_affected}],
            corr_id, f"s12-create-v{SEED_VERSION}",
            id=s12_id,
            event_at=datetime.now(UTC),
            event_time_precision="exact",
            location="Playground",
            original_factual_notes="SCENARIO S12: Broken arm.",
            actions_taken="Called ambulance.",
            witnesses_known=True
        )
        await _submit(session, staff_alex, inc.id, corr_id, f"s12-submit-v{SEED_VERSION}")
        await review_service.acknowledge_review(session, director_maya, inc.id, corr_id)
        await review_service.approve(session, director_maya, inc.id, corr_id)
        # Close incident
        inc.status = IncidentStatus.closed
        inc.closed_at = datetime.now(UTC)
        session.add(inc)
        await session.flush()
        
        await legal_hold_service.apply_legal_hold(session, compliance, inc.id, "Pending litigation", corr_id)

    await session.commit()
    print("  ✓ Scenarios created successfully.")
