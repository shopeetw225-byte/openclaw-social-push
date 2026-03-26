from __future__ import annotations

import fcntl
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest


TESTS_DIR = pathlib.Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from util import load_script_module


GUARD_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "content_assignment_guard.py"
)


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

OVERRIDE_LEDGER_TEMPLATE = textwrap.dedent(
    """
    # Operator Override Ledger (Runtime)

    | override_id | conflict_id | job_id | attempt_no | action | operator_ref | reason | timestamp |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    """
).strip()


def _sample_job(*, account_alias: str = "main") -> dict[str, object]:
    return {
        "platform": "zhihu",
        "account_alias": account_alias,
        "content_type": "article",
        "title": "Guard test title",
        "body": "Guard test body",
        "media_paths": ["/tmp/one.png", "/tmp/two.png"],
    }


def _load_guard_via_subprocess(snippet: str) -> list[str]:
    return [
        sys.executable,
        "-c",
        (
            "import importlib.util, pathlib\n"
            f"script_path = pathlib.Path({str(GUARD_SCRIPT_PATH)!r})\n"
            "spec = importlib.util.spec_from_file_location('content_assignment_guard', script_path)\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "assert spec.loader is not None\n"
            "spec.loader.exec_module(module)\n"
            f"{snippet}\n"
        ),
    ]


class ContentAssignmentGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module(
            "content_assignment_guard.py", "content_assignment_guard"
        )
        cls.loader = load_script_module("load_markdown_table.py", "load_markdown_table")

    def test_identical_content_generates_same_fingerprint(self):
        first = self.module.build_content_fingerprint(_sample_job(account_alias="main"))
        second = self.module.build_content_fingerprint(_sample_job(account_alias="alt"))
        self.assertEqual(first, second)

    def test_build_content_fingerprint_rejects_set_media_paths(self):
        with self.assertRaises(ValueError):
            self.module.build_content_fingerprint(
                {
                    "content_type": "article",
                    "title": "Guard test title",
                    "body": "Guard test body",
                    "media_paths": {"/tmp/two.png", "/tmp/one.png"},
                }
            )

    def test_different_target_accounts_with_identical_content_still_collide(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            first = self.module.reserve_assignment(
                assignment_ledger_path=assignment_path,
                submission_ref="ticket-100",
                platform="zhihu",
                account_alias="main",
                content_type="article",
                job_id="job-100",
                job_like=_sample_job(account_alias="main"),
            )
            self.assertEqual(first["status"], "reserved")

            with self.assertRaises(self.module.DuplicateContentError):
                self.module.reserve_assignment(
                    assignment_ledger_path=assignment_path,
                    submission_ref="ticket-101",
                    platform="zhihu",
                    account_alias="alt",
                    content_type="article",
                    job_id="job-101",
                    job_like=_sample_job(account_alias="alt"),
                )

    def test_cancelled_and_published_assignments_no_longer_block_new_reservations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            first = self.module.reserve_assignment(
                assignment_ledger_path=assignment_path,
                submission_ref="ticket-200",
                platform="zhihu",
                account_alias="main",
                content_type="article",
                job_id="job-200",
                job_like=_sample_job(account_alias="main"),
            )
            self.module.sync_assignment_terminal_state(
                assignment_ledger_path=assignment_path,
                assignment_id=first["assignment_id"],
                status="cancelled",
                notes="cancelled by operator",
            )

            second = self.module.reserve_assignment(
                assignment_ledger_path=assignment_path,
                submission_ref="ticket-201",
                platform="zhihu",
                account_alias="main",
                content_type="article",
                job_id="job-201",
                job_like=_sample_job(account_alias="main"),
            )
            self.module.sync_assignment_terminal_state(
                assignment_ledger_path=assignment_path,
                assignment_id=second["assignment_id"],
                status="published",
                notes="publish complete",
            )

            third = self.module.reserve_assignment(
                assignment_ledger_path=assignment_path,
                submission_ref="ticket-202",
                platform="zhihu",
                account_alias="main",
                content_type="article",
                job_id="job-202",
                job_like=_sample_job(account_alias="main"),
            )

            self.assertNotEqual(first["assignment_id"], second["assignment_id"])
            self.assertNotEqual(second["assignment_id"], third["assignment_id"])

    def test_reserve_assignment_waits_for_external_file_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            locked_handle = assignment_path.open("r+", encoding="utf-8")
            try:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                process = subprocess.Popen(
                    _load_guard_via_subprocess(
                        "\n".join(
                            [
                                f"assignment_path = pathlib.Path({str(assignment_path)!r})",
                                "module.reserve_assignment(",
                                "    assignment_ledger_path=assignment_path,",
                                "    submission_ref='ticket-locked',",
                                "    platform='zhihu',",
                                "    account_alias='main',",
                                "    content_type='article',",
                                "    job_id='job-locked',",
                                "    job_like={",
                                "        'content_type': 'article',",
                                "        'title': 'Guard test title',",
                                "        'body': 'Guard test body',",
                                "        'media_paths': ['/tmp/one.png', '/tmp/two.png'],",
                                "    },",
                                ")",
                            ]
                        )
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                time.sleep(0.25)
                self.assertIsNone(process.poll())
            finally:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_UN)
                locked_handle.close()

            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr or stdout)

    def test_record_conflict_waits_for_external_file_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conflict_path = pathlib.Path(tmpdir) / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            locked_handle = conflict_path.open("r+", encoding="utf-8")
            try:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                process = subprocess.Popen(
                    _load_guard_via_subprocess(
                        "\n".join(
                            [
                                f"conflict_path = pathlib.Path({str(conflict_path)!r})",
                                "module.record_conflict(",
                                "    conflict_ledger_path=conflict_path,",
                                "    assignment_id='assignment-0001',",
                                "    job_id='job-locked',",
                                "    attempt_no=1,",
                                "    conflict_type='duplicate_content',",
                                "    summary='duplicate',",
                                "    requested_account='main',",
                                "    observed_account='alt',",
                                "    jump_target='https://example.com/locked',",
                                ")",
                            ]
                        )
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                time.sleep(0.25)
                self.assertIsNone(process.poll())
            finally:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_UN)
                locked_handle.close()

            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr or stdout)

    def test_sync_assignment_terminal_state_waits_for_external_file_lock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE
                + "\n"
                + "| assignment-0001 | ticket://ops-1 | abc123 | zhihu | main | article | job-1 | reserved | pending | 2026-03-26T02:00:00Z |\n",
                encoding="utf-8",
            )

            locked_handle = assignment_path.open("r+", encoding="utf-8")
            try:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                process = subprocess.Popen(
                    _load_guard_via_subprocess(
                        "\n".join(
                            [
                                f"assignment_path = pathlib.Path({str(assignment_path)!r})",
                                "module.sync_assignment_terminal_state(",
                                "    assignment_ledger_path=assignment_path,",
                                "    assignment_id='assignment-0001',",
                                "    status='cancelled',",
                                "    notes='cancelled under lock',",
                                ")",
                            ]
                        )
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                time.sleep(0.25)
                self.assertIsNone(process.poll())
            finally:
                fcntl.flock(locked_handle.fileno(), fcntl.LOCK_UN)
                locked_handle.close()

            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr or stdout)

    def test_continue_once_only_applies_to_one_conflict_job_attempt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            override_path = pathlib.Path(tmpdir) / "operator-override-ledger.md"
            override_path.write_text(
                OVERRIDE_LEDGER_TEMPLATE
                + "\n"
                + "| override-0001 | conflict-0010 | job-10 | 2 | continue_once | op://main | checked | 2026-03-26T03:00:00Z |\n",
                encoding="utf-8",
            )

            matched = self.module.find_applicable_override(
                override_ledger_path=override_path,
                conflict_id="conflict-0010",
                job_id="job-10",
                attempt_no=2,
            )
            self.assertIsNotNone(matched)
            self.assertEqual(matched["action"], "continue_once")

            self.assertIsNone(
                self.module.find_applicable_override(
                    override_ledger_path=override_path,
                    conflict_id="conflict-0010",
                    job_id="job-10",
                    attempt_no=3,
                )
            )
            self.assertIsNone(
                self.module.find_applicable_override(
                    override_ledger_path=override_path,
                    conflict_id="conflict-0099",
                    job_id="job-10",
                    attempt_no=2,
                )
            )

    def test_find_applicable_override_rejects_invalid_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            override_path = pathlib.Path(tmpdir) / "operator-override-ledger.md"
            override_path.write_text(
                OVERRIDE_LEDGER_TEMPLATE
                + "\n"
                + "| override-0001 | conflict-0010 | job-10 | 2 | skip_forever | op://main | checked | 2026-03-26T03:00:00Z |\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                self.module.find_applicable_override(
                    override_ledger_path=override_path,
                    conflict_id="conflict-0010",
                    job_id="job-10",
                    attempt_no=2,
                )

    def test_cancel_job_marks_linked_assignment_as_cancelled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(ASSIGNMENT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            conflict_path = pathlib.Path(tmpdir) / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE + "\n", encoding="utf-8")
            override_path = pathlib.Path(tmpdir) / "operator-override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            assignment = self.module.reserve_assignment(
                assignment_ledger_path=assignment_path,
                submission_ref="ticket-300",
                platform="zhihu",
                account_alias="main",
                content_type="article",
                job_id="job-300",
                job_like=_sample_job(account_alias="main"),
            )
            conflict = self.module.record_conflict(
                conflict_ledger_path=conflict_path,
                assignment_id=assignment["assignment_id"],
                job_id="job-300",
                attempt_no=1,
                conflict_type="browser_identity_mismatch",
                summary="browser identity mismatch",
                requested_account="main",
                observed_account="alt",
                jump_target="https://example.com/editor",
            )

            override_path.write_text(
                override_path.read_text(encoding="utf-8")
                + "| override-0001 | "
                + conflict["conflict_id"]
                + " | job-300 | 1 | cancel_job | op://main | cancelled | 2026-03-26T03:10:00Z |\n",
                encoding="utf-8",
            )

            override = self.module.find_applicable_override(
                override_ledger_path=override_path,
                conflict_id=conflict["conflict_id"],
                job_id="job-300",
                attempt_no=1,
            )
            self.assertIsNotNone(override)
            self.assertEqual(override["action"], "cancel_job")

            self.module.sync_assignment_terminal_state(
                assignment_ledger_path=assignment_path,
                assignment_id=assignment["assignment_id"],
                status="cancelled",
                notes="cancel_job override applied",
            )
            rows = self.loader.load_markdown_table(assignment_path)
            assignment_rows = [
                row for row in rows if row["assignment_id"] == assignment["assignment_id"]
            ]
            self.assertEqual(len(assignment_rows), 1)
            self.assertEqual(assignment_rows[0]["status"], "cancelled")

    def test_record_conflict_rejects_invalid_allowed_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            conflict_path = pathlib.Path(tmpdir) / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE + "\n", encoding="utf-8")

            invalid_cases = [
                {
                    "conflict_type": "wrong_type",
                    "severity": "block",
                    "status": "open",
                },
                {
                    "conflict_type": "duplicate_content",
                    "severity": "warn",
                    "status": "open",
                },
                {
                    "conflict_type": "duplicate_content",
                    "severity": "block",
                    "status": "paused",
                },
            ]

            for invalid_case in invalid_cases:
                with self.subTest(invalid_case=invalid_case):
                    with self.assertRaises(ValueError):
                        self.module.record_conflict(
                            conflict_ledger_path=conflict_path,
                            assignment_id="assignment-0001",
                            job_id="job-300",
                            attempt_no=1,
                            summary="bad conflict metadata",
                            requested_account="main",
                            observed_account="alt",
                            jump_target="https://example.com/editor",
                            **invalid_case,
                        )

    def test_sync_assignment_terminal_state_rejects_invalid_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assignment_path = pathlib.Path(tmpdir) / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE
                + "\n"
                + "| assignment-0001 | ticket://ops-1 | abc123 | zhihu | main | article | job-1 | reserved | pending | 2026-03-26T02:00:00Z |\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                self.module.sync_assignment_terminal_state(
                    assignment_ledger_path=assignment_path,
                    assignment_id="assignment-0001",
                    status="archived",
                )


if __name__ == "__main__":
    unittest.main()
