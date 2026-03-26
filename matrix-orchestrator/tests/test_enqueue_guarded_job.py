from __future__ import annotations

import pathlib
import sys
import tempfile
import textwrap
import unittest


TESTS_DIR = pathlib.Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from util import load_script_module


ASSIGNMENT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    # Content Assignment Ledger (Runtime)

    | assignment_id | submission_ref | content_fingerprint | platform | account_alias | content_type | job_id | status | notes | created_at |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    """
).strip()

CONFLICT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    # Conflict Ledger (Runtime)

    | conflict_id | assignment_id | job_id | attempt_no | conflict_type | severity | status | summary | requested_account | observed_account | jump_target | notes | timestamp |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    """
).strip()

CLUSTER_QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | job_type | platform | account_alias | content_type | assignment_id | content_fingerprint | preferred_node | payload_json | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


class EnqueueGuardedJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("enqueue_guarded_job.py", "enqueue_guarded_job")
        cls.loader = load_script_module("load_markdown_table.py", "load_markdown_table")

    def test_enqueues_cluster_job_with_assignment_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            assignment_path = root / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            conflict_path = root / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            queue_path = root / "cluster-job-queue.md"
            queue_path.write_text(CLUSTER_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            row = self.module.enqueue_guarded_job(
                queue_path=queue_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                platform="zhihu",
                account_alias="main",
                content_type="idea",
                title="Guarded enqueue",
                body="This job should carry guard metadata.",
                preferred_node="worker-zhihu-01",
                submission_ref="ticket://guard-1",
            )

            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(len(assignment_rows), 1)
            self.assertEqual(assignment_rows[0]["assignment_id"], row["assignment_id"])
            self.assertEqual(assignment_rows[0]["content_fingerprint"], row["content_fingerprint"])
            self.assertEqual(assignment_rows[0]["job_id"], row["job_id"])
            self.assertEqual(assignment_rows[0]["status"], "queued")

            queue_rows = self.loader.load_markdown_table(queue_path)
            self.assertEqual(len(queue_rows), 1)
            self.assertEqual(queue_rows[0]["assignment_id"], row["assignment_id"])
            self.assertEqual(queue_rows[0]["content_fingerprint"], row["content_fingerprint"])

    def test_duplicate_content_records_conflict_and_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            assignment_path = root / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            conflict_path = root / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            queue_path = root / "cluster-job-queue.md"
            queue_path.write_text(CLUSTER_QUEUE_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            self.module.enqueue_guarded_job(
                queue_path=queue_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                platform="zhihu",
                account_alias="main",
                content_type="idea",
                title="Guarded enqueue",
                body="This job should carry guard metadata.",
                preferred_node="worker-zhihu-01",
                submission_ref="ticket://guard-1",
            )

            with self.assertRaisesRegex(Exception, "duplicate_content"):
                self.module.enqueue_guarded_job(
                    queue_path=queue_path,
                    assignment_ledger_path=assignment_path,
                    conflict_ledger_path=conflict_path,
                    platform="zhihu",
                    account_alias="alt",
                    content_type="idea",
                    title="Guarded enqueue",
                    body="This job should carry guard metadata.",
                    preferred_node="worker-zhihu-01",
                    submission_ref="ticket://guard-2",
                )

            conflict_rows = self.loader.load_markdown_table(conflict_path)
            self.assertEqual(len(conflict_rows), 1)
            self.assertEqual(conflict_rows[0]["conflict_type"], "duplicate_content")
            self.assertEqual(conflict_rows[0]["status"], "open")
            self.assertEqual(conflict_rows[0]["job_id"], "")


if __name__ == "__main__":
    unittest.main()
