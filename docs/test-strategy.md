# Test Strategy

## Test layers
| Layer | Focus | Required examples |
|---|---|---|
| Unit | pure rules/state transitions | required fields, policy, 3 attempts/2 dates, severity escalation |
| API integration | FastAPI/Postgres/storage/task boundaries | idempotency, roles, immutable versions, token hash |
| Contract | OpenAPI compatibility/client generation | mobile/portal generated client |
| Mobile component | UI and state | active bar, offline banner, category disclosure |
| End-to-end | deployed services + iOS simulator/device | offline-to-online submission, approval, acknowledgement |
| Security | authorization and abuse | IDOR, replay, revocation, upload tampering |
| UAT/demo | stakeholder script | all demo success scenarios |

## Critical tests
1. Staff creates a two-child draft, assigns primary affected child, submits with all required fields.
2. Required-field omission returns field-specific 422 and blocks submission.
3. Active user remains visible through capture/evidence/submission.
4. Staff A creates draft, Staff B continues online; creator/editor/submitter are separately audited.
5. Offline submit, app restart, duplicate retry, reconnect: exactly one server incident/submission/director alert.
6. Five-image and 10 MB server enforcement; gallery/document/video/audio route absent.
7. High/Critical director immediate alert; backup at 30 minutes unacknowledged; regional at 60.
8. Director minor edit without reason fails; factual edit fails; approved version is immutable.
9. Post-approval correction produces addendum and retains original approved version.
10. Each multi-child guardian packet contains only the target child’s permitted data.
11. Replacement email invalidates old unused link; expired/replayed links fail without disclosure.
12. Disagreement is stored separately and never changes report.
13. Three attempts spanning one date fail unreachable closure; three across two dates succeed only for director.
14. Restricted incident refuses writing assistance and blocks guardian notification by default.
15. Audit packet contains lifecycle, versions, evidence manifest, review/approval, acknowledgement, and export audit event.
16. Legal hold blocks disposal.

## Quality gates
- 100% of critical tests pass.
- No open P0/P1; P2 requires documented demo waiver.
- Static typecheck/lint clean; dependency and secret scan clean.
- iPhone and iPad manual smoke pass.
- Accessibility: dynamic type, VoiceOver labels, focus order, portal keyboard navigation, contrast.
- Restore rehearsal recovers sample approved report and evidence manifest in non-production environment.
