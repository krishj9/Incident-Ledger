# Mobile Offline and Synchronization Design

## Local store
Use encrypted SQLite. Encryption key resides in iOS Keychain and is unavailable until device unlock. Store only cached roster, active draft data, pending operations, transient camera staging files, and minimal report summaries needed by the signed-in user. Purge cached finalized content according to configured device-cache policy.

## Local tables
- `local_incidents`: draft/report snapshot, local status, server version ETag.
- `local_operations`: immutable operation ID, entity ID, type, payload, payload hash, retry count, state.
- `local_evidence`: capture metadata, local file path, checksum, upload state.
- `cached_roster`: center-scoped synthetic child/guardian display data and refresh timestamp.
- `session`: active user and device registration state; no user switch while offline.

## Operation protocol
1. Generate UUIDv7 `operation_id` and include it as `Idempotency-Key`.
2. Commit local entity mutation and operation record in one SQLite transaction.
3. Display local status immediately; never claim server receipt without API response.
4. On connectivity, process operations in dependency order: draft/create -> patch -> evidence intent/upload/finalize -> submit.
5. Server stores `(device_id, idempotency_key, payload_sha256)` and returns prior result for exact retry.
6. If same key has a different hash, return `409 IDEMPOTENCY_PAYLOAD_MISMATCH`.
7. Retry transient failures using capped exponential backoff with jitter. Do not retry validation/policy errors automatically.

## Conflict policy
- Draft changes use `If-Match` version ETag.
- If another authorized staff member changes same draft, fetch latest, show a field-level conflict screen, and require explicit user resolution.
- Submitted/approved records never merge client changes; return a state error and direct user to change-request/addendum flow.
- Evidence finalization is idempotent by evidence ID and SHA-256.

## Connectivity UX
- Persistent offline banner whenever reachability is unavailable.
- Draft autosave indicator: `Saving locally`, `Saved locally`, `Syncing`, `Synced`, `Needs attention`.
- Offline completed submission state: exactly `Submitted—pending secure sync`.
- After 72 hours from local submit without server receipt, create local high-priority issue and, at next connectivity, notify operations through API.
- Disable Switch staff while offline; explain that identity change requires server confirmation.

## Background behavior
Use iOS background task scheduling opportunistically; do not promise immediate background sync. On foreground, app launch, reachability regain, and explicit Retry, invoke the same sync engine. Preserve pending operations across app termination and device restart.

## Test matrix
Test airplane mode during every wizard page, app kill after local commit, repeated submit taps, retry after 500/503, stale ETag, image upload interruption, device revocation before sync, roster refresh offline, and 72-hour unsynced alert.
