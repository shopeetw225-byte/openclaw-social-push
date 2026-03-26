from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from util import load_script_module


class AppendClusterResultLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module(
            "append_cluster_result_ledger.py",
            "append_cluster_result_ledger",
        )

    def test_exports_append_cluster_result_ledger(self):
        self.assertTrue(hasattr(self.module, "append_cluster_result_ledger"))

    def test_appends_one_markdown_row_and_preserves_existing_content(self):
        ledger = textwrap.dedent(
            """
            # Cluster Result Ledger (Runtime)

            | job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            | cluster-job-1 | 1 | worker-zhihu-01 | publisher-zhihu | publish | routing_blocked | init | queued | 2026-03-24T10:00:00Z |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        self.module.append_cluster_result_ledger(
            ledger_path,
            {
                "job_id": "cluster-job-2",
                "attempt_no": 1,
                "node_id": "worker-reddit-01",
                "agent_id": "publisher-reddit",
                "job_type": "publish",
                "result_status": "publish_ok",
                "evidence": "https://example.com/post/2",
                "notes": "ok",
                "timestamp": "2026-03-24T10:01:00Z",
            },
        )

        updated = ledger_path.read_text(encoding="utf-8")
        self.assertIn(
            "| cluster-job-1 | 1 | worker-zhihu-01 | publisher-zhihu | publish | routing_blocked | init | queued | 2026-03-24T10:00:00Z |",
            updated,
        )
        self.assertIn(
            "| cluster-job-2 | 1 | worker-reddit-01 | publisher-reddit | publish | publish_ok | https://example.com/post/2 | ok | 2026-03-24T10:01:00Z |",
            updated,
        )

    def test_rejects_duplicate_terminal_row_for_same_job_attempt(self):
        ledger = textwrap.dedent(
            """
            | job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            | cluster-job-9 | 4 | worker-reddit-01 | publisher-reddit | publish | publish_ok | https://example.com/final | final | 2026-03-24T10:04:00Z |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        before = ledger_path.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            self.module.append_cluster_result_ledger(
                ledger_path,
                {
                    "job_id": "cluster-job-9",
                    "attempt_no": 4,
                    "node_id": "worker-reddit-01",
                    "agent_id": "publisher-reddit",
                    "job_type": "publish",
                    "result_status": "publish_failed",
                    "evidence": "retry",
                    "notes": "retry",
                    "timestamp": "2026-03-24T10:05:00Z",
                },
            )

        self.assertEqual(ledger_path.read_text(encoding="utf-8"), before)

    def test_escapes_pipe_characters_inside_cells(self):
        ledger = textwrap.dedent(
            """
            | job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        self.module.append_cluster_result_ledger(
            ledger_path,
            {
                "job_id": "cluster-job-11",
                "attempt_no": 1,
                "node_id": "worker-zhihu-01",
                "agent_id": "publisher-zhihu",
                "job_type": "publish",
                "result_status": "publish_failed",
                "evidence": "failure | redirected to signin",
                "notes": "reason | login required",
                "timestamp": "2026-03-24T10:06:00Z",
            },
        )

        updated = ledger_path.read_text(encoding="utf-8")
        self.assertIn("failure \\| redirected to signin", updated)
        self.assertIn("reason \\| login required", updated)


if __name__ == "__main__":
    unittest.main()
