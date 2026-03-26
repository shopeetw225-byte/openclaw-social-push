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


QUEUE_TEMPLATE = textwrap.dedent(
    """
    | job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | assignment_id | content_fingerprint | status | notes |
    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

ASSIGNMENT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    | assignment_id | submission_ref | content_fingerprint | platform | account_alias | content_type | job_id | status | notes | created_at |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

CONFLICT_LEDGER_TEMPLATE = textwrap.dedent(
    """
    | conflict_id | assignment_id | job_id | attempt_no | conflict_type | severity | status | summary | requested_account | observed_account | jump_target | notes | timestamp |
    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

OVERRIDE_LEDGER_TEMPLATE = textwrap.dedent(
    """
    | override_id | conflict_id | job_id | attempt_no | action | operator_ref | reason | timestamp |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


class ApplyGuardOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("apply_guard_override.py", "apply_guard_override")
        cls.loader = load_script_module("load_markdown_table.py", "load_markdown_table")

    def test_continue_once_records_override_and_requeues_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows="| job-1 | 1 | zhihu | main | idea | Hello | Body |  | assignment-0001 | fp-1 | blocked | target_account_mismatch |"
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0001 | ticket://guard-1 | fp-1 | zhihu | main | idea | job-1 | blocked | target_account_mismatch | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(
                CONFLICT_LEDGER_TEMPLATE.format(
                    rows="| conflict-0001 | assignment-0001 | job-1 | 1 | target_account_mismatch | block | open | mismatch | main | alt | docs/matrix/job-queue.md#job-1 | blocked | 2026-03-26T00:00:01Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            row = self.module.apply_guard_override(
                queue_path=queue_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
                conflict_id="conflict-0001",
                job_id="job-1",
                attempt_no="1",
                action="continue_once",
                operator_ref="op://main",
                reason="checked and approved",
            )

            self.assertEqual(row["action"], "continue_once")
            queue_rows = self.loader.load_markdown_table(queue_path)
            self.assertEqual(queue_rows[0]["status"], "pending")
            self.assertEqual(queue_rows[0]["notes"], "continue_once")
            conflict_rows = self.loader.load_markdown_table(conflict_path)
            self.assertEqual(conflict_rows[0]["status"], "overridden")
            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(assignment_rows[0]["status"], "blocked")

    def test_cancel_job_records_override_and_cancels_assignment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows="| job-2 | 1 | zhihu | main | idea | Hello | Body |  | assignment-0002 | fp-2 | blocked | browser_identity_mismatch |"
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0002 | ticket://guard-2 | fp-2 | zhihu | main | idea | job-2 | blocked | browser_identity_mismatch | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(
                CONFLICT_LEDGER_TEMPLATE.format(
                    rows="| conflict-0002 | assignment-0002 | job-2 | 1 | browser_identity_mismatch | block | open | mismatch | main | alt | https://example.com/editor | blocked | 2026-03-26T00:00:01Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            row = self.module.apply_guard_override(
                queue_path=queue_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
                conflict_id="conflict-0002",
                job_id="job-2",
                attempt_no="1",
                action="cancel_job",
                operator_ref="op://main",
                reason="cancel this job",
            )

            self.assertEqual(row["action"], "cancel_job")
            queue_rows = self.loader.load_markdown_table(queue_path)
            self.assertEqual(queue_rows[0]["status"], "cancelled")
            self.assertEqual(queue_rows[0]["notes"], "cancel_job")
            conflict_rows = self.loader.load_markdown_table(conflict_path)
            self.assertEqual(conflict_rows[0]["status"], "cancelled")
            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(assignment_rows[0]["status"], "cancelled")

    def test_override_lookup_is_exact_on_conflict_job_attempt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            "| job-3 | 1 | zhihu | main | idea | Hello | Body |  | assignment-0003 | fp-3 | blocked | target_account_mismatch |",
                            "| job-3 | 2 | zhihu | main | idea | Hello | Body |  | assignment-0003 | fp-3 | blocked | target_account_mismatch |",
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0003 | ticket://guard-3 | fp-3 | zhihu | main | idea | job-3 | blocked | target_account_mismatch | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(
                CONFLICT_LEDGER_TEMPLATE.format(
                    rows="\n".join(
                        [
                            "| conflict-0003 | assignment-0003 | job-3 | 1 | target_account_mismatch | block | open | mismatch | main | alt | docs/matrix/job-queue.md#job-3 | blocked | 2026-03-26T00:00:01Z |",
                            "| conflict-0004 | assignment-0003 | job-3 | 2 | target_account_mismatch | block | open | mismatch | main | alt | docs/matrix/job-queue.md#job-3 | blocked | 2026-03-26T00:00:02Z |",
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            self.module.apply_guard_override(
                queue_path=queue_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
                conflict_id="conflict-0004",
                job_id="job-3",
                attempt_no="2",
                action="continue_once",
                operator_ref="op://main",
                reason="retry second attempt only",
            )

            queue_rows = self.loader.load_markdown_table(queue_path)
            self.assertEqual(queue_rows[0]["status"], "blocked")
            self.assertEqual(queue_rows[1]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
