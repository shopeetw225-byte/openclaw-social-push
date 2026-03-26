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

ACCOUNT_MATRIX_TEMPLATE = textwrap.dedent(
    """
    | account_alias | platform | display_name | browser_profile | default | notes |
    | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()

VERIFICATION_MATRIX_TEMPLATE = textwrap.dedent(
    """
    | platform | account_alias | content_type | status | last_verified | evidence | notes |
    | --- | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


def _queue_row(
    job_id: str,
    attempt_no: int,
    status: str,
    platform: str = "zhihu",
    account_alias: str = "main",
    content_type: str = "article",
    title: str = "Hello",
    body: str = "Body",
    media_paths: str = "",
    assignment_id: str = "",
    content_fingerprint: str = "",
    notes: str = "",
) -> str:
    return (
        f"| {job_id} | {attempt_no} | {platform} | {account_alias} | "
        f"{content_type} | {title} | {body} | {media_paths} | {assignment_id} | "
        f"{content_fingerprint} | {status} | {notes} |"
    )


class RunNextJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("run_next_job.py", "run_next_job")
        cls.loader = load_script_module("load_markdown_table.py", "load_markdown_table")

    def test_fails_fast_if_another_job_is_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows="\n".join(
                        [
                            _queue_row("job-1", 1, "running"),
                            _queue_row("job-2", 1, "pending"),
                        ]
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda *_args, **_kwargs: {},
                dispatch_runner=lambda *_args, **_kwargs: {},
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **_kwargs: None,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "running_job_exists")

    def test_transitions_pending_job_to_blocked_when_preflight_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(rows=_queue_row("job-1", 1, "pending")) + "\n",
                encoding="utf-8",
            )

            ledger_calls = []
            log_calls = []

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "block",
                    "reason": "workflow_only",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                verification_updater=lambda *_args, **_kwargs: None,
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| job-1 | 1 | zhihu | main | article | Hello | Body |  |  |  | blocked | workflow_only |", queue_after)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(ledger_calls[-1]["result_status"], "preflight_blocked")
            self.assertTrue(any(row["event"] == "decision_made" for row in log_calls))

    def test_transitions_pending_job_to_done_when_publish_succeeds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(rows=_queue_row("job-2", 1, "pending")) + "\n",
                encoding="utf-8",
            )

            ledger_calls = []
            verification_calls = []

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "go",
                    "reason": "real_publish_ok",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [{"status": "real_publish_ok"}],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                    "evidence": "https://example.com/post/2",
                    "notes": "ok",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **kwargs: verification_calls.append(kwargs["row"]),
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| job-2 | 1 | zhihu | main | article | Hello | Body |  |  |  | done | publish_ok |", queue_after)
            self.assertEqual(result["status"], "done")
            self.assertEqual(ledger_calls[-1]["result_status"], "publish_ok")
            self.assertEqual(verification_calls[-1]["status"], "real_publish_ok")

    def test_warn_requires_allow_warn_to_dispatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(rows=_queue_row("job-3", 1, "pending")) + "\n",
                encoding="utf-8",
            )

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, allow_warn=False, **_kwargs: {
                    "decision": "warn" if not allow_warn else "go",
                    "reason": "submit_ok_filtered" if not allow_warn else "warn_allowed",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [{"status": "submit_ok_filtered"}],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                },
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **_kwargs: None,
                allow_warn=False,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "warn_not_allowed")

    def test_transitions_pending_job_to_failed_when_dispatch_reports_publish_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = pathlib.Path(tmpdir) / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(rows=_queue_row("job-4", 1, "pending")) + "\n",
                encoding="utf-8",
            )

            ledger_calls = []
            verification_calls = []

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "go",
                    "reason": "real_publish_ok",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [{"status": "real_publish_ok"}],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": False,
                    "result_status": "publish_failed",
                    "evidence": "failure | evidence: none",
                    "notes": "reason | unsupported",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **kwargs: verification_calls.append(kwargs["row"]),
            )

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| job-4 | 1 | zhihu | main | article | Hello | Body |  |  |  | failed | publish_failed |", queue_after)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(ledger_calls[-1]["result_status"], "publish_failed")
            self.assertEqual(verification_calls, [])

    def test_guard_block_records_conflict_and_updates_assignment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows=_queue_row(
                        "job-10",
                        1,
                        "pending",
                        content_type="idea",
                        assignment_id="assignment-0001",
                        content_fingerprint="fp-1",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0001 | ticket://guard-1 | fp-1 | zhihu | main | idea | job-10 | queued | ingress accepted | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            ledger_calls = []
            log_calls = []

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "block",
                    "reason": "target_account_mismatch",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [],
                    "conflict_type": "target_account_mismatch",
                    "summary": "job account alias does not match assignment target account",
                    "requested_account": "main",
                    "observed_account": "alt",
                    "jump_target": "docs/matrix/job-queue.md#job-10",
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                },
                ledger_writer=lambda *_args, **kwargs: ledger_calls.append(kwargs["row"]),
                run_log_writer=lambda *_args, **kwargs: log_calls.append(kwargs["row"]),
                verification_updater=lambda *_args, **_kwargs: None,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(ledger_calls[-1]["result_status"], "preflight_blocked")
            self.assertEqual(ledger_calls[-1]["jump_target"], "docs/matrix/job-queue.md#job-10")
            self.assertTrue(ledger_calls[-1]["conflict_id"])
            self.assertTrue(any(row["event"] == "guard_conflict_recorded" for row in log_calls))

            queue_after = queue_path.read_text(encoding="utf-8")
            self.assertIn("| job-10 | 1 | zhihu | main | idea | Hello | Body |  | assignment-0001 | fp-1 | blocked | target_account_mismatch |", queue_after)

            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(assignment_rows[0]["status"], "blocked")
            conflict_rows = self.loader.load_markdown_table(conflict_path)
            self.assertEqual(conflict_rows[0]["conflict_type"], "target_account_mismatch")

    def test_publish_success_marks_assignment_published(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows=_queue_row(
                        "job-20",
                        1,
                        "pending",
                        content_type="idea",
                        assignment_id="assignment-0020",
                        content_fingerprint="fp-20",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0020 | ticket://guard-20 | fp-20 | zhihu | main | idea | job-20 | queued | ingress accepted | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "go",
                    "reason": "real_publish_ok",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [{"status": "real_publish_ok"}],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": True,
                    "result_status": "publish_ok",
                    "evidence": "https://example.com/post/20",
                    "notes": "ok",
                },
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **_kwargs: None,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
            )

            self.assertEqual(result["status"], "done")
            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(assignment_rows[0]["status"], "published")

    def test_runner_error_moves_assignment_to_blocking_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows=_queue_row(
                        "job-30",
                        1,
                        "pending",
                        content_type="idea",
                        assignment_id="assignment-0030",
                        content_fingerprint="fp-30",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0030 | ticket://guard-30 | fp-30 | zhihu | main | idea | job-30 | queued | ingress accepted | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")
            verification_calls = []

            result = self.module.run_next_job(
                queue_path=queue_path,
                preflight_runner=lambda job, **_kwargs: {
                    "decision": "go",
                    "reason": "real_publish_ok",
                    "normalized_task_inputs": {
                        "platform": job["platform"],
                        "account_alias": job["account_alias"],
                    },
                    "matched_rows": [{"status": "real_publish_ok"}],
                },
                dispatch_runner=lambda *_args, **_kwargs: {
                    "ok": False,
                    "result_status": "runner_error",
                    "evidence": "",
                    "notes": "browser missing",
                },
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **kwargs: verification_calls.append(kwargs["row"]),
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
            )

            self.assertEqual(result["status"], "failed")
            assignment_rows = self.loader.load_markdown_table(assignment_path)
            self.assertEqual(assignment_rows[0]["status"], "blocked")
            self.assertEqual(verification_calls, [])

    def test_default_preflight_uses_browser_probe_to_block_wrong_account(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            queue_path = tmp / "job-queue.md"
            queue_path.write_text(
                QUEUE_TEMPLATE.format(
                    rows=_queue_row(
                        "job-40",
                        1,
                        "pending",
                        content_type="idea",
                        assignment_id="assignment-0040",
                        content_fingerprint="fp-40",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            account_matrix_path = tmp / "account-matrix.md"
            account_matrix_path.write_text(
                ACCOUNT_MATRIX_TEMPLATE.format(
                    rows="| main | zhihu | Expected Name | chrome-relay | yes |  |"
                )
                + "\n",
                encoding="utf-8",
            )
            verification_matrix_path = tmp / "verification-matrix.md"
            verification_matrix_path.write_text(
                VERIFICATION_MATRIX_TEMPLATE.format(
                    rows="| zhihu | main | idea | real_publish_ok | 2026-03-26 | demo | ok |"
                )
                + "\n",
                encoding="utf-8",
            )
            assignment_path = tmp / "content-assignment-ledger.md"
            assignment_path.write_text(
                ASSIGNMENT_LEDGER_TEMPLATE.format(
                    rows="| assignment-0040 | ticket://guard-40 | fp-40 | zhihu | main | idea | job-40 | queued | ingress accepted | 2026-03-26T00:00:00Z |"
                )
                + "\n",
                encoding="utf-8",
            )
            conflict_path = tmp / "conflict-ledger.md"
            conflict_path.write_text(CONFLICT_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")
            override_path = tmp / "override-ledger.md"
            override_path.write_text(OVERRIDE_LEDGER_TEMPLATE.format(rows="") + "\n", encoding="utf-8")

            result = self.module.run_next_job(
                queue_path=queue_path,
                dispatch_runner=lambda *_args, **_kwargs: {"ok": True, "result_status": "publish_ok"},
                ledger_writer=lambda *_args, **_kwargs: None,
                run_log_writer=lambda *_args, **_kwargs: None,
                verification_updater=lambda *_args, **_kwargs: None,
                account_matrix_path=account_matrix_path,
                verification_matrix_path=verification_matrix_path,
                assignment_ledger_path=assignment_path,
                conflict_ledger_path=conflict_path,
                override_ledger_path=override_path,
                browser_probe_runner=lambda **_kwargs: {
                    "status": "ok",
                    "observed_account": "Wrong Name",
                    "jump_target": "https://example.com/editor",
                    "notes": "",
                },
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "browser_identity_mismatch")
