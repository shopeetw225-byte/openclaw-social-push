# Operator Override Ledger (Runtime)

Records one-shot operator decisions for active conflicts.

## Fixed Columns

Do not rename or reorder columns.

- `override_id`
- `conflict_id`
- `job_id`
- `attempt_no`
- `action`
- `operator_ref`
- `reason`
- `timestamp`

Allowed `action` values:

- `continue_once`
- `cancel_job`

| override_id | conflict_id | job_id | attempt_no | action | operator_ref | reason | timestamp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| override-0001 | conflict-0001 | cluster-job-0002 | 1 | continue_once | op://openclaw-controller | verified duplicate is intentional retry | 2026-03-26T02:05:00Z |
