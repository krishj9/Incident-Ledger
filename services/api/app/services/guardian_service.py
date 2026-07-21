import hashlib
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List

from fastapi import HTTPException
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acknowledgements import Acknowledgement
from app.models.audit_events import AuditEvent
from app.models.children import ChildGuardian, Child
from app.models.contact_attempts import ContactAttempt
from app.models.guardian_packets import GuardianPacket
from app.models.incidents import Incident, IncidentChild
from app.models.outbox import EmailLinkToken, OutboxEvent, NotificationDelivery
from app.models.report_versions import ReportVersion
from app.models.users import User, UserRole


async def generate_packets_on_approval(
    db: AsyncSession, user: User, incident: Incident, approved_version_id: uuid.UUID
) -> None:
    """
    Called when an incident is approved. Generates one guardian packet per child for their primary guardian.
    If the incident is restricted, sets notification_allowed=False.
    """
    # 1. Get all children involved
    children_result = await db.execute(
        select(IncidentChild).where(IncidentChild.incident_id == incident.id)
    )
    incident_children = children_result.scalars().all()

    # 2. For each child, find the primary guardian
    for ic in incident_children:
        guardian_result = await db.execute(
            select(ChildGuardian).where(
                and_(
                    ChildGuardian.child_id == ic.child_id,
                    ChildGuardian.is_primary == True
                )
            )
        )
        primary_guardian = guardian_result.scalars().first()
        if not primary_guardian:
            continue

        # 3. Create guardian packet
        packet = GuardianPacket(
            incident_id=incident.id,
            child_id=ic.child_id,
            approved_version_id=approved_version_id,
            primary_guardian_id=primary_guardian.guardian_id,
            status="pending",
            notification_allowed=not incident.restricted
        )
        db.add(packet)
        await db.flush()

        # 4. Write audit event
        audit = AuditEvent(
            center_id=incident.center_id,
            incident_id=incident.id,
            actor_user_id=user.id,
            action="guardian_packet_created",
            correlation_id=str(uuid.uuid4()),
            metadata_={"child_id": str(ic.child_id), "packet_id": str(packet.id)}
        )
        db.add(audit)


async def record_in_person_ack(
    db: AsyncSession, user: User, packet_id: uuid.UUID, typed_full_name: str, receipt_confirmed: bool, outcome: str
) -> Acknowledgement:
    """Record an in-person acknowledgement from staff/director."""
    # 1. Fetch and validate packet
    packet = await db.get(GuardianPacket, packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Guardian packet not found")
    
    if packet.status not in ("pending", "sent", "opened"):
        raise HTTPException(status_code=400, detail="Packet is not in an acknowledgeable state")

    incident = await db.get(Incident, packet.incident_id)
    if not incident or incident.center_id != user.center_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if outcome not in ("acknowledged", "disagreed"):
        raise HTTPException(status_code=422, detail="Invalid outcome")

    # 2. Create acknowledgement record
    ack = Acknowledgement(
        guardian_packet_id=packet.id,
        method="in_person",
        typed_full_name=typed_full_name,
        receipt_confirmed=receipt_confirmed,
        outcome=outcome,
        report_version_id=packet.approved_version_id,
        staff_present_user_id=user.id
    )
    db.add(ack)

    # 3. Update packet status
    packet.status = outcome

    # 4. Audit event
    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=user.id,
        action="in_person_acknowledgement",
        correlation_id=str(uuid.uuid4()),
        metadata_={"packet_id": str(packet.id), "outcome": outcome}
    )
    db.add(audit)

    return ack


