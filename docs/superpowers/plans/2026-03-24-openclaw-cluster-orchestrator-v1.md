# OpenClaw Cluster Orchestrator V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first working `openclaw-cluster-orchestrator` that routes `publish` jobs from a cluster queue to local worker agents inside one OpenClaw gateway, then records cluster-level results and logs.

**Architecture:** Add a new Thin Master layer that reads `docs/cluster/*`, selects one `ready` worker from a node matrix, writes a node-local matrix job under `docs/nodes/<node_id>/matrix/`, dispatches the matching worker agent, waits for the worker's terminal result, and writes cluster queue/ledger/log state. Reuse existing `matrix-orchestrator` and `social-push` inside worker nodes instead of duplicating publish logic.

**Tech Stack:** Python 3 stdlib CLI scripts, Markdown-table runtime files, OpenClaw CLI/Gateway, unittest, existing `matrix-orchestrator` script/testing patterns

---

## File Map

### New directories

- `openclaw-cluster-orchestrator/`
  Cluster master skill source.
- `openclaw-cluster-orchestrator/scripts/`
  Cluster routing/runtime scripts.
- `openclaw-cluster-orchestrator/tests/`
  Unit tests for cluster scripts.
- `openclaw-cluster-orchestrator/templates/`
  Cluster runtime markdown templates.
- `openclaw-cluster-orchestrator/references/`
  Master-to-worker dispatch contract docs.
- `docs/cluster/`
  Cluster runtime markdown files.
- `docs/nodes/worker-zhihu-01/matrix/`
  Sample node-local runtime for one worker.
- `docs/nodes/worker-reddit-01/matrix/`
  Sample node-local runtime for one worker.

### New files

- `openclaw-cluster-orchestrator/SKILL.md`
- `openclaw-cluster-orchestrator/agents/openai.yaml`
- `openclaw-cluster-orchestrator/references/dispatch-contract.md`
- `openclaw-cluster-orchestrator/templates/node-matrix.md`
- `openclaw-cluster-orchestrator/templates/cluster-job-queue.md`
- `openclaw-cluster-orchestrator/templates/cluster-result-ledger.md`
- `openclaw-cluster-orchestrator/templates/cluster-run-log.md`
- `openclaw-cluster-orchestrator/scripts/cluster_markdown_utils.py`
- `openclaw-cluster-orchestrator/scripts/load_node_matrix.py`
- `openclaw-cluster-orchestrator/scripts/select_worker.py`
- `openclaw-cluster-orchestrator/scripts/append_cluster_result_ledger.py`
- `openclaw-cluster-orchestrator/scripts/append_cluster_run_log.py`
- `openclaw-cluster-orchestrator/scripts/dispatch_to_worker.py`
- `openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py`
- `openclaw-cluster-orchestrator/tests/util.py`
- `openclaw-cluster-orchestrator/tests/test_load_node_matrix.py`
- `openclaw-cluster-orchestrator/tests/test_select_worker.py`
- `openclaw-cluster-orchestrator/tests/test_append_cluster_result_ledger.py`
- `openclaw-cluster-orchestrator/tests/test_append_cluster_run_log.py`
- `openclaw-cluster-orchestrator/tests/test_dispatch_to_worker.py`
- `openclaw-cluster-orchestrator/tests/test_run_next_cluster_job.py`
- `docs/cluster/node-matrix.md`
- `docs/cluster/cluster-job-queue.md`
- `docs/cluster/cluster-result-ledger.md`
- `docs/cluster/cluster-run-log.md`
- `docs/nodes/worker-zhihu-01/matrix/account-matrix.md`
- `docs/nodes/worker-zhihu-01/matrix/verification-matrix.md`
- `docs/nodes/worker-zhihu-01/matrix/job-queue.md`
- `docs/nodes/worker-zhihu-01/matrix/result-ledger.md`
- `docs/nodes/worker-zhihu-01/matrix/run-log.md`
- `docs/nodes/worker-reddit-01/matrix/account-matrix.md`
- `docs/nodes/worker-reddit-01/matrix/verification-matrix.md`
- `docs/nodes/worker-reddit-01/matrix/job-queue.md`
- `docs/nodes/worker-reddit-01/matrix/result-ledger.md`
- `docs/nodes/worker-reddit-01/matrix/run-log.md`

### Existing files to modify

- `README.md`
  Add the new cluster-control layer and runtime paths.
