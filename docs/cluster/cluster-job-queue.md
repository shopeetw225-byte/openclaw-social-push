# Cluster Job Queue (Runtime)

Cluster jobs consumed by `openclaw-cluster-orchestrator`.

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
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cluster-job-0001 | 1 | publish | zhihu | main | idea | assignment-0001 | 6ec27150ef8f5f67d6f4ed92fcf0e57d4f3e8cc9c8f68a2e5db3264f64ef8fb5 | worker-zhihu-01 | {"title":"Cluster smoke test","body":"This is a cluster publish smoke test.","media_paths":[]} | failed | runner_error |
| cluster-job-0002 | 1 | publish | zhihu | main | idea | assignment-0002 | 4fc2d79c83f6c2be59d5fc17ffea53077ac3718f895caabf1743d4c3901b9bb5 | worker-zhihu-01 | {"title":"Cluster smoke retest","body":"This is the second cluster publish smoke test.","media_paths":[]} | failed | runner_error |
| cluster-job-0003 | 1 | publish | zhihu | main | idea | assignment-0003 | 61b7ab56c9f0fe2667e5da6f23f55f4f1fa11e30cbf0b3f2cdcb27ad30e981f8 | worker-zhihu-01 | {"title":"Cluster publish real run 3","body":"This is the third real cluster publish run.","media_paths":[]} | failed | runner_error |
