# Result Ledger Template

Immutable outcomes per job attempt.

Required columns:

- `job_id`
- `attempt_no`
- `platform`
- `account_alias`
- `content_type`
- `decision`
- `result_status`
- `conflict_id`
- `jump_target`
- `evidence`
- `notes`
- `timestamp`

Allowed `result_status` values:

- `preflight_blocked`
- `preflight_warn`
- `publish_ok`
- `publish_filtered`
- `publish_failed`
- `runner_error`

| job_id | attempt_no | platform | account_alias | content_type | decision | result_status | conflict_id | jump_target | evidence | notes | timestamp |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| `<job-0001>` | `1` | `<zhihu>` | `<main>` | `<article>` | `<go/no-go>` | `preflight_blocked` | `conflict-0001` | `<url or local target>` | `<url/id/screenshot path>` | `<optional note>` | `<YYYY-MM-DDTHH:MM:SSZ>` |
