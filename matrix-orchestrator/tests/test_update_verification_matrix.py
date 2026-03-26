import importlib.util
import pathlib
import tempfile
import textwrap
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "update_verification_matrix.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "update_verification_matrix",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpdateVerificationMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_script_module()

    def test_updates_existing_row_by_platform_alias_content_type_key(self):
        matrix = textwrap.dedent(
            """
            # Verification Matrix (Runtime)

            | platform | account_alias | content_type | status | last_verified | evidence | notes |
            |---|---|---|---|---|---|---|
            | reddit | main | text_post | workflow_only | 2026-03-20 | old evidence | old notes |
            | reddit | alt | text_post | page_verified | 2026-03-21 | keep this | keep this |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(matrix)
            matrix_path = pathlib.Path(handle.name)

        self.module.update_verification_matrix(
            matrix_path,
            {
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "status": "real_publish_ok",
                "last_verified": "2026-03-23",
                "evidence": "https://example.com/post/1",
                "notes": "real publish confirmed",
            },
        )

        updated = matrix_path.read_text(encoding="utf-8")
        self.assertEqual(updated.count("| reddit | main | text_post |"), 1)
        self.assertIn(
            "| reddit | main | text_post | real_publish_ok | 2026-03-23 | https://example.com/post/1 | real publish confirmed |",
            updated,
        )
        self.assertIn(
            "| reddit | alt | text_post | page_verified | 2026-03-21 | keep this | keep this |",
            updated,
        )

    def test_appends_new_row_when_key_is_missing(self):
        matrix = textwrap.dedent(
            """
            | platform | account_alias | content_type | status | last_verified | evidence | notes |
            | --- | --- | --- | --- | --- | --- | --- |
            | zhihu | main | article | real_publish_ok | 2026-03-22 | https://example.com/zhihu | confirmed |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(matrix)
            matrix_path = pathlib.Path(handle.name)

        self.module.update_verification_matrix(
            matrix_path,
            {
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "image_post",
                "status": "submit_ok_filtered",
                "last_verified": "2026-03-23",
                "evidence": "request: 200",
                "notes": "removed by filter",
            },
        )

        updated = matrix_path.read_text(encoding="utf-8")
        self.assertIn(
            "| reddit | main | image_post | submit_ok_filtered | 2026-03-23 | request: 200 | removed by filter |",
            updated,
        )
        self.assertEqual(updated.count("| reddit | main | image_post |"), 1)

    def test_rejects_status_outside_allowed_vocabulary(self):
        matrix = textwrap.dedent(
            """
            | platform | account_alias | content_type | status | last_verified | evidence | notes |
            | --- | --- | --- | --- | --- | --- | --- |
            | x | main | short_post | workflow_only | 2026-03-20 | init | init |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(matrix)
            matrix_path = pathlib.Path(handle.name)

        before = matrix_path.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            self.module.update_verification_matrix(
                matrix_path,
                {
                    "platform": "x",
                    "account_alias": "main",
                    "content_type": "short_post",
                    "status": "published",
                    "last_verified": "2026-03-23",
                    "evidence": "url",
                    "notes": "bad status",
                },
            )

        self.assertEqual(matrix_path.read_text(encoding="utf-8"), before)
        self.assertEqual(
            self.module.ALLOWED_STATUSES,
            {
                "workflow_only",
                "page_verified",
                "submit_ok",
                "real_publish_ok",
                "submit_ok_filtered",
            },
        )

    def test_escapes_pipe_characters_when_updating_cells(self):
        matrix = textwrap.dedent(
            """
            | platform | account_alias | content_type | status | last_verified | evidence | notes |
            | --- | --- | --- | --- | --- | --- | --- |
            | zhihu | main | idea | real_publish_ok | 2026-03-23 | old evidence | old notes |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(matrix)
            matrix_path = pathlib.Path(handle.name)

        self.module.update_verification_matrix(
            matrix_path,
            {
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "status": "submit_ok_filtered",
                "last_verified": "2026-03-24",
                "evidence": "failure | evidence: none",
                "notes": "reason | unsupported",
            },
        )

        updated = matrix_path.read_text(encoding="utf-8")
        self.assertIn("failure \\| evidence: none", updated)
        self.assertIn("reason \\| unsupported", updated)
