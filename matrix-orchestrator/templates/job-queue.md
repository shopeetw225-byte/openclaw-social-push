# Job Queue Template

Queue of publishing jobs to be consumed by `matrix-orchestrator`.

Required columns:

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
|---|---:|---|---|---|---|---|---|---|---|---|---|
| `<job-0001>` | `1` | `<zhihu>` | `<main>` | `<article>` | `<title>` | `<body or path>` | `<comma-separated paths or empty>` | `assignment-0001` | `<sha256 fingerprint>` | `pending` | `<optional note>` |
