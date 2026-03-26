# Run Log (Runtime)

Execution event log per job attempt.

## Fixed Columns

Do not rename or reorder columns.

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
| job-0001 | 1 | job_started | ok |  | 2026-03-24T03:02:46Z |
| job-0001 | 1 | decision_made | go | real_publish_ok | 2026-03-24T03:02:46Z |
| job-0001 | 1 | dispatch_started | running |  | 2026-03-24T03:02:46Z |
| job-0001 | 1 | dispatch_finished | runner_error | social-push runner not configured | 2026-03-24T03:02:46Z |
| job-0001 | 1 | job_started | ok |  | 2026-03-24T03:08:36Z |
| job-0001 | 1 | decision_made | go | real_publish_ok | 2026-03-24T03:08:36Z |
| job-0001 | 1 | dispatch_started | running |  | 2026-03-24T03:08:36Z |
| job-0001 | 1 | dispatch_finished | publish_ok | demo | 2026-03-24T03:08:36Z |
| job-0002 | 1 | job_started | ok |  | 2026-03-24T03:10:19Z |
| job-0002 | 1 | decision_made | go | real_publish_ok | 2026-03-24T03:10:19Z |
| job-0002 | 1 | dispatch_started | running |  | 2026-03-24T03:10:19Z |
| job-0002 | 1 | dispatch_finished | publish_ok | demo-2 | 2026-03-24T03:10:19Z |
| job-0002 | 1 | ledger_updated | publish_ok | demo-2 | 2026-03-24T03:10:19Z |
| job-0002 | 1 | verification_updated | real_publish_ok | demo-2 | 2026-03-24T03:10:19Z |
| job-0003 | 1 | job_started | ok |  | 2026-03-24T03:29:09Z |
| job-0003 | 1 | decision_made | go | real_publish_ok | 2026-03-24T03:29:09Z |
| job-0003 | 1 | dispatch_started | running |  | 2026-03-24T03:29:09Z |
| job-0003 | 1 | dispatch_finished | publish_failed |  | 2026-03-24T03:29:24Z |
| job-0003 | 1 | ledger_updated | publish_failed |  | 2026-03-24T03:29:24Z |
| job-0004 | 1 | job_started | ok |  | 2026-03-24T03:56:41Z |
| job-0004 | 1 | decision_made | go | real_publish_ok | 2026-03-24T03:56:41Z |
| job-0004 | 1 | dispatch_started | running |  | 2026-03-24T03:56:41Z |
| job-0004 | 1 | dispatch_finished | runner_error | Please log into Zhihu in the attached browser session, then rerun the same job. | 2026-03-24T03:57:02Z |
| job-0004 | 1 | ledger_updated | runner_error | Please log into Zhihu in the attached browser session, then rerun the same job. | 2026-03-24T03:57:02Z |
