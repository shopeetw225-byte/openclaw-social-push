# Conflict Ledger (Runtime)

Captures duplicate-content and account-mismatch blocks with operator jump targets.

## Fixed Columns

Do not rename or reorder columns.

- `conflict_id`
- `assignment_id`
- `job_id`
- `attempt_no`
- `conflict_type`
- `severity`
- `status`
- `summary`
- `requested_account`
- `observed_account`
- `jump_target`
- `notes`
- `timestamp`

Allowed `conflict_type` values:

- `duplicate_content`
- `target_account_mismatch`
- `browser_identity_mismatch`

Allowed `severity` values:

- `block`

Allowed `status` values:

- `open`
- `overridden`
- `cancelled`
- `resolved`

| conflict_id | assignment_id | job_id | attempt_no | conflict_type | severity | status | summary | requested_account | observed_account | jump_target | notes | timestamp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| conflict-0001 | assignment-0001 | cluster-job-0002 | 1 | duplicate_content | block | open | identical content fingerprint already reserved by assignment-0001 | alt | main | docs/ops/content-assignment-ledger.md#assignment-0001 | blocked at ingress | 2026-03-26T02:03:00Z |
