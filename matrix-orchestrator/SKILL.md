---
name: matrix-orchestrator
description: Use when coordinating multi-account publishing jobs from markdown matrices, especially to run preflight checks, choose account aliases, dispatch publishing through social-push, and write structured execution results without changing the underlying publish workflows.
---

# Matrix Orchestrator

## Overview

This skill is the execution bridge between:

- `account-matrix` as the governance/source-of-truth layer
- `social-push` as the publish execution layer

It does not replace platform workflows. It decides whether a job should run, then records what happened.

## When to Use

Use this skill when you need to:

- read account and verification matrices from `docs/matrix/`
- decide `go`, `warn`, or `block` before a publish
- dispatch a publishing job through `social-push`
- append results to `result-ledger.md` and `run-log.md`
- update verification state after a successful or filtered publish

Do **not** use this skill to hand-author platform browser steps. That still belongs to `social-push`.

## Runtime Files

This skill expects runtime markdown files at:

```text
docs/matrix/
```

Required files:

- `docs/matrix/account-matrix.md`
- `docs/matrix/verification-matrix.md`
- `docs/matrix/job-queue.md`
- `docs/matrix/result-ledger.md`
- `docs/matrix/run-log.md`

## Core Decision Model

The preflight engine returns one of:

- `go`
- `warn`
- `block`

Default rules:

- `real_publish_ok` -> `go`
- `submit_ok` -> `warn`
- `submit_ok_filtered` -> `warn`
- `page_verified` -> `block`
- `workflow_only` -> `block`
- no matching verification row -> `block`

`warn` is not auto-runnable unless the caller explicitly allows it.

## Execution Flow

1. Read the next `pending` job from `docs/matrix/job-queue.md`
2. Mark it `running`
3. Read account and verification matrices
4. Run preflight
5. If `block`, write result + log and stop
6. If `warn`, require explicit allow
7. If allowed, dispatch to `social-push`
8. Record evidence and result
9. Update verification matrix when appropriate
10. Mark the queue row as terminal

## Contracts

Read before implementing or modifying dispatch behavior:

- `references/social-push-contract.md`

## Dispatch Note

By default, `dispatch_social_push.py` expects an injected runner in tests and controlled integrations.

If you want the built-in OpenClaw runner, enable:

```bash
export MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1
```

The built-in runner defaults to gateway mode:

```bash
"$OPENCLAW_BIN" agent --json --agent main ...
```

In gateway mode, the orchestrator is talking to the skill set already installed in the OpenClaw workspace/session. If this repository contains newer `social-push` changes than the installed skill, sync or reinstall `social-push` first, or switch to local mode.

If you explicitly want embedded local mode instead, also set:

```bash
export MATRIX_ORCHESTRATOR_OPENCLAW_MODE=local
```

That switches the command to:

```bash
"$OPENCLAW_BIN" agent --local --json --agent main ...
```

You can also override `MATRIX_ORCHESTRATOR_OPENCLAW_AGENT`, `MATRIX_ORCHESTRATOR_OPENCLAW_SESSION_ID`, and `MATRIX_ORCHESTRATOR_OPENCLAW_TIMEOUT` when needed.

## Templates

Bundled templates:

- `templates/job-queue.md`
- `templates/result-ledger.md`
- `templates/run-log.md`

## Quick Reference

| task | file or script |
|---|---|
| load markdown tables | `scripts/load_markdown_table.py` |
| run preflight | `scripts/run_preflight.py` |
| dispatch publish | `scripts/dispatch_social_push.py` |
| run next queued job | `scripts/run_next_job.py` |
| append result ledger | `scripts/append_result_ledger.py` |
| append run log | `scripts/append_run_log.py` |
| update verification matrix | `scripts/update_verification_matrix.py` |

Example commands:

```bash
python3 matrix-orchestrator/scripts/run_preflight.py \
  --job-json '{"platform":"zhihu","account_alias":"main","content_type":"article"}'

python3 matrix-orchestrator/scripts/run_next_job.py

# safe demo path without real publish
python3 matrix-orchestrator/scripts/run_next_job.py \
  --dry-run-result-status publish_ok \
  --dry-run-evidence demo://publish/ok \
  --dry-run-notes demo
```
