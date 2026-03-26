# Job Queue (Runtime)

Queue consumed by orchestrator workers.

## Fixed Columns

Do not rename or reorder columns.

- `job_id`
- `attempt_no`
- `platform`
- `account_alias`
- `content_type`
- `title`
- `body`
- `media_paths`
- `assignment_id`
- `content_fingerprint`
- `status`
- `notes`

Allowed `status` values:

- `pending`
- `running`
- `done`
- `blocked`
- `failed`
- `cancelled`

| job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | assignment_id | content_fingerprint | status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| job-0001 | 1 | zhihu | main | article | Matrix Orchestrator Demo | This is a dry-run matrix orchestrator demo job. |  | assignment-0001 | 7f6a0fca4fe9bb5dfd0128f8dd844ea2af7f8d4078fef66216c0daac82466e9d | done | publish_ok |
| job-0002 | 1 | zhihu | main | article | Matrix Orchestrator Demo 2 | This is the second dry-run matrix orchestrator demo job. |  | assignment-0002 | 54560f85bc67f8e455cf8e7376a3bb4a9dca6a706518784ca4b2e027614cf535 | done | publish_ok |
| job-0003 | 1 | zhihu | main | idea | Matrix Orchestrator Live Test 2026-03-24 | Matrix orchestrator live dispatch test from docs/matrix/job-queue.md on 2026-03-24. |  | assignment-0003 | c3fb3ed41a4d610fe0b0f6ca2c55f0ca5e05d5f1f76746bc2a8fdbf4d2f7d7bd | failed | publish_failed |
| job-0004 | 1 | zhihu | main | idea | Matrix Orchestrator Live Retest 2026-03-24 | Matrix orchestrator live retest after syncing workspace social-push skill on 2026-03-24. |  | assignment-0004 | 91a3ce6593227a25c5035f9ef13c3c11ef2252d7033db10ca9dd0544ec934907 | failed | runner_error |
