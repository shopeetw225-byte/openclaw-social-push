import importlib.util
import pathlib
import tempfile
import textwrap
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "append_result_ledger.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("append_result_ledger", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AppendResultLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_script_module()

    def test_exports_append_result_ledger(self):
        self.assertTrue(hasattr(self.module, "append_result_ledger"))

    def test_appends_one_markdown_row_and_preserves_existing_content(self):
        ledger = textwrap.dedent(
            """
            # Result Ledger (Runtime)

            | job_id | attempt_no | platform | account_alias | content_type | decision | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            | job-1 | 1 | zhihu | main | article | go | preflight_warn | init | queued | 2026-03-23T10:00:00Z |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        self.module.append_result_ledger(
            ledger_path,
            {
                "job_id": "job-2",
                "attempt_no": 1,
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "decision": "go",
                "result_status": "publish_ok",
                "evidence": "https://example.com/post/2",
                "notes": "started",
                "timestamp": "2026-03-23T10:01:00Z",
            },
        )

        updated = ledger_path.read_text(encoding="utf-8")
        self.assertIn(
            "| job-1 | 1 | zhihu | main | article | go | preflight_warn | init | queued | 2026-03-23T10:00:00Z |",
            updated,
        )
        self.assertIn(
            "| job-2 | 1 | reddit | main | text_post | go | publish_ok | https://example.com/post/2 | started | 2026-03-23T10:01:00Z |",
            updated,
        )

    def test_append_is_deterministic_and_append_only(self):
        ledger = textwrap.dedent(
            """
            | job_id | attempt_no | platform | account_alias | content_type | decision | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        self.module.append_result_ledger(
            ledger_path,
            {
                "job_id": "job-3",
                "attempt_no": 2,
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "decision": "go",
                "result_status": "publish_ok",
                "evidence": "https://example.com/1",
                "notes": "phase-1",
                "timestamp": "2026-03-23T10:02:00Z",
            },
        )
        first_append = ledger_path.read_text(encoding="utf-8")

        self.module.append_result_ledger(
            ledger_path,
            {
                "job_id": "job-3",
                "attempt_no": 3,
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "decision": "go",
                "result_status": "publish_ok",
                "evidence": "https://example.com/2",
                "notes": "phase-2",
                "timestamp": "2026-03-23T10:03:00Z",
            },
        )
        second_append = ledger_path.read_text(encoding="utf-8")

        self.assertTrue(second_append.startswith(first_append))
        self.assertEqual(second_append.count("| job-3 | 2 | reddit | main | text_post |"), 1)
        self.assertEqual(second_append.count("| job-3 | 3 | reddit | main | text_post |"), 1)

    def test_never_silently_overwrites_terminal_row_for_same_ledger_key(self):
        ledger = textwrap.dedent(
            """
            | job_id | attempt_no | platform | account_alias | content_type | decision | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            | job-9 | 4 | reddit | main | text_post | go | publish_ok | https://example.com/final | final | 2026-03-23T10:04:00Z |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        before = ledger_path.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            self.module.append_result_ledger(
                ledger_path,
                {
                    "job_id": "job-9",
                    "attempt_no": 4,
                    "platform": "reddit",
                    "account_alias": "main",
                    "content_type": "text_post",
                    "decision": "go",
                    "result_status": "publish_failed",
                    "evidence": "https://example.com/retry",
                    "notes": "retry",
                    "timestamp": "2026-03-23T10:05:00Z",
                },
            )

        self.assertEqual(ledger_path.read_text(encoding="utf-8"), before)

    def test_escapes_pipe_characters_inside_cells(self):
        ledger = textwrap.dedent(
            """
            | job_id | attempt_no | platform | account_alias | content_type | decision | result_status | evidence | notes | timestamp |
            | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(ledger)
            ledger_path = pathlib.Path(handle.name)

        self.module.append_result_ledger(
            ledger_path,
            {
                "job_id": "job-11",
                "attempt_no": 1,
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "decision": "go",
                "result_status": "publish_failed",
                "evidence": "failure | evidence: none",
                "notes": "reason | unsupported",
                "timestamp": "2026-03-24T03:40:00Z",
            },
        )

        updated = ledger_path.read_text(encoding="utf-8")
        self.assertIn("failure \\| evidence: none", updated)
        self.assertIn("reason \\| unsupported", updated)


if __name__ == "__main__":
    unittest.main()
