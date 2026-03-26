# Run Log (Runtime)

Node-local execution log for `worker-zhihu-01`.

| job_id | attempt_no | event | status | notes | timestamp |
|---|---:|---|---|---|---|
| cluster-job-0001 | 1 | job_started | ok |  | 2026-03-24T07:31:11Z |
| cluster-job-0001 | 1 | decision_made | go | real_publish_ok | 2026-03-24T07:31:11Z |
| cluster-job-0001 | 1 | dispatch_started | running |  | 2026-03-24T07:31:11Z |
| cluster-job-0001 | 1 | dispatch_finished | runner_error | social-push runner not configured | 2026-03-24T07:31:11Z |
| cluster-job-0001 | 1 | ledger_updated | runner_error | social-push runner not configured | 2026-03-24T07:31:11Z |
| cluster-job-0002 | 1 | job_started | ok |  | 2026-03-24T07:35:57Z |
| cluster-job-0002 | 1 | decision_made | go | real_publish_ok | 2026-03-24T07:35:57Z |
| cluster-job-0002 | 1 | dispatch_started | running |  | 2026-03-24T07:35:57Z |
| cluster-job-0002 | 1 | dispatch_finished | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-24T07:36:13Z |
| cluster-job-0002 | 1 | ledger_updated | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-24T07:36:13Z |
| cluster-job-0003 | 1 | job_started | ok |  | 2026-03-25T02:53:03Z |
| cluster-job-0003 | 1 | decision_made | go | real_publish_ok | 2026-03-25T02:53:03Z |
| cluster-job-0003 | 1 | dispatch_started | running |  | 2026-03-25T02:53:03Z |
| cluster-job-0003 | 1 | dispatch_finished | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-25T02:53:16Z |
| cluster-job-0003 | 1 | ledger_updated | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-25T02:53:16Z |

Allowed guard-specific `event` values when the assignment guard is enabled:

- `guard_conflict_recorded`
- `assignment_updated`
- `override_applied`
