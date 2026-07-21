# Data Model

## Aggregates
| Aggregate | Identity | Immutability rule |
|---|---|---|
| Incident | Shared event across one or more children | Submitted staff source remains immutable |
| Incident child involvement | Child role/details within incident | Used to derive guardian-specific view |
| Report version | Snapshot of source, structured facts, rendered narrative | Never update; create a new version |
| Evidence item | Original still image plus capture metadata/hash | Never replace after finalized/approved |
| Guardian packet | Approved child-specific communication artifact | References exact approved version |
| Acknowledgement | Receipt/disagreement outcome | Immutable outcome record |
| Contact attempt | Contact method/result/actor/time | Immutable event |
| Addendum | Post-approval correction path | New reviewed version; never overwrite approved version |
| Audit event | Material user/system action | Append-only |

## Version model
- `staff_submission`: staff source snapshot at submission.
- `director_edit`: derived narrative with mandatory reason and redline against its parent.
- `approved`: immutable final approved version.
- `addendum`: separate correction referencing the approved parent version.

`original_staff_notes` is always preserved verbatim in every report version snapshot. `rendered_narrative` is the human-readable version. `structured_snapshot` preserves the relevant fields used at that version.

## Report status transitions
| From | Command | To | Actor |
|---|---|---|---|
| Draft | submit | Submitted | Staff |
| Submitted | acknowledge review | Under review | Director/backup/regional |
| Submitted/Under review | request changes | Changes requested | Director |
| Changes requested | update and submit | Submitted | Staff |
| Under review | approve | Guardian acknowledgement pending | Director |
| Guardian acknowledgement pending | acknowledge/disagree | Acknowledged | Guardian/staff |
| Guardian acknowledgement pending | close unreachable | Unreachable | Director |
| Acknowledged/Unreachable | close | Closed | Director/system policy |
| Approved or later | create addendum | Addendum draft | Authorized staff/director |

## Child-specific disclosure
The incident contains all children, but the guardian packet is generated per primary guardian and child. The packet has only: child identity, approved version text filtered to the child-specific details, permitted evidence references, acknowledgement language, and acknowledgement status. Never include another child name, involvement detail, contact data, or acknowledgement.

## Audit model
Material actions include create, view, edit, submit, sync receipt, capture evidence, evidence finalized/failed, review acknowledge, request changes, edit proposal, severity change, approve, notify, email send/delivery/open, acknowledgement, contact attempt, unreachable closure, restricted route, export, legal hold, device register/revoke, and retention disposal attempt. Each event stores actor, device when present, occurrence time, correlation ID, report version where relevant, and minimal safe metadata.