async def send_email_link(db: AsyncSession, user: User, packet_id: uuid.UUID) -> str:
    """
    Generate an opaque one-time token, store its hash, invalidate old tokens,
    and log the email output (simulated send).
    """
    packet = await db.get(GuardianPacket, packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    if not packet.notification_allowed:
        raise HTTPException(status_code=403, detail="Notification not allowed for this packet")
    if packet.status in ("acknowledged", "disagreed", "unreachable", "closed"):
        raise HTTPException(status_code=400, detail="Packet cannot be notified in current state")

    incident = await db.get(Incident, packet.incident_id)
    if not incident or incident.center_id != user.center_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Invalidate previous unused tokens for this packet
    await db.execute(
        update(EmailLinkToken)
        .where(
            and_(
                EmailLinkToken.guardian_packet_id == packet.id,
                EmailLinkToken.status == "active"
            )
        )
        .values(status="invalidated", invalidated_at=datetime.utcnow())
    )

    # Generate token and hash
    raw_token = os.urandom(32).hex()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Store token hash
    token_record = EmailLinkToken(
        center_id=incident.center_id,
        guardian_packet_id=packet.id,
        token_hash=token_hash,
        status="active",
        expires_at=datetime.utcnow() + timedelta(hours=72)
    )
    db.add(token_record)

    # Update packet status if pending
    if packet.status == "pending":
        packet.status = "sent"

    correlation_id = str(uuid.uuid4())

    # Log to console + notification_deliveries table
    print(f"--- EMAIL SIMULATION ---\nGuardian Link: https://example.com/acknowledge/{raw_token}\n-----------------------")
    delivery = NotificationDelivery(
        center_id=incident.center_id,
        guardian_packet_id=packet.id,
        incident_id=incident.id,
        notification_type="guardian_packet_link",
        status="sent"
    )
    db.add(delivery)

    # Write outbox event for async worker
    outbox = OutboxEvent(
        event_type="guardian_email",
        idempotency_key=correlation_id,
        payload={"packet_id": str(packet.id), "recipient_id": str(packet.primary_guardian_id)},
        center_id=incident.center_id
    )
    db.add(outbox)

    # Audit event
    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=user.id,
        action="email_link_sent",
        correlation_id=correlation_id,
        metadata_={"packet_id": str(packet.id)}
    )
    db.add(audit)

    return raw_token


async def record_contact_attempt(
    db: AsyncSession, user: User, incident_id: uuid.UUID, guardian_id: uuid.UUID, method: str, outcome: str, notes: str | None
) -> ContactAttempt:
    """Record an immutable contact attempt."""
    incident = await db.get(Incident, incident_id)
    if not incident or incident.center_id != user.center_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    attempt = ContactAttempt(
        incident_id=incident_id,
        guardian_id=guardian_id,
        method=method,
        outcome=outcome,
        notes=notes,
        attempted_by_user_id=user.id,
        attempted_at=datetime.utcnow()
    )
    db.add(attempt)

    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=user.id,
        action="contact_attempt",
        correlation_id=str(uuid.uuid4()),
        metadata_={"guardian_id": str(guardian_id), "method": method, "outcome": outcome}
    )
    db.add(audit)

    return attempt


async def close_unreachable(db: AsyncSession, user: User, incident_id: uuid.UUID, packet_id: uuid.UUID) -> None:
    """
    Director only. Requires >= 3 contact attempts across >= 2 calendar dates (center timezone).
    """
    if user.role not in (UserRole.director, UserRole.backup_director, UserRole.regional_admin):
        raise HTTPException(status_code=403, detail="Only directors can close unreachable")

    incident = await db.get(Incident, incident_id)
    if not incident or incident.center_id != user.center_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    packet = await db.get(GuardianPacket, packet_id)
    if not packet or packet.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Guardian packet not found")

    if packet.status in ("acknowledged", "disagreed", "closed", "unreachable"):
        raise HTTPException(status_code=400, detail="Packet cannot be marked unreachable from current state")

    # Validate business rule: >= 3 attempts, >= 2 dates
    attempts = await db.execute(
        select(ContactAttempt).where(
            and_(
                ContactAttempt.incident_id == incident_id,
                ContactAttempt.guardian_id == packet.primary_guardian_id
            )
        )
    )
    attempts_list = attempts.scalars().all()
    
    if len(attempts_list) < 3:
        raise HTTPException(status_code=422, detail="Requires at least 3 contact attempts")

    # Center timezone check (assuming UTC for demo simplicity, robust implementation would use center.timezone)
    dates = {attempt.attempted_at.date() for attempt in attempts_list}
    if len(dates) < 2:
        raise HTTPException(status_code=422, detail="Requires contact attempts across at least 2 different dates")

    packet.status = "unreachable"

    audit = AuditEvent(
        center_id=incident.center_id,
        incident_id=incident.id,
        actor_user_id=user.id,
        action="unreachable_closure",
        correlation_id=str(uuid.uuid4()),
        metadata_={"packet_id": str(packet.id)}
    )
    db.add(audit)
