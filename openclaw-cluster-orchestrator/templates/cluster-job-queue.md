# Cluster Job Queue Template

Queue of cluster-level jobs to be routed by `openclaw-cluster-orchestrator`.

Required columns:

- `job_id`
- `attempt_no`
- `job_type`
- `platform`
- `account_alias`
- `content_type`
- `assignment_id`
- `content_fingerprint`
- `preferred_node`
- `payload_json`
- `status`
- `notes`

Allowed `job_type` values:

- `publish`
- `collect_metrics`
- `risk_check`

Allowed `status` values:

- `pending`
- `routing`
- `running`
- `done`
- `failed`
- `blocked`

| job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| `cluster-job-0001` | `1` | `publish` | `zhihu` | `main` | `idea` | `assignment-0001` | `6ec27150ef8f5f67d6f4ed92fcf0e57d4f3e8cc9c8f68a2e5db3264f64ef8fb5` | `worker-zhihu-01` | `{"title":"Title","body":"Body","media_paths":[]}` | `pending` | `optional note` |
