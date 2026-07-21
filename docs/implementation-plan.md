# Implementation Plan

## Milestones
| Milestone | Scope | Completion evidence |
|---|---|---|
| M0 Foundation | Monorepo, Terraform, CI, OIDC, Cloud SQL, buckets, synthetic seed guard | dev smoke sign-in and migration run |
| M1 Capture | Mobile shell, active user, roster, draft wizard, category schemas | create/resume multi-child draft |
| M2 Offline/Evidence | encrypted SQLite queue, sync API, camera flow, storage finalization | airplane-mode submit then exactly-once sync |
| M3 Review | director portal, redline/versioning, severity, escalation worker | High/Critical timeline and approval |
| M4 Guardian | child packets, in-person/email acknowledgement, unreachable | acknowledgement and resend/unreachable scenarios |
| M5 Audit/Controls | restricted policy, audit export, legal hold, operations health | auditable restricted scenario and packet export |
| M6 Hardening | accessibility, security, recovery rehearsal, UAT/demo | all release gates passed |

## Build order
1. Define Pydantic domain types, enums, state machine, and pure policy tests before UI.
2. Create schema migrations, repositories, transactional outbox, audit writer, and seed command.
3. Implement OIDC mapping, session/device policies, and `/me`.
4. Implement draft create/read/patch, required-field validation, report versions, and submission.
5. Generate TypeScript client from OpenAPI; mobile/portal must use it rather than duplicate API types.
6. Build mobile workflow and encrypted local persistence.
7. Implement sync protocol and test retry/idempotency before evidence capture.
8. Add evidence intent/finalize flow, then director review commands and worker escalation.
9. Add child-specific packet generation and acknowledgement flows.
10. Add bounded writing assistance after manual capture works fully.
11. Add exports, retention/legal hold controls, operational health, and demo script.

## CI/CD
- Pull request: formatting, lint, typecheck, dependency scan, unit tests, API contract compatibility, migration validation, synthetic-data scan.
- Main: build immutable images, deploy dev, run integration/E2E smoke.
- Release candidate: deploy demo, execute migration, seed/reset verified synthetic dataset, run full E2E/security suite, produce test evidence.

## Definition of done
A feature is done only when API authorization and audit event are implemented, unit/integration/E2E coverage exists where relevant, error and offline behavior are defined, accessibility labels exist, observability is added, seed data supports demonstration, and documentation is updated.
