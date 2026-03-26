from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest
from unittest import mock

from util import load_script_module


QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


class EnqueueClusterJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("enqueue_cluster_job.py", "enqueue_cluster_job")

    def test_exports_enqueue_cluster_job(self):
        self.assertTrue(hasattr(self.module, "enqueue_cluster_job"))

    def test_appends_pending_publish_job_with_generated_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            "| cluster-job-0001 | 1 | publish | zhihu | main | idea | assignment-0001 | deadbeef | worker-zhihu-01 | {\"title\":\"Old\",\"body\":\"Old\",\"media_paths\":[]} | failed | runner_error |",
                            "| cluster-job-0002 | 1 | publish | reddit | main | text_post | assignment-0002 | cafe1234 | worker-reddit-01 | {\"title\":\"Old 2\",\"body\":\"Old 2\",\"media_paths\":[]} | done | publish_ok |",
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            row = self.module.enqueue_cluster_job(
                queue_path=queue_path,
                platform="zhihu",
                account_alias="main",
                content_type="idea",
                title="New title",
                body="New body",
                preferred_node="worker-zhihu-01",
                notes="queued from test",
            )

            content = queue_path.read_text(encoding="utf-8")
            self.assertEqual(row["job_id"], "cluster-job-0003")
            self.assertIn(
                '| cluster-job-0003 | 1 | publish | zhihu | main | idea |  |  | worker-zhihu-01 | {"title":"New title","body":"New body","media_paths":[]} | pending | queued from test |',
                content,
            )

    def test_accepts_media_paths_and_explicit_job_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            row = self.module.enqueue_cluster_job(
                queue_path=queue_path,
                platform="reddit",
                account_alias="main",
                content_type="image_post",
                title="Images",
                body="Gallery",
                media_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
                job_id="cluster-job-0100",
                notes="images",
            )

            content = queue_path.read_text(encoding="utf-8")
            self.assertEqual(row["job_id"], "cluster-job-0100")
            self.assertIn(
                '{"title":"Images","body":"Gallery","media_paths":["/tmp/a.jpg","/tmp/b.jpg"]}',
                content,
            )
            self.assertEqual(row["assignment_id"], "")
            self.assertEqual(row["content_fingerprint"], "")

    def test_accepts_assignment_metadata_without_interpreting_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            row = self.module.enqueue_cluster_job(
                queue_path=queue_path,
                platform="zhihu",
                account_alias="main",
                content_type="idea",
                assignment_id="assignment-0100",
                content_fingerprint="a" * 64,
                title="Guarded",
                body="Guarded body",
                notes="metadata passthrough",
            )

            self.assertEqual(row["assignment_id"], "assignment-0100")
            self.assertEqual(row["content_fingerprint"], "a" * 64)
            content = queue_path.read_text(encoding="utf-8")
            self.assertIn(
                "| cluster-job-0001 | 1 | publish | zhihu | main | idea | assignment-0100 | "
                + ("a" * 64)
                + ' |  | {"title":"Guarded","body":"Guarded body","media_paths":[]} | pending | metadata passthrough |',
                content,
            )

    def test_rejects_non_publish_job_type_in_v1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsupported_job_type"):
                self.module.enqueue_cluster_job(
                    queue_path=queue_path,
                    platform="zhihu",
                    account_alias="main",
                    content_type="idea",
                    title="Nope",
                    body="Nope",
                    job_type="collect_metrics",
                )

    def test_rejects_duplicate_job_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "cluster-job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows='| cluster-job-0007 | 1 | publish | zhihu | main | idea |  |  |  | {"title":"Old","body":"Old","media_paths":[]} | done | publish_ok |'
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate_job_id"):
                self.module.enqueue_cluster_job(
                    queue_path=queue_path,
                    platform="zhihu",
                    account_alias="main",
                    content_type="idea",
                    title="Duplicate",
                    body="Duplicate",
                    job_id="cluster-job-0007",
                )

    def test_main_routes_to_guarded_enqueue_when_assignment_metadata_missing(self):
        class Args:
            queue = "docs/cluster/cluster-job-queue.md"
            platform = "zhihu"
            account_alias = "main"
            content_type = "idea"
            title = "Guarded"
            body = "Body"
            media_path = []
            assignment_id = ""
            content_fingerprint = ""
            preferred_node = "worker-zhihu-01"
            notes = "guarded"
            submission_ref = "ticket://guard-1"
            assignment_ledger = "docs/ops/content-assignment-ledger.md"
            conflict_ledger = "docs/ops/conflict-ledger.md"
            job_type = "publish"
            job_id = None

        captured = {}

        class GuardedModule:
            @staticmethod
            def enqueue_guarded_job(**kwargs):
                captured.update(kwargs)
                return {"job_id": "cluster-job-0001"}

        with mock.patch.object(
            self.module,
            "_build_arg_parser",
            return_value=type("Parser", (), {"parse_args": staticmethod(lambda: Args())})(),
        ), mock.patch.object(
            self.module,
            "_guarded_enqueue_module",
            return_value=GuardedModule,
        ):
            exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["queue_path"], "docs/cluster/cluster-job-queue.md")
        self.assertEqual(captured["assignment_ledger_path"], "docs/ops/content-assignment-ledger.md")
        self.assertEqual(captured["conflict_ledger_path"], "docs/ops/conflict-ledger.md")
        self.assertEqual(captured["submission_ref"], "ticket://guard-1")


if __name__ == "__main__":
    unittest.main()
