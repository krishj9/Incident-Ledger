from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import IncidentCategory, IncidentStatus, InvolvementRole, SeverityLevel, TimePrecision


class FieldError(BaseModel):
    path: str
    code: str


class IncidentChildDraft(BaseModel):
    child_id: uuid.UUID
    role: InvolvementRole


class IncidentCreate(BaseModel):
    category: IncidentCategory | None = None
    severity: SeverityLevel | None = None
    children: list[IncidentChildDraft] = Field(default_factory=list)


class IncidentDraftUpdate(BaseModel):
    category: IncidentCategory | None = None
    severity: SeverityLevel | None = None
    event_at: datetime | None = None
    event_time_precision: TimePrecision | None = None
    location: str | None = None
    original_factual_notes: str | None = None
    actions_taken: str | None = None
    treatment_response: str | None = None
    witnesses_known: bool | None = None
    children: list[IncidentChildDraft] | None = None


class StaffAttestation(BaseModel):
    accurate_to_best_of_knowledge: bool
    confirmed_at: datetime


class DeviceInfo(BaseModel):
    device_id: uuid.UUID
    offline_originated: bool


class IncidentSubmit(BaseModel):
    staff_attestation: StaffAttestation
    submitted_from: DeviceInfo


class AssignedReviewer(BaseModel):
    user_id: uuid.UUID
    display_name: str


class SubmitResponse(BaseModel):
    incident_id: uuid.UUID
    status: IncidentStatus
    server_received_at: datetime
    sync_state: str
    assigned_reviewer: AssignedReviewer | None = None
    version_etag: str | None = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: IncidentStatus
    category: IncidentCategory
    severity: SeverityLevel
    event_at: datetime | None = None
    location: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    first_child_name: str | None = None
    version_etag: str | None = None


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]


class SyncOperationItem(BaseModel):
    operation_id: str
    operation_type: str
    payload: dict[str, Any]
    payload_sha256: str


class SyncOperationsRequest(BaseModel):
    operations: list[SyncOperationItem]
