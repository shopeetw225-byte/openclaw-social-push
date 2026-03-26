import importlib.util
import pathlib
import tempfile
import textwrap
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "append_run_log.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("append_run_log", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AppendRunLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_script_module()

    def test_exports_append_run_log(self):
        self.assertTrue(hasattr(self.module, "append_run_log"))

    def test_appends_one_run_log_row_per_event_and_preserves_existing_rows(self):
        run_log = textwrap.dedent(
            """
            # Run Log (Runtime)

            | job_id | attempt_no | event | status | notes | timestamp |
            | --- | --- | --- | --- | --- | --- |
            | job-1 | 1 | queue | queued | waiting | 2026-03-23T11:00:00Z |
            """
        ).strip()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(run_log)
            log_path = pathlib.Path(handle.name)

        self.module.append_run_log(
            log_path,
            {
                "job_id": "job-1",
                "attempt_no": 1,
                "event": "dispatch",
                "status": "running",
                "notes": "started",
                "timestamp": "2026-03-23T11:01:00Z",
            },
        )

        content = log_path.read_text(encoding="utf-8")
        self.assertIn(
            "| job-1 | 1 | queue | queued | waiting | 2026-03-23T11:00:00Z |",
            content,
        )
        self.assertIn(
            "| job-1 | 1 | dispatch | running | started | 2026-03-23T11:01:00Z |",
            content,
        )

    def test_uses_stable_columns_when_creating_new_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "run_log.md"

            self.module.append_run_log(
                log_path,
                {
                    "job_id": "job-7",
                    "attempt_no": 3,
                    "event": "complete",
                    "status": "success",
                    "notes": "done",
                    "timestamp": "2026-03-23T11:02:00Z",
                },
            )

            self.assertEqual(
                log_path.read_text(encoding="utf-8"),
                "\n".join(
                    [
                        "| job_id | attempt_no | event | status | notes | timestamp |",
                        "| --- | --- | --- | --- | --- | --- |",
                        "| job-7 | 3 | complete | success | done | 2026-03-23T11:02:00Z |",
                    ]
                )
                + "\n",
            )

    def test_appends_one_row_each_call_for_multiple_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = pathlib.Path(tmpdir) / "run_log.md"

            self.module.append_run_log(
                log_path,
                {
                    "job_id": "job-8",
                    "attempt_no": 1,
                    "event": "queue",
                    "status": "queued",
                    "notes": "n/a",
                    "timestamp": "2026-03-23T11:03:00Z",
                },
            )
            self.module.append_run_log(
                log_path,
                {
                    "job_id": "job-8",
                    "attempt_no": 1,
                    "event": "retry",
                    "status": "running",
                    "notes": "retrying",
                    "timestamp": "2026-03-23T11:04:00Z",
                },
            )

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(
                lines[-1],
                "| job-8 | 1 | retry | running | retrying | 2026-03-23T11:04:00Z |",
            )
