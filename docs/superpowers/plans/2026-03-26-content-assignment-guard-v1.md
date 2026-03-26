# Content Assignment Guard V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first working `content-assignment-guard` that reserves content at ingress time, blocks duplicate or mismatched publishes at node-local preflight time, records conflicts/overrides in markdown ledgers, and threads guard metadata through the cluster handoff.

**Architecture:** Add one new guard helper module under `matrix-orchestrator/scripts/` to own content fingerprinting, assignment/conflict/override ledger IO, and preflight guard evaluation. Extend cluster enqueue and cluster-to-node handoff so `assignment_id` and `content_fingerprint` exist before execution, then make `run_preflight.py` and `run_next_job.py` consult the new guard state and update ledgers on block / cancel / publish terminal states. Treat browser-identity checks as contract-driven in V1: enforce `browser_identity_mismatch` when the caller or runner provides `observed_account` / `jump_target`, without requiring a brand-new live browser probe before the rest of the guard can ship. Keep `openclaw-cluster-orchestrator` business-light by passing guard metadata through without interpreting it.

**Tech Stack:** Python 3 stdlib CLI scripts, Markdown-table runtime files, unittest, existing `matrix-orchestrator` markdown table helpers, existing cluster queue wiring

---

## File Map

### New runtime files

- `docs/ops/content-assignment-ledger.md`
  Runtime assignment ledger keyed by `assignment_id` and `content_fingerprint`.
- `docs/ops/conflict-ledger.md`
  Runtime conflict ledger for duplicate-content and mismatch blocks.
- `docs/ops/operator-override-ledger.md`
  Runtime override ledger for `continue_once` and `cancel_job`.

### New source files

- `matrix-orchestrator/scripts/content_assignment_guard.py`
  Shared guard helpers for fingerprinting, ledger loading/appending, conflict evaluation, override lookup, and assignment status sync.
- `matrix-orchestrator/tests/test_content_assignment_guard.py`
  Unit tests for fingerprinting, duplicate detection, override scoping, and ledger row helpers.
- `matrix-orchestrator/scripts/enqueue_guarded_job.py`
  Guard-layer ingress that reserves assignments before appending runnable jobs.
- `matrix-orchestrator/tests/test_enqueue_guarded_job.py`
  Tests for guarded ingress, duplicate blocking, and queue append behavior.
- `matrix-orchestrator/scripts/apply_guard_override.py`
  Explicit operator entry point for `continue_once` and `cancel_job`.
- `matrix-orchestrator/tests/test_apply_guard_override.py`
  Tests for override recording and blocked-job requeue / cancel behavior.

### Existing files to modify

- `matrix-orchestrator/templates/job-queue.md`
  Add guard columns that node-local jobs must carry.
- `matrix-orchestrator/templates/result-ledger.md`
  Record guard references / jump targets in result rows.
- `matrix-orchestrator/templates/run-log.md`
  Record guard-related events.
- `matrix-orchestrator/scripts/run_preflight.py`
  Combine verification status with guard evaluation.
- `matrix-orchestrator/scripts/run_next_job.py`
  Read guard ledgers, block on conflicts, update assignment/conflict terminal state, and write richer result/log rows.
- `matrix-orchestrator/scripts/dispatch_social_push.py`
  Preserve extra runner fields such as `jump_target` and `observed_account`.
- `matrix-orchestrator/references/social-push-contract.md`
  Document the new optional runner output fields.
- `matrix-orchestrator/tests/test_run_preflight.py`
  Cover duplicate-content, target-account-mismatch, browser-identity-mismatch, and override behavior.
- `matrix-orchestrator/tests/test_run_next_job.py`
  Cover guard-aware queue transitions and ledger updates.
- `matrix-orchestrator/tests/test_dispatch_social_push.py`
  Cover pass-through normalization for `jump_target` and `observed_account`.
- `matrix-orchestrator/tests/test_enqueue_guarded_job.py`
  Cover assignment reservation, duplicate-content blocking, and pass-through queue metadata.
