from __future__ import annotations

import uuid
from typing import Any
import structlog
from datetime import datetime, UTC

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.repositories import sync_operations as sync_repo
from app.services import incident_service
from app.api.schemas.incidents import (
    SyncOperationItem,
    IncidentCreate,
    IncidentDraftUpdate,
    IncidentSubmit,
)
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import ValidationFailedError

logger = structlog.get_logger(__name__)

async def process_sync_batch(
    session: AsyncSession,
    user: User,
    device_id: uuid.UUID,
    incident_id: uuid.UUID,
    operations: list[SyncOperationItem],
) -> list[dict[str, Any]]:
    """
    Process a batch of offline operations for a specific incident.
    Ensures idempotency for each operation.
    """
    results = []

    for op in operations:
        # Check idempotency
        existing_op = await sync_repo.find_by_idempotency_key(session, device_id, op.operation_id)
        
        if existing_op:
            if existing_op.payload_sha256 == op.payload_sha256:
                # Exact retry -> return stored response
                results.append(existing_op.response_json or {})
                continue
            else:
                # Same idempotency key, different payload -> 409
                raise HTTPException(
                    status_code=409,
                    detail={
                        "type": "https://incident-ledger.dev/errors/idempotency_payload_mismatch",
                        "title": "Idempotency payload mismatch",
                        "status": 409,
                        "code": "IDEMPOTENCY_PAYLOAD_MISMATCH",
                        "detail": f"Operation {op.operation_id} was already executed with a different payload.",
                    },
                )
        
        # New operation -> execute based on type
        response_json: dict[str, Any] = {}
        
        try:
            if op.operation_type == "create":
                # Create draft
                create_data = IncidentCreate.model_validate(op.payload)
                # We expect the payload to look like IncidentCreate
                children = []
                if create_data.children:
                    for child in create_data.children:
                        children.append({"child_id": child.child_id, "role": child.role})

                incident = await incident_service.create_draft(
                    session=session,
                    user=user,
                    center_id=user.center_id,
                    category=create_data.category.value if create_data.category else "other",
                    severity=create_data.severity.value if create_data.severity else "low",
                    children=children,
                    correlation_id="",
                    idempotency_key=op.operation_id,
                    event_at=datetime.now(UTC),
                    event_time_precision="exact",
                    location="",
                    original_factual_notes="",
                    actions_taken="",
                    witnesses_known=False,
                    # We pass the ID explicitly so the client's UUID is respected
                    id=incident_id
                )
                
                response_json = {"status": "success", "id": str(incident.id)}
            
            elif op.operation_type == "patch":
                patch_data = IncidentDraftUpdate.model_validate(op.payload)
                # Apply patch
                incident = await incident_service.update_draft(
                    session=session,
                    incident_id=incident_id,
                    user=user,
                    center_id=user.center_id,
                    updates=patch_data.model_dump(exclude_unset=True),
                    idempotency_key=op.operation_id,
                    correlation_id="",
                    # For a sync patch, we may skip optimistic concurrency by passing an empty etag,
                    # or the mobile client will just have to resolve conflicts itself.
                    etag="",
                )
                response_json = {"status": "success", "id": str(incident.id)}
            
            elif op.operation_type == "submit":
                submit_data = IncidentSubmit.model_validate(op.payload)
                result = await incident_service.submit(
                    session=session,
                    user=user,
                    incident_id=incident_id,
                    attestation=submit_data.staff_attestation.model_dump(),
                    device_info=submit_data.submitted_from.model_dump(),
                    correlation_id="",
                    idempotency_key=op.operation_id,
                )
                response_json = {"status": "success", "id": str(incident_id), "sync_state": "synchronized"}
                
            else:
                # Unsupported operation type
                raise ValidationFailedError(f"Unsupported operation type: {op.operation_type}", [])

        except Exception as e:
            # Let exceptions propagate (422, 404, etc.)
            raise e
            
        # If successful, record the operation
        await sync_repo.create_sync_operation(
            session=session,
            device_id=device_id,
            incident_id=incident_id,
            idempotency_key=op.operation_id,
            operation_type=op.operation_type,
            payload_sha256=op.payload_sha256,
            response_json=response_json,
        )
        
        results.append(response_json)

    return results
