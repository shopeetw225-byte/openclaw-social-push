---
name: openclaw-cluster-orchestrator
description: Use when routing publish jobs across multiple OpenClaw worker agents, especially to select a local worker from a node matrix, dispatch one cluster job to that worker, and record cluster-level queue, ledger, and run-log results without replacing node-local matrix-orchestrator behavior.
---

# OpenClaw Cluster Orchestrator

## Overview

This skill is the cluster-control layer above:

- `account-matrix` for governance facts
- `matrix-orchestrator` for node-local job execution
- `social-push` for platform publishing

It does not replace node-local publish logic. It only decides which worker agent should run a cluster job, then records what happened.

## When to Use

Use this skill when you need to:

- read `docs/cluster/node-matrix.md`
- pick a `ready` worker agent for a `publish` job
- fan one cluster job out into `docs/nodes/<node_id>/matrix/`
- dispatch that worker through OpenClaw
- write `cluster-result-ledger.md` and `cluster-run-log.md`

Do **not** use this skill to hand-author platform browser steps. That still belongs to `social-push`.

## Runtime Files

Cluster runtime files:

```text
docs/cluster/
```

Required cluster files:

- `docs/cluster/node-matrix.md`
- `docs/cluster/cluster-job-queue.md`
- `docs/cluster/cluster-result-ledger.md`
- `docs/cluster/cluster-run-log.md`

Node-local worker runtime files:

```text
docs/nodes/<node_id>/matrix/
```

Required node-local files per worker:

- `account-matrix.md`
- `verification-matrix.md`
- `job-queue.md`
- `result-ledger.md`
- `run-log.md`

## Core Rules

1. V1 only supports `publish` cluster jobs.
2. V1 only supports `mode = local_agent` nodes.
3. The master must choose one `ready` worker from the node matrix.
4. The master must write node-local job rows under `docs/nodes/<node_id>/matrix/`, never shared `docs/matrix/`.
5. The worker must run `MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1 python3 matrix-orchestrator/scripts/run_next_job.py` exactly once for the selected node-local runtime.
6. Cluster queue terminal states are only `done`, `failed`, or `blocked`.
7. The master must not treat commentary or `toolUse` as a final worker result.
8. Before enqueueing node-local work, the master must verify the selected worker is ready by checking its node-local `account-matrix.md` and probing the current browser identity.
9. If the worker depends on `chrome-relay`, the target browser tab must already have Browser Relay attached and switched to `ON`.

## Cluster Status Model

Cluster queue statuses:

- `pending`
- `routing`
- `running`
- `done`
- `failed`
- `blocked`

Cluster result statuses:

- `routing_blocked`
- `dispatch_error`
- `runner_error`
- `preflight_blocked`
- `publish_ok`
- `publish_filtered`
- `publish_failed`

## Dispatch Contract

Read before modifying dispatch behavior:

- `references/dispatch-contract.md`

## Quick Reference

| task | file or script |
|---|---|
| load node matrix | `scripts/load_node_matrix.py` |
| select worker | `scripts/select_worker.py` |
| bootstrap local agents | `scripts/bootstrap_local_agents.py` |
| enqueue cluster job | `scripts/enqueue_cluster_job.py` |
| dispatch worker | `scripts/dispatch_to_worker.py` |
| append cluster ledger | `scripts/append_cluster_result_ledger.py` |
| append cluster run log | `scripts/append_cluster_run_log.py` |
| cluster status | `scripts/cluster_status.py` |
| reset cluster runtime | `scripts/reset_cluster_runtime.py` |
| run next cluster job | `scripts/run_next_cluster_job.py` |
