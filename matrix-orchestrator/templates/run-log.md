# Run Log Template

Append-only execution event log per job attempt.

Required columns:

- `job_id`
- `attempt_no`
- `event`
- `status`
- `notes`
- `timestamp`

Allowed `event` values:

- `job_started`
- `decision_made`
- `dispatch_started`
- `dispatch_finished`
- `ledger_updated`
- `verification_updated`
- `guard_conflict_recorded`
- `assignment_updated`
- `override_applied`

| job_id | attempt_no | event | status | notes | timestamp |
|---|---:|---|---|---|---|
| `<job-0001>` | `1` | `job_started` | `<ok/warn/error>` | `<optional note>` | `<YYYY-MM-DDTHH:MM:SSZ>` |
