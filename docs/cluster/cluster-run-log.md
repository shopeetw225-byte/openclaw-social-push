# Cluster Run Log (Runtime)

Cluster-level routing event log.

Allowed `event` values:

- `job_started`
- `worker_selected`
- `dispatch_started`
- `dispatch_finished`
- `ledger_updated`

| job_id | attempt_no | node_id | event | status | notes | timestamp |
|---|---:|---|---|---|---|---|
| cluster-job-0001 | 1 |  | job_started | ok |  | 2026-03-24T07:30:54Z |
| cluster-job-0001 | 1 | worker-zhihu-01 | worker_selected | ok | publisher-zhihu | 2026-03-24T07:30:54Z |
| cluster-job-0001 | 1 | worker-zhihu-01 | dispatch_started | running | publisher-zhihu | 2026-03-24T07:30:54Z |
| cluster-job-0001 | 1 | worker-zhihu-01 | dispatch_finished | runner_error | social-push runner not configured | 2026-03-24T07:31:21Z |
| cluster-job-0001 | 1 | worker-zhihu-01 | ledger_updated | runner_error | social-push runner not configured | 2026-03-24T07:31:21Z |
| cluster-job-0002 | 1 |  | job_started | ok |  | 2026-03-24T07:35:48Z |
| cluster-job-0002 | 1 | worker-zhihu-01 | worker_selected | ok | publisher-zhihu | 2026-03-24T07:35:48Z |
| cluster-job-0002 | 1 | worker-zhihu-01 | dispatch_started | running | publisher-zhihu | 2026-03-24T07:35:48Z |
| cluster-job-0002 | 1 | worker-zhihu-01 | dispatch_finished | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-24T07:36:19Z |
| cluster-job-0002 | 1 | worker-zhihu-01 | ledger_updated | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-24T07:36:19Z |
| cluster-job-0003 | 1 |  | job_started | ok |  | 2026-03-25T02:52:51Z |
| cluster-job-0003 | 1 | worker-zhihu-01 | worker_selected | ok | publisher-zhihu | 2026-03-25T02:52:51Z |
| cluster-job-0003 | 1 | worker-zhihu-01 | dispatch_started | running | publisher-zhihu | 2026-03-25T02:52:51Z |
| cluster-job-0003 | 1 | worker-zhihu-01 | dispatch_finished | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-25T02:53:23Z |
| cluster-job-0003 | 1 | worker-zhihu-01 | ledger_updated | runner_error | Please attach the OpenClaw Browser Relay extension to the target browser tab first, then rerun the same job. | 2026-03-25T02:53:23Z |