- `matrix-orchestrator/tests/test_apply_guard_override.py`
  Cover operator override writes and queue row status changes.
- `openclaw-cluster-orchestrator/templates/cluster-job-queue.md`
  Add pass-through guard columns.
- `openclaw-cluster-orchestrator/scripts/enqueue_cluster_job.py`
  Accept and preserve guard metadata without interpreting it.
- `openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py`
  Copy guard fields from cluster jobs into node-local jobs.
- `openclaw-cluster-orchestrator/scripts/dispatch_to_worker.py`
  Pass the new ops-ledger CLI paths into worker-side `run_next_job.py`.
- `openclaw-cluster-orchestrator/references/dispatch-contract.md`
  Document worker invocation with guard-ledger paths.
- `openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py`
  Reset `docs/ops/*` runtime ledgers together with queue/log/result files.
- `openclaw-cluster-orchestrator/tests/test_enqueue_cluster_job.py`
  Cover cluster pass-through of guard metadata.
- `openclaw-cluster-orchestrator/tests/test_run_next_cluster_job.py`
  Cover pass-through of guard metadata into node-local queue rows.
- `openclaw-cluster-orchestrator/tests/test_dispatch_to_worker.py`
  Cover worker command-line propagation of guard-ledger paths.
- `openclaw-cluster-orchestrator/tests/test_reset_cluster_runtime.py`
  Cover reset of `docs/ops/*` ledgers.
- `docs/matrix/job-queue.md`
  Sync sample runtime table with new queue columns.
- `docs/matrix/result-ledger.md`
  Sync sample runtime table with new result columns.
- `docs/matrix/run-log.md`
  Sync sample runtime table with new events / notes examples.
- `docs/cluster/cluster-job-queue.md`
  Sync sample cluster queue with new guard columns.
- `docs/nodes/worker-zhihu-01/matrix/job-queue.md`
  Sync sample node-local queue with new guard columns.
- `docs/nodes/worker-reddit-01/matrix/job-queue.md`
  Sync sample node-local queue with new guard columns.
- `docs/nodes/worker-zhihu-01/matrix/result-ledger.md`
  Sync sample runtime table with new result columns.
- `docs/nodes/worker-zhihu-01/matrix/run-log.md`
  Sync sample runtime table with new guard events.
- `docs/nodes/worker-reddit-01/matrix/result-ledger.md`
  Sync sample runtime table with new result columns.
- `docs/nodes/worker-reddit-01/matrix/run-log.md`
  Sync sample runtime table with new guard events.
- `GUIDE.md`
  Explain `docs/ops/*` ledgers and override flow.
- `README.md`
  Mention `content-assignment-guard` in the architecture overview.

## Task 1: Add Guard Runtime Ledgers and Shared Helper

**Files:**
- Create: `matrix-orchestrator/scripts/content_assignment_guard.py`
- Create: `matrix-orchestrator/tests/test_content_assignment_guard.py`
- Create: `docs/ops/content-assignment-ledger.md`
- Create: `docs/ops/conflict-ledger.md`
- Create: `docs/ops/operator-override-ledger.md`

- [ ] **Step 1: Write failing unit tests for guard helpers**

Cover:
- identical content generates the same `content_fingerprint`
- different target accounts with identical content still collide
- terminal `cancelled` / `published` assignments no longer block new reservations
- `continue_once` only applies to one `conflict_id + job_id + attempt_no`
- `cancel_job` marks the linked assignment as cancelled

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_content_assignment_guard.py' -v`

Expected: FAIL because the helper module does not exist yet.

- [ ] **Step 2: Implement guard helper module**

Expose focused functions so later tasks can reuse them without copying business rules:

```python
def build_content_fingerprint(job_like: dict[str, object]) -> str: ...
def reserve_assignment(... ) -> dict[str, str]: ...
def record_conflict(... ) -> dict[str, str]: ...
def find_applicable_override(... ) -> dict[str, str] | None: ...
def sync_assignment_terminal_state(... ) -> None: ...
```

