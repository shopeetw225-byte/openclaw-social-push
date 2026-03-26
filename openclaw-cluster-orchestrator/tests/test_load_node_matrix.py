from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from util import load_script_module


class LoadNodeMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("load_node_matrix.py", "load_node_matrix")

    def test_exports_load_node_matrix(self):
        self.assertTrue(hasattr(self.module, "load_node_matrix"))

    def test_parses_escaped_pipe_and_required_columns(self):
        markdown = textwrap.dedent(
            """
            # Node Matrix

            | node_id | mode | agent_id | platforms | account_aliases | capabilities | status | notes |
            | --- | --- | --- | --- | --- | --- | --- | --- |
            | worker-zhihu-01 | local_agent | openai/worker-zhihu | zhihu | main | publish | ready | supports evidence \\| logs |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            matrix_path = pathlib.Path(handle.name)

        rows = self.module.load_node_matrix(matrix_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["notes"], "supports evidence | logs")

    def test_raises_for_missing_required_columns(self):
        markdown = textwrap.dedent(
            """
            | node_id | agent_id | platforms | capabilities | status |
            | --- | --- | --- | --- | --- |
            | worker-zhihu-01 | openai/worker-zhihu | zhihu | publish | ready |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            matrix_path = pathlib.Path(handle.name)

        with self.assertRaisesRegex(ValueError, "missing_required_columns"):
            self.module.load_node_matrix(matrix_path)

    def test_normalizes_rows(self):
        markdown = textwrap.dedent(
            """
            | node_id | mode | agent_id | platforms | account_aliases | capabilities | status | notes |
            | --- | --- | --- | --- | --- | --- | --- | --- |
            | worker-mixed-01 | local_agent | openai/worker-mixed | zhihu, reddit | main, alt | publish, collect_metrics | READY |  has spaces  |
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            matrix_path = pathlib.Path(handle.name)

        rows = self.module.load_node_matrix(matrix_path)

        self.assertEqual(
            rows[0],
            {
                "node_id": "worker-mixed-01",
                "mode": "local_agent",
                "agent_id": "openai/worker-mixed",
                "platforms": "zhihu,reddit",
                "account_aliases": "main,alt",
                "capabilities": "publish,collect_metrics",
                "status": "ready",
                "notes": "has spaces",
            },
        )

    def test_returns_empty_for_no_markdown_table(self):
        markdown = textwrap.dedent(
            """
            # Empty

            no pipe table here
            """
        ).strip()

        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(markdown)
            matrix_path = pathlib.Path(handle.name)

        rows = self.module.load_node_matrix(matrix_path)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
