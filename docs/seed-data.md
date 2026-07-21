# Seed Data

## Rules
All identities begin `DEMO-`, all records set `synthetic_marker=true`, all emails route to approved mail capture, and fixtures must never reuse real child/guardian data. Seed scripts must be deterministic from a versioned seed and support `reset-demo` only in dev/test/demo.

## Base roster
- Center: `DEMO-Maple Grove Learning Center` (`DEMO-MGLC-01`), timezone `America/New_York`.
- Users: director `DEMO-Maya Chen`, backup `DEMO-Jordan Patel`, regional `DEMO-Avery Brooks`, compliance `DEMO-Riley Morgan`, operations `DEMO-Casey Rivera`, six staff accounts.
- Children: twelve synthetic children across two classrooms, one primary guardian per child.
- Devices: selected staff have one/two registered iPhone/iPad installations, total under 20; no user exceeds three.
- Policies: all categories enabled; photos enabled only for injury/accident, property damage, and configured other; restricted category disables photo and AI narrative assistance by default.

## Scenario fixtures
| ID | Scenario | Required final state |
|---|---|---|
| S01 | Low injury, one child, in-person receipt | acknowledged |
| S02 | Moderate behavior, two children | child-specific packets |
| S03 | High illness | immediate director alert |
| S04 | Critical medication error | escalation clock ready |
| S05 | Offline injury with image | pending sync then synchronized |
| S06 | Returned factual clarification | resubmitted |
| S07 | Director neutral wording edit | redline/reason preserved |
| S08 | Post-approval correction | reviewed addendum |
| S09 | Email link expiry/resend/disagreement | disagreement recorded |
| S10 | Three attempts/two dates | unreachable closure eligible |
| S11 | Suspected abuse/neglect | restricted/compliance routed |
| S12 | Legal hold | disposal blocked |

## Seed command contract
```bash
make seed-demo SEED_VERSION=1
make reset-demo CONFIRM_SYNTHETIC_ONLY=true
make verify-demo-data
```
`verify-demo-data` must reject records missing synthetic marker, unapproved center, unapproved email domain, unexpected object prefix, or policy-inconsistent evidence.