- `GUIDE.md`
  Add cluster runtime and local multi-agent setup notes.
- `docs/superpowers/specs/2026-03-24-openclaw-cluster-orchestrator-design.md`
  Keep aligned if implementation reveals one concrete v1 boundary adjustment.

## Task 1: Scaffold Cluster Skill and Runtime Templates

**Files:**
- Create: `openclaw-cluster-orchestrator/SKILL.md`
- Create: `openclaw-cluster-orchestrator/agents/openai.yaml`
- Create: `openclaw-cluster-orchestrator/references/dispatch-contract.md`
- Create: `openclaw-cluster-orchestrator/templates/node-matrix.md`
- Create: `openclaw-cluster-orchestrator/templates/cluster-job-queue.md`
- Create: `openclaw-cluster-orchestrator/templates/cluster-result-ledger.md`
- Create: `openclaw-cluster-orchestrator/templates/cluster-run-log.md`
- Create: `docs/cluster/node-matrix.md`
- Create: `docs/cluster/cluster-job-queue.md`
- Create: `docs/cluster/cluster-result-ledger.md`
- Create: `docs/cluster/cluster-run-log.md`
- Create: `docs/nodes/worker-zhihu-01/matrix/account-matrix.md`
- Create: `docs/nodes/worker-zhihu-01/matrix/verification-matrix.md`
- Create: `docs/nodes/worker-zhihu-01/matrix/job-queue.md`
- Create: `docs/nodes/worker-zhihu-01/matrix/result-ledger.md`
- Create: `docs/nodes/worker-zhihu-01/matrix/run-log.md`
- Create: `docs/nodes/worker-reddit-01/matrix/account-matrix.md`
- Create: `docs/nodes/worker-reddit-01/matrix/verification-matrix.md`
- Create: `docs/nodes/worker-reddit-01/matrix/job-queue.md`
- Create: `docs/nodes/worker-reddit-01/matrix/result-ledger.md`
- Create: `docs/nodes/worker-reddit-01/matrix/run-log.md`
- Test: `python3 /Users/openclawcn/.codex/skills/.system/skill-creator/scripts/quick_validate.py openclaw-cluster-orchestrator`

- [ ] **Step 1: Write the cluster templates and skill metadata**

Write minimal but complete runtime markdown tables with fixed columns, allowed statuses, and one or two realistic sample rows. Mirror the style already used by `matrix-orchestrator/` and `docs/matrix/*`.

- [ ] **Step 2: Validate the new skill**

Run: `python3 /Users/openclawcn/.codex/skills/.system/skill-creator/scripts/quick_validate.py openclaw-cluster-orchestrator`

Expected: `Skill is valid!`

- [ ] **Step 3: Verify sample runtime files are parseable Markdown tables**

Run: `rg -n '^[|]' docs/cluster docs/nodes/worker-zhihu-01/matrix docs/nodes/worker-reddit-01/matrix`

Expected: Each runtime file contains exactly one parseable table with fixed columns.

## Task 2: Add Cluster Markdown Helpers, Node Loader, and Worker Selection

**Files:**
- Create: `openclaw-cluster-orchestrator/scripts/cluster_markdown_utils.py`
- Create: `openclaw-cluster-orchestrator/scripts/load_node_matrix.py`
- Create: `openclaw-cluster-orchestrator/scripts/select_worker.py`
- Create: `openclaw-cluster-orchestrator/tests/util.py`
- Create: `openclaw-cluster-orchestrator/tests/test_load_node_matrix.py`
- Create: `openclaw-cluster-orchestrator/tests/test_select_worker.py`

- [ ] **Step 1: Write failing tests for node matrix parsing**

Add tests covering:
- escaped pipe parsing
- required columns
- row normalization
- empty table behavior

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_load_node_matrix.py' -v`

Expected: FAIL because loader does not exist yet.

- [ ] **Step 2: Write failing tests for worker selection**

Add tests covering:
- ready node selection
- `preferred_node`
- blocked when no ready worker
- exact `account_alias` preference over generic platform match
- `capabilities` coverage is mandatory
- `platforms` mismatch blocks selection
- deterministic tie-break order stays stable when multiple ready workers match

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_select_worker.py' -v`

Expected: FAIL because selector does not exist yet.

- [ ] **Step 3: Implement shared markdown helper and loader**

