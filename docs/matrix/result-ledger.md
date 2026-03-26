# Result Ledger (Runtime)

Immutable publish and decision outcomes per job attempt.

## Fixed Columns

Do not rename or reorder columns.

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
| job-0001 | 1 | zhihu | main | article | go | runner_error |  |  |  | social-push runner not configured | 2026-03-24T03:02:46Z |
| job-0002 | 1 | zhihu | main | article | go | publish_ok |  |  | demo://publish/ok-2 | demo-2 | 2026-03-24T03:10:19Z |
| job-0003 | 1 | zhihu | main | idea | go | publish_failed |  |  | failure \| evidence: none \| filtered: no \| reason: social-push 当前不支持 zhihu/知乎发布（skill 仅覆盖 Instagram、Threads、X、Facebook、小红书、微博、微信公众号、掘金） |  | 2026-03-24T03:29:24Z |
| job-0004 | 1 | zhihu | main | idea | go | runner_error |  |  | Navigating the attached chrome-relay tab to https://www.zhihu.com/ redirected immediately to https://www.zhihu.com/signin?next=%2F, so the current browser session is not logged into Zhihu and the publish workflow could not proceed. | Please log into Zhihu in the attached browser session, then rerun the same job. | 2026-03-24T03:57:02Z |
