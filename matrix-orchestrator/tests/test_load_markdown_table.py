import importlib.util
import pathlib
import tempfile
import textwrap
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "load_markdown_table.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("load_markdown_table", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LoadMarkdownTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_script_module()

    def test_exports_loader_function(self):
        self.assertTrue(hasattr(self.module, "load_markdown_table"))

    def test_parses_first_table_header_and_rows_after_prose(self):
        markdown = textwrap.dedent(
            """
            # Matrix Notes

            This prose should be ignored.

            | platform | account_alias | notes |
            | --- | --- | --- |
            | xhs | main | ready |
            | wechat | backup | pending |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            file_path = pathlib.Path(handle.name)

        rows = self.module.load_markdown_table(file_path)

        self.assertEqual(
            rows,
            [
                {
                    "platform": "xhs",
                    "account_alias": "main",
                    "notes": "ready",
                },
                {
                    "platform": "wechat",
                    "account_alias": "backup",
                    "notes": "pending",
                },
            ],
        )

    def test_preserves_empty_string_cells(self):
        markdown = textwrap.dedent(
            """
            intro text

            | platform | account_alias | notes |
            | --- | --- | --- |
            | xhs | main | |
            | wechat | | pending |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            file_path = pathlib.Path(handle.name)

        rows = self.module.load_markdown_table(file_path)

        self.assertEqual(
            rows,
            [
                {
                    "platform": "xhs",
                    "account_alias": "main",
                    "notes": "",
                },
                {
                    "platform": "wechat",
                    "account_alias": "",
                    "notes": "pending",
                },
            ],
        )

    def test_parses_escaped_pipe_characters_inside_cells(self):
        markdown = textwrap.dedent(
            """
            | platform | account_alias | notes |
            | --- | --- | --- |
            | zhihu | main | failure \\| evidence: none |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            file_path = pathlib.Path(handle.name)

        rows = self.module.load_markdown_table(file_path)

        self.assertEqual(
            rows,
            [
                {
                    "platform": "zhihu",
                    "account_alias": "main",
                    "notes": "failure | evidence: none",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
