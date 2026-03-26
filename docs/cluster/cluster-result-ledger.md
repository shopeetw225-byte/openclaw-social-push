# Cluster Result Ledger (Runtime)

Immutable cluster-level result ledger.

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
| cluster-job-0001 | 1 | worker-zhihu-01 | publisher-zhihu | publish | runner_error | {"ok":true,"result_status":"runner_error","evidence":"","notes":"social-push runner not configured"} | social-push runner not configured | 2026-03-24T07:31:21Z |
| cluster-job-0002 | 1 | worker-zhihu-01 | publisher-zhihu | publish | runner_error | No attached chrome-relay browser tabs were available, so the social-push workflow could not access a logged-in Zhihu session to publish the idea. | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-24T07:36:19Z |
| cluster-job-0003 | 1 | worker-zhihu-01 | publisher-zhihu | publish | runner_error | No attached chrome-relay browser tabs were available, so the social-push workflow could not access a logged-in Zhihu session to publish the idea. | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-25T02:53:23Z |
