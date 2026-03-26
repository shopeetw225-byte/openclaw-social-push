from __future__ import annotations

import pathlib
import io
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from util import load_script_module


CLUSTER_QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


def _cluster_row(
    job_id: str,
    attempt_no: int,
    status: str,
    *,
    job_type: str = "publish",
    platform: str = "zhihu",
    account_alias: str = "main",
    content_type: str = "idea",
    assignment_id: str = "",
    content_fingerprint: str = "",
    preferred_node: str = "",
    payload_json: str = '{"title":"Hello","body":"Body","media_paths":[]}',
    notes: str = "",
) -> str:
    return (
        f"| {job_id} | {attempt_no} | {job_type} | {platform} | {account_alias} | "
        f"{content_type} | {assignment_id} | {content_fingerprint} | {preferred_node} | "
        f"{payload_json} | {status} | {notes} |"
    )


NODE_MATRIX_TEMPLATE = textwrap.dedent(
    """
    | node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


def _node_row(
    node_id: str,
    *,
    mode: str = "local_agent",
    agent_id: str = "publisher-zhihu",
    platforms: str = "zhihu",
    account_aliases: str = "main",
    browser_profiles: str = "chrome-relay",
    capabilities: str = "publish",
    status: str = "ready",
    notes: str = "",
) -> str:
    return (
        f"| {node_id} | {mode} | {agent_id} |  | {platforms} | {account_aliases} | "
        f"{browser_profiles} | {capabilities} | {status} | {notes} |"
    )


NODE_QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | assignment_id | content_fingerprint | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


class RunNextClusterJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("run_next_cluster_job.py", "run_next_cluster_job")

    def test_blocks_when_another_cluster_job_is_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            _cluster_row("cluster-job-1", 1, "running"),
                            _cluster_row("cluster-job-2", 1, "pending"),
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[],
                dispatch_runner=lambda *_args, **_kwargs: {},
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                node_runtime_root=pathlib.Path(tmpdir) / "nodes",
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "running_job_exists")

    def test_blocks_with_routing_blocked_when_no_ready_worker_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-3", 1, "pending")) + "\n",
                encoding="utf-8",
            )

            ledger_calls = []
            log_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[],
                dispatch_runner=lambda *_args, **_kwargs: {},
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                node_runtime_root=pathlib.Path(tmpdir) / "nodes",
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| cluster-job-3 | 1 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | blocked | no_ready_worker |", queue_after)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(ledger_calls[-1]["result_status"], "routing_blocked")
            self.assertTrue(any(row["event"] == "job_started" for row in log_calls))

    def test_marks_done_and_writes_node_local_job_for_publish_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows=_cluster_row(
                        "cluster-job-4",
                        2,
                        "pending",
                        assignment_id="assignment-0004",
                        content_fingerprint="f" * 64,
                        preferred_node="worker-zhihu-01",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []
            log_calls = []
            dispatch_calls = []

            def fake_dispatch(node, payload):
                dispatch_calls.append((node, payload))
                return {
                    "ok": True,
                    "result_status": "publish_ok",
                    "evidence": "https://example.com/post/4",
                    "notes": "ok",
                }

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=fake_dispatch,
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                node_runtime_root=node_root,
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            node_queue_after = node_queue.read_text(encoding="utf-8")
            self.assertIn("| cluster-job-4 | 2 | publish | zhihu | main | idea | assignment-0004 | " + ("f" * 64) + " | worker-zhihu-01 | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | done | publish_ok |", queue_after)
            self.assertIn("| cluster-job-4 | 2 | zhihu | main | idea | Hello | Body |  | assignment-0004 | " + ("f" * 64) + " | pending | routed_from_cluster |", node_queue_after)
            self.assertEqual(dispatch_calls[0][1]["node_id"], "worker-zhihu-01")
            self.assertEqual(result["status"], "done")
            self.assertEqual(ledger_calls[-1]["result_status"], "publish_ok")
            self.assertTrue(any(row["event"] == "worker_selected" for row in log_calls))

    def test_fails_with_dispatch_error_when_worker_dispatch_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-5", 1, "pending")) + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": False,
                    "result_status": "dispatch_error",
                    "evidence": "",
                    "notes": "timeout",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **_kwargs: None,
                node_runtime_root=node_root,
            )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(ledger_calls[-1]["result_status"], "dispatch_error")

    def test_fails_with_dispatch_error_when_node_local_queue_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-5b", 1, "pending")) + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"

            ledger_calls = []
            log_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                    "evidence": "should-not-run",
                    "notes": "should-not-run",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                node_runtime_root=node_root,
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "dispatch_error")
            self.assertIn("| cluster-job-5b | 1 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | failed | dispatch_error |", queue_after)
            self.assertEqual(ledger_calls[-1]["result_status"], "dispatch_error")
            self.assertIn("worker_runtime_error", ledger_calls[-1]["notes"])
            self.assertTrue(any(row["event"] == "dispatch_finished" and row["status"] == "dispatch_error" for row in log_calls))

    def test_fails_with_dispatch_error_when_dispatch_runner_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-5c", 1, "pending")) + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []
            log_calls = []

            def boom(*_args, **_kwargs):
                raise RuntimeError("worker exploded")

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=boom,
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                node_runtime_root=node_root,
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "dispatch_error")
            self.assertIn("| cluster-job-5c | 1 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | failed | dispatch_error |", queue_after)
            self.assertEqual(ledger_calls[-1]["result_status"], "dispatch_error")
            self.assertIn("worker_runtime_error", ledger_calls[-1]["notes"])
            self.assertTrue(any(row["event"] == "dispatch_finished" and row["status"] == "dispatch_error" for row in log_calls))

    def test_blocks_on_worker_preflight_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-6", 1, "pending")) + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": False,
                    "result_status": "preflight_blocked",
                    "evidence": "",
                    "notes": "workflow_only",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **_kwargs: None,
                node_runtime_root=node_root,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(ledger_calls[-1]["result_status"], "preflight_blocked")

    def test_supports_dry_run_dispatch_without_real_worker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(rows=_cluster_row("cluster-job-7", 1, "pending")) + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **_kwargs: None,
                node_runtime_root=node_root,
                dry_run_result_status="publish_filtered",
                dry_run_evidence="demo://cluster/filter",
                dry_run_notes="demo",
            )

            self.assertEqual(result["status"], "done")
            self.assertEqual(ledger_calls[-1]["result_status"], "publish_filtered")

    def test_blocks_unsupported_non_publish_job_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows=_cluster_row("cluster-job-8", 1, "pending", job_type="collect_metrics")
                )
                + "\n",
                encoding="utf-8",
            )
            node_root = tmp / "nodes"
            node_queue = node_root / "worker-zhihu-01" / "matrix" / "job-queue.md"
            node_queue.parent.mkdir(parents=True, exist_ok=True)
            node_queue.write_text(NODE_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []
            log_calls = []

            result = self.module.run_next_cluster_job(
                queue_path=queue_path,
                node_matrix_rows=[
                    {
                        "node_id": "worker-zhihu-01",
                        "mode": "local_agent",
                        "agent_id": "publisher-zhihu",
                        "platforms": "zhihu",
                        "account_aliases": "main",
                        "browser_profiles": "chrome-relay",
                        "capabilities": "publish,collect_metrics",
                        "status": "ready",
                        "notes": "",
                    }
                ],
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                    "evidence": "should-not-run",
                    "notes": "should-not-run",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                node_runtime_root=node_root,
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            node_queue_after = node_queue.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "unsupported_job_type")
            self.assertIn("| cluster-job-8 | 1 | collect_metrics | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | blocked | unsupported_job_type |", queue_after)
            self.assertEqual(ledger_calls[-1]["result_status"], "routing_blocked")
            self.assertEqual(ledger_calls[-1]["job_type"], "collect_metrics")
            self.assertEqual(node_queue_after, NODE_QUEUE_TEMPLATE.format(rows="") + "\n")
            self.assertTrue(any(row["event"] == "ledger_updated" and row["status"] == "routing_blocked" for row in log_calls))

    def test_main_uses_dry_run_dispatch_runner_when_flag_is_present(self):
        captured: dict[str, object] = {}

        def fake_run_next_cluster_job(**kwargs):
            captured.update(kwargs)
            return {"status": "done", "reason": "publish_ok"}

        with patch.object(self.module, "run_next_cluster_job", side_effect=fake_run_next_cluster_job):
            with patch.object(
                self.module.sys,
                "argv",
                [
                    "run_next_cluster_job.py",
                    "--dry-run-result-status",
                    "publish_filtered",
                    "--dry-run-evidence",
                    "https://example.com/fake",
                    "--dry-run-notes",
                    "dry-run-only",
                ],
            ):
                with patch("sys.stdout", new=io.StringIO()):
                    exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("dispatch_runner", captured)
        dispatch_runner = captured["dispatch_runner"]
        self.assertTrue(callable(dispatch_runner))
        dispatch_result = dispatch_runner({}, {})
        self.assertEqual(
            dispatch_result,
            {
                "ok": True,
                "result_status": "publish_filtered",
                "evidence": "https://example.com/fake",
                "notes": "dry-run-only",
            },
        )

    def test_main_keeps_dispatch_runner_none_without_dry_run_flag(self):
        captured: dict[str, object] = {}

        def fake_run_next_cluster_job(**kwargs):
            captured.update(kwargs)
            return {"status": "blocked", "reason": "no_pending_job"}

        with patch.object(self.module, "run_next_cluster_job", side_effect=fake_run_next_cluster_job):
            with patch.object(self.module.sys, "argv", ["run_next_cluster_job.py"]):
                with patch("sys.stdout", new=io.StringIO()):
                    exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertIsNone(captured["dispatch_runner"])


if __name__ == "__main__":
    unittest.main()
