# Cluster Result Ledger Template

Immutable cluster-level outcome log per dispatch attempt.

Required columns:

- `job_id`
- `attempt_no`
- `node_id`
- `agent_id`
- `job_type`
- `result_status`
- `evidence`
- `notes`
- `timestamp`

Allowed `result_status` values:

- `routing_blocked`
- `dispatch_error`
- `runner_error`
- `preflight_blocked`
- `publish_ok`
- `publish_filtered`
- `publish_failed`

| job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
|---|---:|---|---|---|---|---|---|---|
| `cluster-job-0001` | `1` | `worker-zhihu-01` | `publisher-zhihu` | `publish` | `publish_ok` | `https://example.com/post/1` | `optional note` | `2026-03-24T00:00:00Z` |