Reuse `load_markdown_table.py`, `markdown_table_utils.py`, and the append-only ledger style already used by `append_result_ledger.py` and `append_run_log.py`.

- [ ] **Step 3: Write runtime ledger templates**

Create the three `docs/ops/*` files with fixed columns, allowed statuses/actions, and one realistic sample row each so scripts/tests have stable fixtures to parse.

- [ ] **Step 4: Run the focused tests**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_content_assignment_guard.py' -v`

Expected: PASS

## Task 2: Add Guarded Ingress and Keep Cluster Pass-Through

**Files:**
- Create: `matrix-orchestrator/scripts/enqueue_guarded_job.py`
- Create: `matrix-orchestrator/tests/test_enqueue_guarded_job.py`
- Modify: `openclaw-cluster-orchestrator/templates/cluster-job-queue.md`
- Modify: `openclaw-cluster-orchestrator/scripts/enqueue_cluster_job.py`
- Modify: `openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py`
- Modify: `openclaw-cluster-orchestrator/tests/test_enqueue_cluster_job.py`
- Modify: `openclaw-cluster-orchestrator/tests/test_run_next_cluster_job.py`
- Modify: `docs/cluster/cluster-job-queue.md`
- Modify: `docs/nodes/worker-zhihu-01/matrix/job-queue.md`
- Modify: `docs/nodes/worker-reddit-01/matrix/job-queue.md`

- [ ] **Step 1: Write failing ingress and cluster tests**

Extend tests to cover:
- guarded ingress creates `assignment_id` and `content_fingerprint`
- duplicate content is rejected before a runnable job is appended
- cluster enqueue accepts caller-supplied `assignment_id` and `content_fingerprint` unchanged
- cluster-to-node handoff copies `assignment_id` and `content_fingerprint` into node-local queue rows

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_enqueue_guarded_job.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_enqueue_cluster_job.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_run_next_cluster_job.py' -v`

Expected: FAIL because guarded ingress does not exist and cluster queue schema does not carry guard fields yet.

- [ ] **Step 2: Build guarded ingress**

Create `enqueue_guarded_job.py` so it:
- builds the fingerprint from `title`, `body`, `content_type`, and `media_paths`
- reserves an assignment in `docs/ops/content-assignment-ledger.md`
- records a conflict in `docs/ops/conflict-ledger.md` and exits with a clear duplicate-content error when the fingerprint is already actively reserved
- appends a runnable row only after the reservation succeeds

The script may target either node-local `docs/matrix/job-queue.md` or cluster `docs/cluster/cluster-job-queue.md`, but guard judgment must happen here, not inside cluster routing code.

- [ ] **Step 3: Extend cluster queue schema for pass-through**

Add `assignment_id` and `content_fingerprint` to the cluster template and sample runtime file. Update `enqueue_cluster_job.py` so callers can pass these fields explicitly and the cluster layer stores them unchanged.

- [ ] **Step 4: Copy guard metadata into node-local jobs**

Update `run_next_cluster_job.py` so `_append_node_local_job(...)` writes `assignment_id` and `content_fingerprint` into the node-local `job-queue.md` row.

- [ ] **Step 5: Run the focused tests**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_enqueue_guarded_job.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_enqueue_cluster_job.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_run_next_cluster_job.py' -v`

Expected: PASS

## Task 3: Enforce Guard Decisions in Node-Local Preflight and Execution

