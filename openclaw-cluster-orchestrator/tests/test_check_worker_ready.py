from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from util import load_script_module


ACCOUNT_MATRIX_TEMPLATE = textwrap.dedent(
    """
    | account_alias | platform | display_name | browser_profile | default | notes |
    | --- | --- | --- | --- | --- | --- |
    {rows}
    """
).strip()


class CheckWorkerReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("check_worker_ready.py", "check_worker_ready")

    def test_reports_ready_when_probe_matches_expected_account(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            account_matrix = root / "worker-zhihu-01" / "matrix" / "account-matrix.md"
            account_matrix.parent.mkdir(parents=True, exist_ok=True)
            account_matrix.write_text(
                ACCOUNT_MATRIX_TEMPLATE.format(
                    rows="| main | zhihu | 嘤嘤嘤 | chrome-relay | yes | zhihu |"
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.check_worker_ready(
                node_runtime_root=root,
                node_id="worker-zhihu-01",
                platform="zhihu",
                account_alias="main",
                browser_probe_runner=lambda **_kwargs: {
                    "status": "ok",
                    "observed_account": "嘤嘤嘤",
                    "jump_target": "https://www.zhihu.com/",
                    "notes": "",
                },
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["reason"], "ready")
            self.assertEqual(result["expected_display_name"], "嘤嘤嘤")

    def test_reports_not_ready_when_probe_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            account_matrix = root / "worker-zhihu-01" / "matrix" / "account-matrix.md"
            account_matrix.parent.mkdir(parents=True, exist_ok=True)
            account_matrix.write_text(
                ACCOUNT_MATRIX_TEMPLATE.format(
                    rows="| main | zhihu | 嘤嘤嘤 | chrome-relay | yes | zhihu |"
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.check_worker_ready(
                node_runtime_root=root,
                node_id="worker-zhihu-01",
                platform="zhihu",
                account_alias="main",
                browser_probe_runner=lambda **_kwargs: {
                    "status": "probe_error",
                    "observed_account": "",
                    "jump_target": "",
                    "notes": "no attached tab",
                },
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "probe_error")
            self.assertIn("no attached tab", result["notes"])

    def test_reports_not_ready_when_observed_account_mismatches_expected_account(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            account_matrix = root / "worker-reddit-01" / "matrix" / "account-matrix.md"
            account_matrix.parent.mkdir(parents=True, exist_ok=True)
            account_matrix.write_text(
                ACCOUNT_MATRIX_TEMPLATE.format(
                    rows="| main | reddit | u/Fun_Supermarket9297 | chrome-relay | yes | reddit |"
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.module.check_worker_ready(
                node_runtime_root=root,
                node_id="worker-reddit-01",
                platform="reddit",
                account_alias="main",
                browser_probe_runner=lambda **_kwargs: {
                    "status": "ok",
                    "observed_account": "u/OtherUser",
                    "jump_target": "https://www.reddit.com/submit",
                    "notes": "",
                },
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "account_mismatch")
            self.assertEqual(result["observed_account"], "u/OtherUser")


if __name__ == "__main__":
    unittest.main()
