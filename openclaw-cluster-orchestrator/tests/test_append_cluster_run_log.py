from __future__ import annotations

import pathlib
import tempfile
import unittest

from util import load_script_module


class AppendClusterRunLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module(
            "append_cluster_run_log.py",
            "append_cluster_run_log",
        )

    def test_exports_append_cluster_run_log(self):
        self.assertTrue(hasattr(self.module, "append_cluster_run_log"))

    def test_appends_one_row_and_preserves_existing_rows(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(
                "\n".join(
                    [
                        "# Cluster Run Log (Runtime)",
                        "",
                        "| job_id | attempt_no | node_id | event | status | notes | timestamp |",
                        "| --- | --- | --- | --- | --- | --- | --- |",
                        "| cluster-job-1 | 1 | worker-zhihu-01 | job_started | ok | queued | 2026-03-24T11:00:00Z |",
                    ]
                )
            )
            log_path = pathlib.Path(handle.name)

        self.module.append_cluster_run_log(
            log_path,
            {
                "job_id": "cluster-job-1",
                "attempt_no": 1,
                "node_id": "worker-zhihu-01",
                "event": "dispatch_started",
                "status": "running",
                "notes": "started",
                "timestamp": "2026-03-24T11:01:00Z",
            },
        )

        content = log_path.read_text(encoding="utf-8")
        self.assertIn(
            "| cluster-job-1 | 1 | worker-zhihu-01 | job_started | ok | queued | 2026-03-24T11:00:00Z |",
            content,
        )
        self.assertIn(
            "| cluster-job-1 | 1 | worker-zhihu-01 | dispatch_started | running | started | 2026-03-24T11:01:00Z |",
            content,
        )

    def test_creates_table_if_file_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "cluster-run-log.md"

            self.module.append_cluster_run_log(
                log_path,
                {
                    "job_id": "cluster-job-7",
                    "attempt_no": 3,
                    "node_id": "worker-reddit-01",
                    "event": "ledger_updated",
                    "status": "publish_ok",
                    "notes": "done",
                    "timestamp": "2026-03-24T11:02:00Z",
                },
            )

            self.assertEqual(
                log_path.read_text(encoding="utf-8"),
                "\n".join(
                    [
                        "| job_id | attempt_no | node_id | event | status | notes | timestamp |",
                        "| --- | --- | --- | --- | --- | --- | --- |",
                        "| cluster-job-7 | 3 | worker-reddit-01 | ledger_updated | publish_ok | done | 2026-03-24T11:02:00Z |",
                    ]
                )
                + "\n",
            )

    def test_appends_one_row_each_call_for_multiple_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "cluster-run-log.md"

            self.module.append_cluster_run_log(
                log_path,
                {
                    "job_id": "cluster-job-8",
                    "attempt_no": 1,
                    "node_id": "worker-zhihu-01",
                    "event": "job_started",
                    "status": "ok",
                    "notes": "queued",
                    "timestamp": "2026-03-24T11:03:00Z",
                },
            )
            self.module.append_cluster_run_log(
                log_path,
                {
                    "job_id": "cluster-job-8",
                    "attempt_no": 1,
                    "node_id": "worker-zhihu-01",
                    "event": "dispatch_finished",
                    "status": "publish_failed",
                    "notes": "failed",
                    "timestamp": "2026-03-24T11:04:00Z",
                },
            )

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(
                lines[-1],
                "| cluster-job-8 | 1 | worker-zhihu-01 | dispatch_finished | publish_failed | failed | 2026-03-24T11:04:00Z |",
            )


if __name__ == "__main__":
    unittest.main()
