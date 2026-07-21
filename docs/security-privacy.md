# Security, Privacy, and Demo Controls

## Demo-only data controls
- Seeded data and all generated entities require `synthetic_marker=true`.
- API rejects create/update requests containing a non-allowlisted center or absent synthetic marker in demo environment.
- Email sends are restricted to mail-capture addresses/domain allowlist.
- CI scans fixtures, environment values, logs, exports, and screenshots for prohibited real-data patterns and production email domains.
- Do not connect to child-care, identity, regulator, or production email systems.

## Authentication and sessions
- No self-registration. Map approved OIDC subjects to pre-seeded users.
- Require explicit sign-in; never identify a user solely by device or PIN.
- Render no roster, report, guardian, or evidence content before valid session establishment.
- Visible active-user bar includes display name and role. Switch staff terminates prior server session before next starts.

## Authorization
- Enforce RBAC and center scope in every service method, not just router middleware.
- Restricted incident policy requires authorized director/compliance role after submission.
- Guardian token can retrieve only one packet and its exact approved version; token cannot enumerate, search, download raw evidence, or call staff APIs.
- Operations views show issue metadata by default; narrative/evidence require an explicit break-glass role and auditable reason if enabled later.

## Evidence
- Camera-only capture. Omit library/document/audio/video picker dependencies.
- Validate policy, count, type, and 10 MB limit server-side before issuing upload intent and again on finalization.
- Private objects; no public ACL. Verify SHA-256 and recorded capturer/device/time.
- Preserve original capture metadata in the application record. Do not permit replacement after approval.

## Retention and legal hold
- Closed report retention baseline is seven years.
- Legal hold blocks report, version, evidence, packet, and audit disposal.
- Lifecycle jobs must check legal hold before marking any data eligible for disposal.
- Retention-protected object buckets contain finalized evidence and audit exports; staging objects are separately lifecycle-cleaned.

## Logging
- Never log raw tokens, JWTs, original image bytes, complete guardian email links, or full report content at info level.
- Use correlation IDs, stable opaque IDs, status, actor ID, event type, and safe error codes.
- Audit logs are not application debug logs; audit records are append-only and retention-bound.

## Threat-focused tests
Test token replay, expired/resend token behavior, IDOR across children, role escalation, device revocation, unsigned object URL access, modified upload checksum, offline stolen-device cache protection, prompt injection in notes, restricted incident access, and export authorization.
