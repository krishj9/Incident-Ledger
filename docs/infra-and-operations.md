# Infrastructure and Operations

## Terraform modules
- `network`: private service networking/VPC connectors as needed.
- `cloudsql`: PostgreSQL, backups, PITR configuration, least-privilege DB users.
- `storage`: staging/final evidence/audit export buckets, private IAM, lifecycle/retention policies.
- `run`: API, worker, guardian web, director portal services; service accounts and environment config.
- `tasks`: queues, retry policy, dead-letter routing.
- `secrets`: OIDC/email/Gemini secrets references only; never secret values in Terraform state where avoidable.
- `monitoring`: uptime/availability, worker backlog, sync exception, error-rate and new-device alerts.

## Worker jobs
| Job | Trigger | Idempotency key |
|---|---|---|
| Director alert | high/critical submission | incident + submitted version |
| Backup escalation | 30 minutes unacknowledged | incident + escalation stage |
| Regional escalation | 60 minutes unacknowledged | incident + escalation stage |
| Guardian email | approval/explicit resend | guardian packet + link generation |
| Token expiry | scheduled/event | token ID |
| Unsynced exception | server receives delayed client state | device + incident |
| Audit export | authorized request | export request ID |
| Retention evaluation | scheduled | incident + retention date |

## Operational dashboards
- Reports by status; High/Critical awaiting review; acknowledgement status; pending synchronization; device registration status.
- Worker failure/dead-letter count; notification delivery failures; oldest pending sync; newly registered/revoked device events.
- Do not expose broad trend analytics or report narrative/evidence in default operations dashboard.

## Runbooks
Maintain separate runbooks for device revoke, user access issue, sync failure, notification failure, failed evidence upload, guardian token issue, worker backlog, audit export failure, legal hold, and recovery rehearsal.