Implement:
- `split_markdown_row`
- `escape_markdown_cell`
- `format_markdown_row`
- `is_separator_row`
- `load_node_matrix(path)`

Follow the safer escaping/parsing pattern already used in the current `matrix-orchestrator` codebase.

- [ ] **Step 4: Implement `select_worker.py`**

Expose a function shaped like:

```python
def select_worker(node_rows: list[dict[str, str]], job: dict[str, str]) -> dict[str, str]:
    ...
```

Return the selected node row or raise a clear `ValueError("no_ready_worker")`.

- [ ] **Step 5: Run the focused tests**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_load_node_matrix.py' -v && python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_select_worker.py' -v`

Expected: PASS

## Task 3: Add Cluster Ledger and Run-Log Writers

**Files:**
- Create: `openclaw-cluster-orchestrator/scripts/append_cluster_result_ledger.py`
- Create: `openclaw-cluster-orchestrator/scripts/append_cluster_run_log.py`
- Create: `openclaw-cluster-orchestrator/tests/test_append_cluster_result_ledger.py`
- Create: `openclaw-cluster-orchestrator/tests/test_append_cluster_run_log.py`

- [ ] **Step 1: Write failing tests for append-only ledger behavior**

Cover:
- append one row
- preserve existing rows
- reject overwrite of same `job_id + attempt_no`
- preserve escaped pipe content

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_append_cluster_result_ledger.py' -v`

Expected: FAIL because writer does not exist yet.

- [ ] **Step 2: Write failing tests for run-log appends**

Cover:
- append one event row
- append multiple events for same job attempt
- create table if file is empty

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_append_cluster_run_log.py' -v`

Expected: FAIL because writer does not exist yet.

- [ ] **Step 3: Implement ledger and run-log appenders**

Mirror the patterns in:
- `matrix-orchestrator/scripts/append_result_ledger.py`
- `matrix-orchestrator/scripts/append_run_log.py`

But use cluster columns:
- ledger: `job_id`, `attempt_no`, `node_id`, `agent_id`, `job_type`, `result_status`, `evidence`, `notes`, `timestamp`
- run-log: `job_id`, `attempt_no`, `node_id`, `event`, `status`, `notes`, `timestamp`

- [ ] **Step 4: Run the focused tests**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_append_cluster_result_ledger.py' -v && python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_append_cluster_run_log.py' -v`

Expected: PASS

## Task 4: Implement Worker Dispatch with Terminal Result Waiting

**Files:**
- Create: `openclaw-cluster-orchestrator/scripts/dispatch_to_worker.py`
- Create: `openclaw-cluster-orchestrator/tests/test_dispatch_to_worker.py`

- [ ] **Step 1: Write failing tests for worker dispatch**

Cover:
- gateway-mode OpenClaw call command shape
- `toolUse` intermediate result followed until terminal session result
- `dispatch_error` on subprocess failure
- terminal `runner_error` returned from worker JSON
- plain commentary is not treated as success

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_dispatch_to_worker.py' -v`

Expected: FAIL because dispatch script does not exist yet.

- [ ] **Step 2: Implement worker dispatch**

Implement a function shaped like:

```python
def dispatch_to_worker(node: dict[str, str], payload: dict[str, object]) -> dict[str, str]:
    ...
```

Requirements:
- call `"$OPENCLAW_BIN" agent --json --agent <agent_id> -m <normalized prompt>`
- wait for terminal session result if first response stops on `toolUse`
- accept only worker terminal JSON with:
  - `ok`
  - `result_status`
  - `evidence`
  - `notes`
- map subprocess/gateway failures to `dispatch_error`

- [ ] **Step 3: Reuse the proven session-follow pattern**

Copy/adapt the safe pieces from:
- `matrix-orchestrator/scripts/dispatch_social_push.py`

Do not duplicate unrelated publish heuristics.

- [ ] **Step 4: Run the focused tests**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_dispatch_to_worker.py' -v`

Expected: PASS

## Task 5: Implement End-to-End Cluster Queue Runner

**Files:**
- Create: `openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py`
- Create: `openclaw-cluster-orchestrator/tests/test_run_next_cluster_job.py`
- Modify: `README.md`
- Modify: `GUIDE.md`

- [ ] **Step 1: Write failing tests for cluster queue state flow**

