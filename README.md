# Incident Ledger — Coding Agent Pack

## Purpose
This pack is the build specification for the **Demo Center Release** of Incident Ledger: a synthetic-data-only incident reporting workflow for iPhone/iPad staff, browser-based directors, and token-based guardian acknowledgement.

## Architecture & Design Overview

### Stack
* **Staff mobile:** React Native + TypeScript, iOS/iPadOS only; native modules for Keychain, encrypted SQLite, camera, background tasks, and network state.
* **Director portal:** React + TypeScript browser application, responsive with iPad side-by-side review.
* **Guardian web:** Small responsive React application with opaque one-time token flow.
* **API:** FastAPI + Pydantic + SQLAlchemy/Alembic (Python 3.14, UV), deployed to Cloud Run.
* **Workers:** Cloud Run service/job consuming Cloud Tasks for notifications, escalation, token expiry, audit export, and sync exception processing.
* **System of record:** Cloud SQL PostgreSQL.
* **Binary storage:** Google Cloud Storage for evidence items and audit-packet buckets.

### Data Model & Synchronization
* **Version Model:** Revisions to reports do not mutate the original data. Instead, they produce an append-only sequence: `staff_submission` -> `director_edit` -> `approved` -> `addendum`.
* **Mobile Offline Sync:** The app utilizes an encrypted SQLite local store. Mutations (draft creation, evidence capture, etc.) generate idempotent `UUIDv7` operations. Upon regaining connectivity, the app syncs operations in strict dependency order.
* **Idempotency:** The API uses `Idempotency-Key` headers on mutations and stores hashes of request payloads to safely resume interrupted uploads or patch commands.

### Security & Privacy Controls
* Guardian views are strictly scoped to one child's data via opaque, short-lived tokens.
* Restricted reports (e.g., suspected abuse) block automated notification workflows and disable the optional Gemini writing assistant.
* The API enforces complete Role-Based Access Control (RBAC), and all significant actions are committed to an append-only `audit_events` table.

## Read order
1. `product-scope.md`
2. `architecture.md`
3. `data-model.md` and `db-schema.md`
4. `api-contracts.md`
5. `mobile-offline-sync.md`
6. `agents.md`
7. `security-privacy.md`
8. `implementation-plan.md`
9. `test-strategy.md`
10. `seed-data.md` and `demo-runbook.md`

## Non-negotiable constraints
- Allow exactly one enabled synthetic demo center; reject non-synthetic data.
- Staff reporting runs only in the iPhone/iPad app; no web staff reporting.
- No guardian app or guardian account; guardian acknowledgement is in person or through a one-time email link.
- Never expose any data before authentication.
- Keep staff source facts immutable after submission. Director wording edits are a new version with a reason, not overwrites.
- Offline submission is not server receipt. Display `Submitted—pending secure sync` until server acknowledgement.
- AI is optional, text-only, review-only, and unavailable for suspected abuse/neglect.
- Do not use AI to approve, route, notify, modify, or finalize reports.
- No real people, children, guardians, incidents, photos, or contact information.

## Delivery definition
The demo is complete only after all acceptance tests in `test-strategy.md` pass and every scenario in `demo-runbook.md` works without product-owner intervention.
