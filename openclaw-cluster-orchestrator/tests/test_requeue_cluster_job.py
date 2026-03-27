from __future__ import annotations

import pathlib
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


class RequeueClusterJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("requeue_cluster_job.py", "requeue_cluster_job")

    def test_exports_requeue_cluster_job(self):
        self.assertTrue(hasattr(self.module, "requeue_cluster_job"))

    def test_requeues_latest_failed_attempt_when_attempt_not_provided(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            _cluster_row("cluster-job-0007", 1, "failed", notes="runner_error"),
                            _cluster_row("cluster-job-0007", 2, "blocked", notes="no_ready_worker"),
                            _cluster_row("cluster-job-0009", 1, "done", notes="other_job"),
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            row = self.module.requeue_cluster_job(
                queue_path=queue_path,
                job_id="cluster-job-0007",
            )

            content = queue_path.read_text(encoding="utf-8")
            self.assertEqual(row["job_id"], "cluster-job-0007")
            self.assertEqual(row["attempt_no"], "3")
            self.assertEqual(row["status"], "pending")
            self.assertEqual(row["notes"], "retry_of:2")
            self.assertIn(
                "| cluster-job-0007 | 3 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | pending | retry_of:2 |",
                content,
            )
            self.assertIn("| cluster-job-0007 | 1 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | failed | runner_error |", content)
            self.assertIn("| cluster-job-0007 | 2 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | blocked | no_ready_worker |", content)

    def test_requeues_explicit_attempt_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows=_cluster_row(
                        "cluster-job-0010",
                        4,
                        "blocked",
                        job_type="risk_check",
                        platform="reddit",
                        account_alias="ops",
                        content_type="text_post",
                        assignment_id="assignment-0100",
                        content_fingerprint="a" * 64,
                        preferred_node="worker-reddit-02",
                        payload_json='{"title":"Risk","body":"Check","media_paths":["/tmp/a.png"]}',
                        notes="route_limit",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            row = self.module.requeue_cluster_job(
                queue_path=queue_path,
                job_id="cluster-job-0010",
                attempt_no="4",
                notes="manual retry",
            )

            content = queue_path.read_text(encoding="utf-8")
            self.assertEqual(row["attempt_no"], "5")
            self.assertEqual(row["job_type"], "risk_check")
            self.assertEqual(row["platform"], "reddit")
            self.assertEqual(row["account_alias"], "ops")
            self.assertEqual(row["content_type"], "text_post")
            self.assertEqual(row["assignment_id"], "assignment-0100")
            self.assertEqual(row["content_fingerprint"], "a" * 64)
            self.assertEqual(row["preferred_node"], "worker-reddit-02")
            self.assertEqual(row["payload_json"], '{"title":"Risk","body":"Check","media_paths":["/tmp/a.png"]}')
            self.assertEqual(row["status"], "pending")
            self.assertEqual(row["notes"], "manual retry")
            self.assertIn("| cluster-job-0010 | 5 | risk_check | reddit | ops | text_post | assignment-0100 | " + ("a" * 64) + ' | worker-reddit-02 | {"title":"Risk","body":"Check","media_paths":["/tmp/a.png"]} | pending | manual retry |', content)

    def test_explicit_retry_uses_next_global_attempt_number_for_same_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            _cluster_row("cluster-job-0011", 1, "failed", notes="runner_error"),
                            _cluster_row("cluster-job-0011", 2, "blocked", notes="no_ready_worker"),
                            _cluster_row("cluster-job-0011", 3, "failed", notes="dispatch_error"),
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            row = self.module.requeue_cluster_job(
                queue_path=queue_path,
                job_id="cluster-job-0011",
                attempt_no="1",
            )

            content = queue_path.read_text(encoding="utf-8")
            self.assertEqual(row["attempt_no"], "4")
            self.assertEqual(row["notes"], "retry_of:1")
            self.assertIn("| cluster-job-0011 | 4 | publish | zhihu | main | idea |  |  |  | {\"title\":\"Hello\",\"body\":\"Body\",\"media_paths\":[]} | pending | retry_of:1 |", content)

    def test_rejects_non_retryable_source_statuses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                CLUSTER_QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            _cluster_row("cluster-job-0001", 1, "pending"),
                            _cluster_row("cluster-job-0002", 1, "routing"),
                            _cluster_row("cluster-job-0003", 1, "running"),
                            _cluster_row("cluster-job-0004", 1, "done"),
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "source_status_not_retryable:pending"):
                self.module.requeue_cluster_job(queue_path=queue_path, job_id="cluster-job-0001")
            with self.assertRaisesRegex(ValueError, "source_status_not_retryable:routing"):
                self.module.requeue_cluster_job(queue_path=queue_path, job_id="cluster-job-0002")
            with self.assertRaisesRegex(ValueError, "source_status_not_retryable:running"):
                self.module.requeue_cluster_job(queue_path=queue_path, job_id="cluster-job-0003")
            with self.assertRaisesRegex(ValueError, "source_status_not_retryable:done"):
                self.module.requeue_cluster_job(queue_path=queue_path, job_id="cluster-job-0004")

    def test_main_parses_cli_arguments(self):
        class Args:
            queue = "docs/cluster/cluster-job-queue.md"
            job_id = "cluster-job-0007"
            attempt_no = "2"
            notes = "from cli"

        captured = {}

        def fake_requeue_cluster_job(**kwargs):
            captured.update(kwargs)
            return {"job_id": "cluster-job-0007", "attempt_no": "3"}

        with patch.object(
            self.module,
            "_build_arg_parser",
            return_value=type("Parser", (), {"parse_args": staticmethod(lambda: Args())})(),
        ), patch.object(self.module, "requeue_cluster_job", side_effect=fake_requeue_cluster_job):
            exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["queue_path"], "docs/cluster/cluster-job-queue.md")
        self.assertEqual(captured["job_id"], "cluster-job-0007")
        self.assertEqual(captured["attempt_no"], "2")
        self.assertEqual(captured["notes"], "from cli")


if __name__ == "__main__":
    unittest.main()
