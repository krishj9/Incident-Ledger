# Architecture

## Stack
- **Staff mobile:** React Native + TypeScript, iOS/iPadOS only; native modules for Keychain, encrypted SQLite, camera, background tasks, and network state.
- **Director portal:** React + TypeScript browser application, responsive with iPad side-by-side review.
- **Guardian web:** small responsive React application with opaque one-time token flow.
- **API:** FastAPI + Pydantic + SQLAlchemy/Alembic, deployed to Cloud Run.
- **Workers:** Cloud Run service/job consuming Cloud Tasks for notifications, escalation, token expiry, audit export, and sync exception processing.
- **System of record:** Cloud SQL PostgreSQL.
- **Binary storage:** Google Cloud Storage: mutable staging bucket, retention-protected finalized evidence bucket, retention-protected audit-packet bucket.
- **Identity:** OIDC provider; FastAPI validates JWTs and maps external subject to approved synthetic user.
- **Observability:** Cloud Logging/Monitoring/Error Reporting, structured JSON logs, correlation IDs, audit events.
- **Infrastructure:** Terraform, GitHub Actions, Secret Manager, Artifact Registry.

## Context diagram
```text
Staff iOS app ----HTTPS/OIDC----> FastAPI API ----> Cloud SQL
       |                               |             |
       |                               +--> Cloud Tasks -> Worker -> Email provider
       +-- signed upload intent ------> Cloud Storage  |
Director browser ---HTTPS/OIDC-------> FastAPI API    +-> Audit packets
Guardian browser ---opaque token-----> Guardian endpoints
Writing assist ----authenticated API--> Gemini adapter (bounded request only)
```

## Component rules
- The API owns authorization, business transitions, versioning, and audit writes; clients never infer authorization.
- Cloud Storage objects are private. Clients receive narrow, short-lived upload intents only after API policy checks.
- Only the worker sends email; mobile and portal never call email provider directly.
- Use a transactional outbox table for durable domain events. A worker claims and processes events idempotently.
- Use Cloud Tasks task names derived from event IDs so alert and email work is deduplicated.
- Store all times in UTC; center timezone controls display and two-calendar-date validation.

## Environments
`dev`, `test`, and `demo` are isolated projects or isolated service/database/bucket namespaces. Demo has a compile/deploy-time `DEMO_ONLY=true` control, one allowlisted center code, mail-capture recipient allowlist, and synthetic data validation.

## Service modules
```text
services/api/app/
  api/             # routers and request/response models
  domain/          # pure business rules and state transitions
  repositories/    # SQL persistence
  services/        # use cases and policy enforcement
  integrations/    # storage, OIDC, email, Gemini, task queue
  workers/         # task handlers
  audit/           # append-only audit writer and export builder
```

## Decisions
1. Encrypted SQLite operation-log sync is used instead of a cloud-document offline store because the product needs explicit server receipt, version history, idempotency, and a transactional PostgreSQL record.
2. Use commands for workflow transitions, not generic CRUD updates after draft creation.
3. Use report versions and addenda rather than in-place edits after submission.
4. Use one bounded writing-assistance service, not autonomous or multi-agent orchestration.
5. Separate shared incident data from child-specific guardian packets to protect multi-child privacy.
6. Use Python 3.14 
7. Use UV, pyproject.toml for dependency management
8. Use expo for mobile (iOS/iPad/Android) and web UIs

