from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from util import load_script_module


CLUSTER_QUEUE_TEMPLATE = textwrap.dedent(
    """
    # Cluster Queue

    | job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}

    <!-- queue footer -->
    """
).strip()

RUN_LOG_TEMPLATE = textwrap.dedent(
    """
    # Cluster Run Log
    | job_id | attempt_no | node_id | event | status | notes | timestamp |
    | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

RESULT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    # Cluster Result Ledger
    | job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

NODE_QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | assignment_id | content_fingerprint | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

NODE_RUN_LOG_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | event | status | notes | timestamp |
    | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

NODE_RESULT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | result_status | evidence | notes | timestamp |
    | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

OPS_LEDGER_TEMPLATE = textwrap.dedent(
    """
    | id | status | notes |
    | --- | --- | --- |
    {rows}
    """
).strip()


class ResetClusterRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("reset_cluster_runtime.py", "reset_cluster_runtime")

    def test_exports_reset_cluster_runtime(self):
        self.assertTrue(hasattr(self.module, "reset_cluster_runtime"))

    def test_dry_run_reports_targets_without_writing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            cluster_dir = tmp / "cluster"
            cluster_dir.mkdir(parents=True, exist_ok=True)
            nodes_root = tmp / "nodes"
            runtime_dir = nodes_root / "worker-zhihu-01" / "matrix"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            ops_dir = tmp / "ops"
            ops_dir.mkdir(parents=True, exist_ok=True)

            queue_path = cluster_dir / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows='| cluster-job-0001 | 1 | publish | zhihu | main | idea | assignment-0001 | fp-1 |  | {"title":"A"} | pending |  |'
                )
                + "\n",
                encoding="utf-8",
            )
            run_log_path = cluster_dir / "cluster-run-log.md"
            run_log_path.write_text(
                RUN_LOG_TEMPLATE.format(
                    rows="| cluster-job-0001 | 1 | worker-zhihu-01 | dispatch_finished | publish_ok | ok | 2026-03-25T10:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            result_ledger_path = cluster_dir / "cluster-result-ledger.md"
            result_ledger_path.write_text(
                RESULT_LEDGER_TEMPLATE.format(
                    rows="| cluster-job-0001 | 1 | worker-zhihu-01 | publisher-zhihu | publish | publish_ok | https://evidence | ok | 2026-03-25T10:00:01Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "job-queue.md").write_text(
                NODE_QUEUE_TEMPLATE.format(rows="| cluster-job-0001 | 1 | zhihu | main | idea | A | B |  | assignment-0001 | fp-1 | pending | routed_from_cluster |")
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "run-log.md").write_text(
                NODE_RUN_LOG_TEMPLATE.format(rows="| cluster-job-0001 | 1 | dispatch_finished | publish_ok | ok | 2026-03-25T10:00:02Z |")
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "result-ledger.md").write_text(
                NODE_RESULT_LEDGER_TEMPLATE.format(rows="| cluster-job-0001 | 1 | publish_ok | https://evidence | ok | 2026-03-25T10:00:03Z |")
                + "\n",
                encoding="utf-8",
            )
            assignment_path = ops_dir / "content-assignment-ledger.md"
            assignment_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| assignment-0001 | queued | ingress accepted |") + "\n",
                encoding="utf-8",
            )
            conflict_path = ops_dir / "conflict-ledger.md"
            conflict_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| conflict-0001 | open | blocked |") + "\n",
                encoding="utf-8",
            )
            override_path = ops_dir / "operator-override-ledger.md"
            override_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| override-0001 | continue_once | approved |") + "\n",
                encoding="utf-8",
            )

            queue_before = queue_path.read_text(encoding="utf-8")

            result = self.module.reset_cluster_runtime(
                cluster_queue_path=queue_path,
                cluster_run_log_path=run_log_path,
                cluster_result_ledger_path=result_ledger_path,
                node_runtime_root=nodes_root,
                ops_assignment_ledger_path=assignment_path,
                ops_conflict_ledger_path=conflict_path,
                ops_override_ledger_path=override_path,
                dry_run=True,
            )

            self.assertTrue(result["dry_run"])
            self.assertEqual(result["files_modified"], 0)
            self.assertGreaterEqual(result["rows_removed"], 9)
            self.assertEqual(queue_path.read_text(encoding="utf-8"), queue_before)
            self.assertTrue(any(str(path).endswith("cluster-job-queue.md") for path in result["targets"]))
            self.assertTrue(any(str(path).endswith("worker-zhihu-01/matrix/run-log.md") for path in result["targets"]))
            self.assertTrue(any(str(path).endswith("content-assignment-ledger.md") for path in result["targets"]))

    def test_reset_clears_cluster_and_node_runtime_rows_but_preserves_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            cluster_dir = tmp / "cluster"
            cluster_dir.mkdir(parents=True, exist_ok=True)
            nodes_root = tmp / "nodes"
            runtime_dir = nodes_root / "worker-zhihu-01" / "matrix"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            ops_dir = tmp / "ops"
            ops_dir.mkdir(parents=True, exist_ok=True)

            queue_path = cluster_dir / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            '| cluster-job-0001 | 1 | publish | zhihu | main | idea | assignment-0001 | fp-1 |  | {"title":"A"} | pending |  |',
                            '| cluster-job-0002 | 1 | publish | zhihu | main | idea | assignment-0002 | fp-2 |  | {"title":"B"} | running |  |',
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            run_log_path = cluster_dir / "cluster-run-log.md"
            run_log_path.write_text(
                RUN_LOG_TEMPLATE.format(
                    rows="\n".join(
                        [
                            "| cluster-job-0001 | 1 | worker-zhihu-01 | job_started | ok |  | 2026-03-25T10:00:00Z |",
                            "| cluster-job-0001 | 1 | worker-zhihu-01 | dispatch_finished | publish_ok | ok | 2026-03-25T10:00:01Z |",
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            result_ledger_path = cluster_dir / "cluster-result-ledger.md"
            result_ledger_path.write_text(
                RESULT_LEDGER_TEMPLATE.format(
                    rows="| cluster-job-0001 | 1 | worker-zhihu-01 | publisher-zhihu | publish | publish_ok | https://evidence | ok | 2026-03-25T10:00:02Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "job-queue.md").write_text(
                NODE_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            "| cluster-job-0001 | 1 | zhihu | main | idea | A | B |  | assignment-0001 | fp-1 | pending | routed_from_cluster |",
                            "| cluster-job-0002 | 1 | zhihu | main | idea | C | D |  | assignment-0002 | fp-2 | pending | routed_from_cluster |",
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "run-log.md").write_text(
                NODE_RUN_LOG_TEMPLATE.format(rows="| cluster-job-0001 | 1 | dispatch_finished | publish_ok | ok | 2026-03-25T10:00:03Z |")
                + "\n",
                encoding="utf-8",
            )
            (runtime_dir / "result-ledger.md").write_text(
                NODE_RESULT_LEDGER_TEMPLATE.format(rows="| cluster-job-0001 | 1 | publish_ok | https://evidence | ok | 2026-03-25T10:00:04Z |")
                + "\n",
                encoding="utf-8",
            )
            assignment_path = ops_dir / "content-assignment-ledger.md"
            assignment_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| assignment-0001 | queued | ingress accepted |") + "\n",
                encoding="utf-8",
            )
            conflict_path = ops_dir / "conflict-ledger.md"
            conflict_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| conflict-0001 | open | blocked |") + "\n",
                encoding="utf-8",
            )
            override_path = ops_dir / "operator-override-ledger.md"
            override_path.write_text(
                OPS_LEDGER_TEMPLATE.format(rows="| override-0001 | continue_once | approved |") + "\n",
                encoding="utf-8",
            )

            result = self.module.reset_cluster_runtime(
                cluster_queue_path=queue_path,
                cluster_run_log_path=run_log_path,
                cluster_result_ledger_path=result_ledger_path,
                node_runtime_root=nodes_root,
                ops_assignment_ledger_path=assignment_path,
                ops_conflict_ledger_path=conflict_path,
                ops_override_ledger_path=override_path,
                dry_run=False,
            )

            self.assertFalse(result["dry_run"])
            self.assertEqual(result["files_modified"], 9)
            self.assertEqual(result["rows_removed"], 12)

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |", queue_after)
            self.assertNotIn("cluster-job-0001", queue_after)
            self.assertIn("<!-- queue footer -->", queue_after)

            node_queue_after = (runtime_dir / "job-queue.md").read_text(encoding="utf-8")
            self.assertIn("| job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | assignment_id | content_fingerprint | status | notes |", node_queue_after)
            self.assertNotIn("cluster-job-0002", node_queue_after)


if __name__ == "__main__":
    unittest.main()