**Files:**
- Modify: `matrix-orchestrator/templates/job-queue.md`
- Modify: `matrix-orchestrator/templates/result-ledger.md`
- Modify: `matrix-orchestrator/templates/run-log.md`
- Modify: `matrix-orchestrator/scripts/run_preflight.py`
- Modify: `matrix-orchestrator/scripts/run_next_job.py`
- Modify: `matrix-orchestrator/tests/test_run_preflight.py`
- Modify: `matrix-orchestrator/tests/test_run_next_job.py`
- Modify: `docs/matrix/job-queue.md`
- Modify: `docs/matrix/result-ledger.md`
- Modify: `docs/matrix/run-log.md`
- Modify: `docs/nodes/worker-zhihu-01/matrix/result-ledger.md`
- Modify: `docs/nodes/worker-zhihu-01/matrix/run-log.md`
- Modify: `docs/nodes/worker-reddit-01/matrix/result-ledger.md`
- Modify: `docs/nodes/worker-reddit-01/matrix/run-log.md`

- [ ] **Step 1: Write failing preflight tests**

Add tests for:
- `duplicate_content` blocks when another active assignment owns the same fingerprint
- `target_account_mismatch` blocks when the job row does not match the assignment record
- `browser_identity_mismatch` blocks when guard context supplies `observed_account` and it differs from `account-matrix` display name
- matching `continue_once` override downgrades the current conflict from block to go only for the specific attempt

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_run_preflight.py' -v`

Expected: FAIL because guard-aware preflight does not exist yet.

- [ ] **Step 2: Write failing run-next-job tests**

Add tests for:
- blocked guard decisions append a result row with `conflict_id`, `jump_target`, and `preflight_blocked`
- publish success marks the assignment `published`
- `publish_filtered`, `publish_failed`, and `runner_error` move the assignment to a non-success terminal status that still blocks duplicate reuse until an operator resolves it
- blocked conflicts update the conflict ledger status to `open`

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_run_next_job.py' -v`

Expected: FAIL because queue execution does not update guard ledgers yet.

- [ ] **Step 3: Extend queue / ledger / log schemas**

Add these queue columns:
- `assignment_id`
- `content_fingerprint`

Add these result-ledger columns:
- `conflict_id`
- `jump_target`

Add these run-log events:
- `guard_conflict_recorded`
- `assignment_updated`
- `override_applied`

Add CLI plumbing for:
- `--assignment-ledger`
- `--conflict-ledger`
- `--override-ledger`

- [ ] **Step 4: Implement guard-aware preflight and execution**

Update `run_preflight.py` so it accepts optional guard context, reuses account-matrix display names, and returns structured mismatch metadata instead of bare reasons.

Be explicit in code and tests that V1 has two browser-identity paths:
- caller-supplied `observed_account` can trigger `browser_identity_mismatch` during preflight
- runner-supplied `observed_account` / `jump_target` can be recorded and enforced after dispatch surfaces them

Do not pretend the default path has a brand-new pre-dispatch browser probe if it does not.

Update `run_next_job.py` so it:
- loads account, verification, assignment, conflict, and override ledgers
- applies preflight guard decisions before dispatch
- records new conflicts with `jump_target`
- passes `observed_account` / `jump_target` data from dispatch back into guard sync and treats browser-identity mismatch as enforceable whenever those fields are present
- updates assignment status on `running`, `blocked`, `cancelled`, and `published`
- keeps `publish_filtered`, `publish_failed`, and `runner_error` in a blocking non-success assignment state until an operator explicitly resolves or cancels the assignment

- [ ] **Step 5: Run the focused tests**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_run_preflight.py' -v`

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_run_next_job.py' -v`

Expected: PASS

## Task 4: Add Explicit Override Application Flow

**Files:**
- Create: `matrix-orchestrator/scripts/apply_guard_override.py`
- Create: `matrix-orchestrator/tests/test_apply_guard_override.py`
- Modify: `matrix-orchestrator/templates/job-queue.md`
- Modify: `matrix-orchestrator/templates/run-log.md`
- Modify: `docs/matrix/job-queue.md`
- Modify: `docs/matrix/run-log.md`

- [ ] **Step 1: Write failing override tests**

