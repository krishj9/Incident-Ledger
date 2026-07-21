# API Contracts

## Conventions
Base path is `/v1`. Staff/director endpoints require OIDC bearer JWT. Guardian endpoints use only an opaque bearer token in the URL path and must return the minimum child-specific view. Every mutation requires `Idempotency-Key`; every response returns `X-Correlation-ID`. Use ISO-8601 UTC timestamps and RFC 9457-style errors.

## Endpoints
| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/me` | authenticated | active user, role, center, device status |
| POST | `/auth/session/switch` | authenticated | ends prior active session, begins named user session |
| POST | `/devices/register` | authenticated | register/check device limits |
| GET/POST | `/incidents` | staff+ | list eligible reports/create draft |
| GET | `/incidents/{id}` | policy scoped | report detail/history |
| PATCH | `/incidents/{id}/draft` | authorized staff | optimistic draft update |
| POST | `/incidents/{id}/submit` | authorized staff | server submission receipt |
| POST | `/incidents/{id}/sync-operations` | staff | idempotent offline operation batch |
| POST | `/incidents/{id}/evidence/intents` | staff | validate policy/create upload intent |
| POST | `/incidents/{id}/evidence/{evidenceId}/finalize` | staff | verify and finalize captured image |
| POST | `/writing-assistance/suggestions` | staff | optional bounded suggestions |
| GET | `/review-queue` | director+ | queue, escalation and elapsed time |
| POST | `/incidents/{id}/review/acknowledge` | director+ | acknowledge ownership |
| POST | `/incidents/{id}/review/edits` | director | minor wording version/reason |
| POST | `/incidents/{id}/review/request-changes` | director | return factual clarification request |
| POST | `/incidents/{id}/review/severity` | director | change severity/reason |
| POST | `/incidents/{id}/review/approve` | director | freeze version/start permitted notification |
| POST | `/incidents/{id}/addenda` | authorized staff/director | create correction workflow |
| POST | `/incidents/{id}/contact-attempts` | staff/director | record attempt |
| POST | `/incidents/{id}/acknowledgement/close-unreachable` | director | validate/close unreachable |
| POST | `/guardian-packets/{id}/in-person-acknowledgements` | staff/director | record in-person receipt |
| POST | `/guardian-packets/{id}/email-links` | policy scoped | send/resend link |
| GET/POST | `/guardian/acknowledgements/{token}` | token | view/acknowledge child packet |
| GET | `/incidents/{id}/audit-packet` | director/compliance | request/download export |
| GET | `/operations/health` | operations | no-content exception dashboard |

## Submit request
```json
{
  "staff_attestation": {"accurate_to_best_of_knowledge": true, "confirmed_at": "2026-07-19T17:45:00Z"},
  "submitted_from": {"device_id": "uuid", "offline_originated": true}
}
```

## Submit response
```json
{
  "incident_id": "uuid", "status": "submitted", "server_received_at": "2026-07-19T17:46:02Z",
  "sync_state": "synchronized", "assigned_reviewer": {"user_id": "uuid", "display_name": "DEMO-Maya Chen"}
}
```

## Error contract
```json
{
  "type": "https://incident-ledger/errors/submission-required-field-missing",
  "title": "Required field missing", "status": 422,
  "code": "SUBMISSION_REQUIRED_FIELD_MISSING", "detail": "Location is required before submission.",
  "field_errors": [{"path": "event.location", "code": "REQUIRED"}], "correlation_id": "uuid"
}
```

## Status semantics
Use `401` unauthenticated, `403` policy/role/device denial, `404` non-disclosing inaccessible resource, `409` stale version/invalid state/idempotency mismatch, `422` validation, `429` throttling, and `503` retriable dependency error. Never return sensitive incident existence details to an unauthorized caller.
