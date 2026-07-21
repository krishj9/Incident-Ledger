# Product Scope and Requirements

## Product outcome
Incident Ledger lets child-care staff document significant incidents promptly, directors review and approve them, and a primary guardian acknowledge the approved child-specific report. This release is a controlled synthetic-data demonstration, not a real-center deployment.

## Personas and permissions
| Persona | Core permissions | Explicit exclusions |
|---|---|---|
| Staff | Create/edit own and handed-off drafts, capture permitted evidence, submit, record contact attempts, in-person acknowledgement where allowed | Approve, alter approved report, view restricted reports not assigned to them |
| Director | Review queue, acknowledge alerts, request changes, make minor wording edits, change severity with reason, approve, close unreachable, export | Directly alter staff factual content |
| Backup director | Review escalated assigned-center reports | Center administration unless separately authorized |
| Regional administrator | View 60-minute escalations, review/escalate | Routine staff capture |
| Compliance reviewer | View/review restricted reports and history | Device administration by default |
| Operations support | Device, synchronization, notification exception metadata | Incident narrative/evidence/restricted contents by default |
| Primary guardian | View one child-specific approved packet and acknowledge/disagree | See other children, edit report, access account |

## Core workflow
```text
Draft -> Submitted—pending secure sync (local only) -> Submitted -> Under review
  -> Changes requested -> Draft -> Submitted
  -> Approved -> Guardian acknowledgement pending -> Acknowledged | Unreachable -> Closed
Approved -> Addendum draft -> Addendum under review -> Approved with addendum
```

## Required capture
Every submission requires at least one child, category, severity, event date/time, exact-or-estimated time flag, location, factual description, actions taken, and staff accuracy confirmation. Capture staff present/witnesses or an explicit no-known-witnesses confirmation, treatment/response when applicable, guardian contact outcome, and follow-up/corrective actions.

## Categories
- Injury or accident
- Illness or medical event
- Behavioral incident
- Suspected abuse or neglect
- Missing child or unauthorized pickup
- Medication error
- Property damage
- Other

## Severity
| Level | Meaning | Workflow effect |
|---|---|---|
| Low | Minor event with limited immediate impact | Normal routing |
| Moderate | Meaningful staff response or guardian communication | Normal routing |
| High | Serious event requiring immediate director attention | Immediate director alert |
| Critical | Urgent or potentially severe event | Immediate director, backup at 30 minutes, regional at 60 minutes |

## Business rules
- A report can involve multiple children, but each guardian receives a separate child-specific packet.
- The primary affected child is distinct from other involved children.
- Directors may change severity only with a reason; preserve staff-selected severity.
- Director minor edits are grammar, spelling, formatting, neutrality, or clarity only. Factual changes require staff changes or an addendum.
- Approval freezes a version. Any later correction is an addendum.
- Photos require both category-policy and center-policy permission; capture only from in-app camera; maximum five images/report and 10 MB/image.
- A suspected abuse/neglect report is restricted, uses structured observations, blocks AI narrative generation, and blocks guardian notification until authorized decision.
- Email links are single-use and expire after 72 hours; resend invalidates unused older link.
- Unreachable closure requires three attempts across at least two calendar dates, then director action.
- Retain closed records seven years unless legal hold exists.

## Out of scope
Real data, Android, staff web reporting, guardian mobile app, self-registration, MFA, digital handwritten signature, video/audio/PDF/gallery uploads, regulator filing, medical/legal advice, trend analytics, device management, and child-care management system integration.

## Acceptance criteria
- Active staff identity and role remain visible throughout capture, evidence capture, review, and submission.
- Different authorized staff may continue a draft; creator/editor/submitter attribution remains intact.
- Offline drafts save locally; offline submission never appears as director-received until synchronized.
- Every material action has actor, device, timestamp, report version where relevant, and immutable audit history.
- Guardian acknowledgement means receipt/review, not agreement.