Cover:
- block when another cluster job is `running`
- block with `routing_blocked` when no ready worker exists
- fail with `dispatch_error` when worker dispatch fails
- mark `done` on `publish_ok`
- mark `done` on `publish_filtered`
- mark `blocked` on worker `preflight_blocked`
- mark `failed` on worker `publish_failed` and `runner_error`
- ensure `attempt_no` is preserved across queue/log/ledger
- ensure the selected worker is instructed to run `matrix-orchestrator/scripts/run_next_job.py` exactly once against `docs/nodes/<node_id>/matrix/*`

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_run_next_cluster_job.py' -v`

Expected: FAIL because runner does not exist yet.

- [ ] **Step 2: Implement cluster queue reader/writer**

Implement helpers mirroring `matrix-orchestrator/scripts/run_next_job.py`:
- read first pending row
- set `routing`
- select worker
- set `running`
- finalize to `done` / `failed` / `blocked`

- [ ] **Step 3: Implement node-local matrix job fan-out**

When a worker is selected:
- write one node-local job row into `docs/nodes/<node_id>/matrix/job-queue.md`
- preserve the node-local queue's existing completed rows
- do not write into shared `docs/matrix/job-queue.md`

- [ ] **Step 4: Make the worker entrypoint explicit in code**

Require `run_next_cluster_job.py` to construct one concrete worker prompt that tells the selected worker agent to execute:

```bash
python3 matrix-orchestrator/scripts/run_next_job.py \
  --queue docs/nodes/<node_id>/matrix/job-queue.md \
  --account-matrix docs/nodes/<node_id>/matrix/account-matrix.md \
  --verification-matrix docs/nodes/<node_id>/matrix/verification-matrix.md \
  --result-ledger docs/nodes/<node_id>/matrix/result-ledger.md \
  --run-log docs/nodes/<node_id>/matrix/run-log.md
```

The tests must assert that v1 workers do not bypass `matrix-orchestrator` and do not target shared `docs/matrix/*`.

- [ ] **Step 5: Wire dispatch and cluster result recording**

Use:
- `load_node_matrix.py`
- `select_worker.py`
- `dispatch_to_worker.py`
- `append_cluster_result_ledger.py`
- `append_cluster_run_log.py`

- [ ] **Step 6: Run the focused tests**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_run_next_cluster_job.py' -v`

Expected: PASS

- [ ] **Step 7: Add one fake-worker integration-style cluster test**

Add one integration-style cluster runner test that uses a fake worker runner and covers:
- successful publish
- dispatch failure / timeout
- worker terminal failure

This test must assert queue, ledger, and run-log transitions together.

- [ ] **Step 8: Run the full cluster test suite**

Run: `python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_*.py'`

Expected: PASS

- [ ] **Step 9: Update high-level docs**

Update `README.md` and `GUIDE.md` to describe:
- the new cluster layer
- the difference between `matrix-orchestrator` and `openclaw-cluster-orchestrator`
- the single-gateway multi-agent first version

## Task 6: Manual Verification and Runtime Smoke Test

**Files:**
- Modify: `docs/cluster/cluster-job-queue.md`
- Modify: `docs/cluster/cluster-result-ledger.md`
- Modify: `docs/cluster/cluster-run-log.md`
- Modify: `docs/nodes/worker-zhihu-01/matrix/job-queue.md` (runtime only if needed)
- Modify: `docs/nodes/worker-reddit-01/matrix/job-queue.md` (runtime only if needed)

- [ ] **Step 1: Add one realistic pending publish job**

Add one `pending` cluster row that targets a worker already represented in `docs/cluster/node-matrix.md`.

- [ ] **Step 2: Run the cluster job runner in dry mode or fake dispatch first**

Run a safe dry-path command if implemented, otherwise inject a fake worker runner in a one-off test harness.

Expected: queue, ledger, and run-log transition correctly.

- [ ] **Step 3: Run one real local multi-agent smoke test**

Run: `python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py`

Expected: the master selects one worker and records a truthful terminal result. It is acceptable if the real worker returns a truthful runtime failure such as `runner_error`; it is not acceptable to misclassify intermediate commentary as success.

- [ ] **Step 4: Final verification**

Run:

```bash
python3 -m unittest discover -s openclaw-cluster-orchestrator/tests -p 'test_*.py'
python3 /Users/openclawcn/.codex/skills/.system/skill-creator/scripts/quick_validate.py openclaw-cluster-orchestrator
git diff --check
```

Expected:
- all tests pass
- skill validates
- no diff-check errors
