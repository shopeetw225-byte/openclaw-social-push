import importlib.util
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_preflight.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_script_module()

    def test_blocks_when_account_row_is_missing(self):
        result = self.module.run_preflight(
            verification_rows=[],
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "missing_verification_row")
        self.assertEqual(result["matched_rows"], [])
        self.assertEqual(
            result["normalized_task_inputs"],
            {
                "platform": "xhs",
                "account_alias": "main",
                "content_type": "",
                "job_id": "",
                "attempt_no": "",
                "assignment_id": "",
                "content_fingerprint": "",
                "observed_account": "",
                "jump_target": "",
            },
        )

    def test_go_when_real_publish_ok(self):
        rows = [
            {
                "platform": "xhs",
                "account_alias": "main",
                "status": "real_publish_ok",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "go")
        self.assertEqual(result["reason"], "real_publish_ok")
        self.assertEqual(result["matched_rows"], rows)

    def test_warn_when_submit_ok(self):
        rows = [
            {
                "platform": "xhs",
                "account_alias": "main",
                "status": "submit_ok",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "warn")
        self.assertEqual(result["reason"], "submit_ok")
        self.assertEqual(result["matched_rows"], rows)

    def test_warn_when_submit_ok_filtered(self):
        rows = [
            {
                "platform": "xhs",
                "account_alias": "main",
                "status": "submit_ok_filtered",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "warn")
        self.assertEqual(result["reason"], "submit_ok_filtered")
        self.assertEqual(result["matched_rows"], rows)

    def test_block_when_page_verified(self):
        rows = [
            {
                "platform": "xhs",
                "account_alias": "main",
                "status": "page_verified",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "page_verified")
        self.assertEqual(result["matched_rows"], rows)

    def test_block_when_workflow_only(self):
        rows = [
            {
                "platform": "xhs",
                "account_alias": "main",
                "status": "workflow_only",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": "xhs", "account_alias": "main"},
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "workflow_only")
        self.assertEqual(result["matched_rows"], rows)

    def test_allow_warn_promotes_warn_to_go(self):
        rows = [
            {
                "platform": " xHs ",
                "account_alias": " Main ",
                "status": " submit_ok ",
            }
        ]
        result = self.module.run_preflight(
            verification_rows=rows,
            task_inputs={"platform": " XHS ", "account_alias": " main "},
            allow_warn=True,
        )

        self.assertEqual(result["decision"], "go")
        self.assertEqual(result["reason"], "warn_allowed")
        self.assertEqual(
            result["normalized_task_inputs"],
            {
                "platform": "xhs",
                "account_alias": "main",
                "content_type": "",
                "job_id": "",
                "attempt_no": "",
                "assignment_id": "",
                "content_fingerprint": "",
                "observed_account": "",
                "jump_target": "",
            },
        )
        self.assertEqual(result["matched_rows"], rows)

    def test_blocks_when_assignment_account_alias_differs_from_job(self):
        verification_rows = [
            {
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "real_publish_ok",
            }
        ]
        assignment_rows = [
            {
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
                "platform": "zhihu",
                "account_alias": "alt",
                "content_type": "idea",
                "status": "queued",
            }
        ]

        result = self.module.run_preflight(
            verification_rows=verification_rows,
            task_inputs={
                "job_id": "job-1",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
            },
            assignment_rows=assignment_rows,
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "target_account_mismatch")
        self.assertEqual(result["conflict_type"], "target_account_mismatch")
        self.assertEqual(result["requested_account"], "main")
        self.assertEqual(result["observed_account"], "alt")

    def test_blocks_when_another_active_assignment_owns_same_fingerprint(self):
        verification_rows = [
            {
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "real_publish_ok",
            }
        ]
        assignment_rows = [
            {
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "queued",
            },
            {
                "assignment_id": "assignment-0002",
                "content_fingerprint": "fp-1",
                "platform": "zhihu",
                "account_alias": "alt",
                "content_type": "idea",
                "status": "running",
            },
        ]

        result = self.module.run_preflight(
            verification_rows=verification_rows,
            task_inputs={
                "job_id": "job-1",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
            },
            assignment_rows=assignment_rows,
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "duplicate_content")
        self.assertEqual(result["conflict_type"], "duplicate_content")

    def test_blocks_when_observed_account_differs_from_expected_display_name(self):
        verification_rows = [
            {
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "real_publish_ok",
            }
        ]
        assignment_rows = [
            {
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "queued",
            }
        ]
        account_rows = [
            {
                "platform": "zhihu",
                "account_alias": "main",
                "display_name": "Expected Name",
            }
        ]

        result = self.module.run_preflight(
            verification_rows=verification_rows,
            task_inputs={
                "job_id": "job-1",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
                "observed_account": "Other Name",
                "jump_target": "https://example.com/editor",
            },
            assignment_rows=assignment_rows,
            account_rows=account_rows,
        )

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["reason"], "browser_identity_mismatch")
        self.assertEqual(result["conflict_type"], "browser_identity_mismatch")
        self.assertEqual(result["jump_target"], "https://example.com/editor")

    def test_matching_continue_once_override_allows_guard_block_once(self):
        verification_rows = [
            {
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "real_publish_ok",
            }
        ]
        assignment_rows = [
            {
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
                "platform": "zhihu",
                "account_alias": "alt",
                "content_type": "idea",
                "status": "queued",
            }
        ]
        conflict_rows = [
            {
                "conflict_id": "conflict-0001",
                "assignment_id": "assignment-0001",
                "job_id": "job-1",
                "attempt_no": "1",
                "conflict_type": "target_account_mismatch",
                "status": "open",
            }
        ]
        override_rows = [
            {
                "conflict_id": "conflict-0001",
                "job_id": "job-1",
                "attempt_no": "1",
                "action": "continue_once",
            }
        ]

        result = self.module.run_preflight(
            verification_rows=verification_rows,
            task_inputs={
                "job_id": "job-1",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "assignment_id": "assignment-0001",
                "content_fingerprint": "fp-1",
            },
            assignment_rows=assignment_rows,
            conflict_rows=conflict_rows,
            override_rows=override_rows,
        )

        self.assertEqual(result["decision"], "go")
        self.assertEqual(result["reason"], "continue_once")
        self.assertEqual(result["conflict_id"], "conflict-0001")


if __name__ == "__main__":
    unittest.main()
