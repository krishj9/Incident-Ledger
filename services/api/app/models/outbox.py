"""
Additional tables (§Additional required tables from db-schema.md):
  category_responses, review_actions, email_link_tokens, notification_deliveries,
  outbox_events, legal_holds, retention_disposals, assistant_interactions, report_views

All follow the same center_id scoping and immutable-event patterns as core tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid7


# ── CategoryResponse ──────────────────────────────────────────────────────────

class CategoryResponse(Base):
    """
    Center-configurable category-specific response requirements
    (e.g., which categories allow photos, require structured observation).
    Mutable by center admin.
    """

    __tablename__ = "category_responses"
    __table_args__ = (
        UniqueConstraint("center_id", "category", name="uq_category_responses_center_cat"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    photo_permitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_assistance_permitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    structured_observation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # type: ignore[type-arg]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── ReviewAction ─────────────────────────────────────────────────────────────

class ReviewAction(Base):
    """
    Immutable record of every director/compliance action taken during review.
    Separate from audit_events to allow structured querying of review steps.
    """

    __tablename__ = "review_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. acknowledge_review, request_changes, edit_narrative, change_severity, approve
    report_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── EmailLinkToken ────────────────────────────────────────────────────────────

class EmailLinkToken(Base):
    """
    One-time guardian email link token.
    STORES TOKEN HASH ONLY — never the raw token.
    Single-use; 72-hour expiry. Resend invalidates prior unused token.
    """

    __tablename__ = "email_link_tokens"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'used', 'expired', 'invalidated')",
            name="ck_email_link_tokens_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    guardian_packet_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardian_packets.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Raw token is NEVER stored. token_hash = SHA-256 of the raw opaque token.
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ── NotificationDelivery ──────────────────────────────────────────────────────

class NotificationDelivery(Base):
    """
    Immutable record of every notification attempt (email, alert).
    In demo environment: console/DB logging only, no actual email sending.
    """

    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True
    )
    guardian_packet_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("guardian_packets.id"), nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. director_alert, guardian_email, backup_escalation, regional_escalation
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    recipient_email_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 of recipient email; never store raw
    status: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. logged, sent, delivered, failed
    outbox_event_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── OutboxEvent ───────────────────────────────────────────────────────────────

class OutboxEvent(Base):
    """
    Transactional outbox for durable domain events (per architecture.md).
    Worker claims and processes events idempotently via Cloud Tasks.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'claimed', 'processed', 'failed')",
            name="ck_outbox_events_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. director_alert, guardian_email, backup_escalation, token_expiry, retention_check
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # Derived from event ID; used for Cloud Tasks task name deduplication.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_id: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── LegalHold ────────────────────────────────────────────────────────────────

class LegalHold(Base):
    """
    Immutable record of legal hold application.
    legal_hold flag on incidents is the enforcement point;
    this table provides the audit trail of who applied it and why.
    """

    __tablename__ = "legal_holds"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    applied_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Holds cannot be removed in this system (immutable) — a separate release record
    # would need compliance authorization; out of scope for demo.


# ── RetentionDisposal ─────────────────────────────────────────────────────────

class RetentionDisposal(Base):
    """
    Immutable record of retention evaluation outcomes.
    In demo: records eligibility only — does NOT actually delete data.
    legal_hold=true blocks eligibility.
    """

    __tablename__ = "retention_disposals"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    retention_years: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    eligible_for_disposal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocked_by_legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disposal_note: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── AssistantInteraction ──────────────────────────────────────────────────────

class AssistantInteraction(Base):
    """
    Immutable record of writing assistance suggestion dispositions.
    Persists: suggestion_id, disposition, actor, timestamp, model/prompt versions,
    field hashes. Does NOT persist raw prompts.
    """

    __tablename__ = "assistant_interactions"
    __table_args__ = (
        CheckConstraint(
            "disposition IN ('accepted', 'rejected', 'edited')",
            name="ck_assistant_interactions_disposition",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    suggestion_id: Mapped[str] = mapped_column(String, nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String, nullable=False)
    disposition: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    field_hashes: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    # SHA-256 hashes of input fields — not raw content.
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── ReportView ────────────────────────────────────────────────────────────────

class ReportView(Base):
    """
    Immutable audit record of every time a report was viewed by a user.
    Used for access audit trail per data-model.md §Audit model.
    """

    __tablename__ = "report_views"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    center_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("centers.id"), nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    viewer_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    report_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_versions.id"), nullable=True
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    access_context: Mapped[str | None] = mapped_column(String, nullable=True)
    # e.g. 'director_review', 'compliance_audit', 'guardian_packet'