Cover:
- `continue_once` writes an override row, marks the conflict `overridden`, and flips the blocked queue row back to `pending`
- `cancel_job` writes an override row, marks the conflict `cancelled`, marks the assignment `cancelled`, and updates the queue row to `cancelled`
- override lookup is exact on `conflict_id + job_id + attempt_no`

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_apply_guard_override.py' -v`

Expected: FAIL because there is no explicit override entry point yet.

- [ ] **Step 2: Implement override application**

Add `apply_guard_override.py` as the only place that writes `operator-override-ledger.md` rows. Keep actions limited to:
- `continue_once`
- `cancel_job`

Update queue handling so `continue_once` can actually rerun a previously blocked job and `cancel_job` leaves an auditable terminal queue state.

- [ ] **Step 3: Run the focused tests**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_apply_guard_override.py' -v`

Expected: PASS

## Task 5: Extend Dispatch / Runtime Contracts and Finish Docs

**Files:**
- Modify: `matrix-orchestrator/scripts/dispatch_social_push.py`
- Modify: `matrix-orchestrator/references/social-push-contract.md`
- Modify: `matrix-orchestrator/tests/test_dispatch_social_push.py`
- Modify: `openclaw-cluster-orchestrator/scripts/dispatch_to_worker.py`
- Modify: `openclaw-cluster-orchestrator/references/dispatch-contract.md`
- Modify: `openclaw-cluster-orchestrator/tests/test_dispatch_to_worker.py`
- Modify: `openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py`
- Modify: `openclaw-cluster-orchestrator/tests/test_reset_cluster_runtime.py`
- Modify: `GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Write failing dispatch normalization tests**

Cover:
- JSON runner output preserves `jump_target`
- JSON runner output preserves `observed_account`
- non-JSON fallback still returns the legacy shape without breaking existing callers
- cluster worker dispatch propagates `--assignment-ledger`, `--conflict-ledger`, and `--override-ledger`
- cluster runtime reset clears `docs/ops/content-assignment-ledger.md`, `docs/ops/conflict-ledger.md`, and `docs/ops/operator-override-ledger.md`

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_dispatch_social_push.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_dispatch_to_worker.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_reset_cluster_runtime.py' -v`

Expected: FAIL because extra fields are dropped today, worker command lines do not carry guard-ledger paths, and runtime reset ignores `docs/ops/*`.

- [ ] **Step 2: Update dispatch normalization**

Keep the current result-status behavior, but preserve optional fields needed by the guard:
- `jump_target`
- `observed_account`

Do not make them mandatory for legacy runner outputs.
Also update the built-in prompt so the default runner explicitly asks for these optional fields when the publishing layer can observe them.

- [ ] **Step 3: Update cluster worker contract and reset tooling**

Update `dispatch_to_worker.py` and `dispatch-contract.md` so worker-side `run_next_job.py` calls include the new ops-ledger paths whenever the cluster runner is used.

Update `reset_cluster_runtime.py` and its tests so reset clears the new `docs/ops/*` ledgers alongside existing cluster/node runtime files.

- [ ] **Step 4: Update contracts and docs**

Document the new optional runner fields in `social-push-contract.md`, and add a short architecture note in `README.md` / `GUIDE.md` covering:
- where `docs/ops/*` lives
- what triggers a block
- how `continue_once` and `cancel_job` are recorded

- [ ] **Step 5: Run the focused tests**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -p 'test_dispatch_social_push.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_dispatch_to_worker.py' -v`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_reset_cluster_runtime.py' -v`

Expected: PASS

## Full Verification

- [ ] **Step 1: Run matrix-orchestrator test suite**

Run: `python3 -m unittest discover -s matrix-orchestrator/tests -v`

Expected: PASS

- [ ] **Step 2: Run cluster-orchestrator test suite**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -v`

Expected: PASS

- [ ] **Step 3: Sanity-check runtime docs**

Run: `rg -n 'assignment_id|content_fingerprint|conflict_id|jump_target' docs matrix-orchestrator openclaw-cluster-orchestrator`

Expected: The new guard fields appear consistently in templates, runtime files, tests, and code.
