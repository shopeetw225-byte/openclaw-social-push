# Content Assignment Ledger (Runtime)

Tracks which content fingerprint is currently reserved by which target account.

## Fixed Columns

Do not rename or reorder columns.

- `assignment_id`
- `submission_ref`
- `content_fingerprint`
- `platform`
- `account_alias`
- `content_type`
- `job_id`
- `status`
- `notes`
- `created_at`

Allowed `status` values:

- `reserved`
- `queued`
- `running`
- `published`
- `blocked`
- `cancelled`

| assignment_id | submission_ref | content_fingerprint | platform | account_alias | content_type | job_id | status | notes | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| assignment-0001 | ticket://ops-1001 | 6ec27150ef8f5f67d6f4ed92fcf0e57d4f3e8cc9c8f68a2e5db3264f64ef8fb5 | zhihu | main | article | cluster-job-0001 | queued | ingress accepted | 2026-03-26T02:00:00Z |
