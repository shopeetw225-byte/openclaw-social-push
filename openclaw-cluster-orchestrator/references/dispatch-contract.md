# Cluster Dispatch Contract

This file defines the V1 boundary between:

- `openclaw-cluster-orchestrator` as the master control layer
- local worker agents as the execution targets
- `matrix-orchestrator` as the node-local runner

## V1 Worker Entry

The master must dispatch one local worker agent through OpenClaw CLI:

```bash
"$OPENCLAW_BIN" agent --json --agent <worker-agent-id> -m "<worker prompt>"
```

The worker prompt must instruct the worker to run:

```bash
MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1 python3 matrix-orchestrator/scripts/run_next_job.py \
  --queue docs/nodes/<node_id>/matrix/job-queue.md \
  --account-matrix docs/nodes/<node_id>/matrix/account-matrix.md \
  --verification-matrix docs/nodes/<node_id>/matrix/verification-matrix.md \
  --result-ledger docs/nodes/<node_id>/matrix/result-ledger.md \
  --run-log docs/nodes/<node_id>/matrix/run-log.md \
  --assignment-ledger docs/ops/content-assignment-ledger.md \
  --conflict-ledger docs/ops/conflict-ledger.md \
  --override-ledger docs/ops/operator-override-ledger.md
```

V1 workers must not bypass `matrix-orchestrator`.

Before the master writes a node-local job row, it should probe the selected worker runtime:

- load `docs/nodes/<node_id>/matrix/account-matrix.md`
- resolve the `platform + account_alias` row
- use that row's `browser_profile` and `display_name` to probe current browser identity

If the worker publishes through `chrome-relay`, the target browser tab must already have the OpenClaw Browser Relay extension attached and switched to `ON`. If the probe cannot confirm the expected logged-in identity, the master should stop before dispatch and record a cluster-side `routing_blocked` result instead of consuming the worker runtime.

## Required Payload Fields

The normalized cluster payload must include:

- `job_id`
- `attempt_no`
- `node_id`
- `job_type`
- `platform`
- `account_alias`
- `content_type`
- `assignment_id`
- `content_fingerprint`
- `title`
- `body`
- `media_paths`
- `preferred_node`
- `cluster_notes`

## Allowed Worker Terminal Results

Workers must return terminal JSON with:

```json
{"ok": true, "result_status": "publish_ok", "evidence": "", "notes": ""}
```

Allowed `result_status` values:

- `preflight_blocked`
- `publish_ok`
- `publish_filtered`
- `publish_failed`
- `runner_error`

## Master-Side Mapping

- no ready worker -> `routing_blocked`
- worker readiness probe fails before dispatch -> `routing_blocked`
- OpenClaw dispatch failure -> `dispatch_error`
- worker `preflight_blocked` -> cluster queue `blocked`
- worker `publish_ok` / `publish_filtered` -> cluster queue `done`
- worker `publish_failed` / `runner_error` -> cluster queue `failed`
