from __future__ import annotations

import pathlib
import sys
import unittest


TESTS_DIR = pathlib.Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from util import load_script_module


class ProbeBrowserIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("probe_browser_identity.py", "probe_browser_identity")

    def test_returns_expected_account_when_display_name_is_visible(self):
        result = self.module.probe_browser_identity(
            platform="zhihu",
            expected_display_name="嘤嘤嘤",
            browser_profile="chrome-relay",
            runner=lambda *_args, **_kwargs: {
                "url": "https://www.zhihu.com/",
                "title": "知乎 - 嘤嘤嘤",
                "text": "首页 嘤嘤嘤 创作 消息",
                "candidates": ["嘤嘤嘤", "创作"],
            },
        )

        self.assertEqual(result["observed_account"], "嘤嘤嘤")
        self.assertEqual(result["jump_target"], "https://www.zhihu.com/")
        self.assertEqual(result["status"], "ok")

    def test_detects_not_logged_in_from_login_url(self):
        result = self.module.probe_browser_identity(
            platform="zhihu",
            expected_display_name="嘤嘤嘤",
            browser_profile="chrome-relay",
            runner=lambda *_args, **_kwargs: {
                "url": "https://www.zhihu.com/signin?next=%2F",
                "title": "登录 - 知乎",
                "text": "登录 注册",
                "candidates": [],
            },
        )

        self.assertEqual(result["observed_account"], "not_logged_in")
        self.assertEqual(result["status"], "not_logged_in")

    def test_extracts_reddit_username_from_page_text(self):
        result = self.module.probe_browser_identity(
            platform="reddit",
            expected_display_name="u/Fun_Supermarket9297",
            browser_profile="chrome-relay",
            runner=lambda *_args, **_kwargs: {
                "url": "https://www.reddit.com/r/test/submit?type=TEXT",
                "title": "Create Post",
                "text": "Create Post draft by u/Fun_Supermarket9297 in r/test",
                "candidates": ["u/Fun_Supermarket9297", "r/test"],
            },
        )

        self.assertEqual(result["observed_account"], "u/Fun_Supermarket9297")
        self.assertEqual(result["status"], "ok")

    def test_returns_probe_error_without_blocking_identity_when_runner_fails(self):
        result = self.module.probe_browser_identity(
            platform="threads",
            expected_display_name="qiang8513",
            browser_profile="chrome-relay",
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no tab")),
        )

        self.assertEqual(result["status"], "probe_error")
        self.assertEqual(result["observed_account"], "")
        self.assertIn("no tab", result["notes"])


if __name__ == "__main__":
    unittest.main()
