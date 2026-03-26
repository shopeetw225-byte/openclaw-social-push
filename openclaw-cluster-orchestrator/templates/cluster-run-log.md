# Cluster Run Log Template

Append-only cluster routing event log.

Required columns:

- `job_id`
- `attempt_no`
- `node_id`
- `event`
- `status`
- `notes`
- `timestamp`

Allowed `event` values:

- `job_started`
- `worker_selected`
- `dispatch_started`
- `dispatch_finished`
- `ledger_updated`

| job_id | attempt_no | node_id | event | status | notes | timestamp |
|---|---:|---|---|---|---|---|
| `cluster-job-0001` | `1` | `worker-zhihu-01` | `job_started` | `ok` | `optional note` | `2026-03-24T00:00:00Z` |
