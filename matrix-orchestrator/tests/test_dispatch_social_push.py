from __future__ import annotations

import json
import pathlib
import sys
import unittest
from unittest import mock


TESTS_DIR = pathlib.Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from util import load_script_module


class DispatchSocialPushTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module(
            "dispatch_social_push.py", "dispatch_social_push"
        )

    def test_builds_normalized_payload_for_runner(self):
        captured: dict[str, object] = {}

        def fake_runner(payload):
            captured["payload"] = payload
            return {
                "ok": True,
                "result_status": "publish_ok",
                "evidence": "https://example.com/post/1",
                "notes": "ok",
            }

        result = self.module.dispatch_social_push(
            {
                "job_id": "job-1",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "article",
                "title": "Hello",
                "body": "Body",
                "media_paths": "",
                "notes": "n/a",
            },
            runner=fake_runner,
        )

        self.assertEqual(captured["payload"]["job_id"], "job-1")
        self.assertEqual(captured["payload"]["platform"], "zhihu")
        self.assertEqual(captured["payload"]["title"], "Hello")
        self.assertEqual(result["result_status"], "publish_ok")

    def test_returns_runner_error_when_no_runner_is_provided(self):
        result = self.module.dispatch_social_push(
            {
                "job_id": "job-2",
                "attempt_no": "1",
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "title": "Test",
                "body": "",
                "media_paths": "",
                "notes": "",
            }
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["result_status"], "runner_error")

    def test_maps_filtered_publish_result(self):
        def fake_runner(_payload):
            return {
                "ok": True,
                "result_status": "publish_filtered",
                "evidence": "filtered by subreddit",
                "notes": "removed by filter",
            }

        result = self.module.dispatch_social_push(
            {
                "job_id": "job-3",
                "attempt_no": "2",
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "image_post",
                "title": "photo",
                "body": "",
                "media_paths": "/tmp/a.jpg",
                "notes": "",
            },
            runner=fake_runner,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["result_status"], "publish_filtered")
        self.assertEqual(result["evidence"], "filtered by subreddit")

    def test_maps_runtime_exception_to_runner_error(self):
        def broken_runner(_payload):
            raise RuntimeError("boom")

        result = self.module.dispatch_social_push(
            {
                "job_id": "job-4",
                "attempt_no": "1",
                "platform": "reddit",
                "account_alias": "main",
                "content_type": "text_post",
                "title": "test",
                "body": "",
                "media_paths": "",
                "notes": "",
            },
            runner=broken_runner,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["result_status"], "runner_error")
        self.assertIn("boom", result["notes"])

    def test_preserves_optional_guard_fields_from_runner(self):
        def fake_runner(_payload):
            return {
                "ok": False,
                "result_status": "runner_error",
                "evidence": "redirected",
                "notes": "wrong account",
                "jump_target": "https://example.com/editor",
                "observed_account": "alt-account",
            }

        result = self.module.dispatch_social_push(
            {
                "job_id": "job-4b",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "title": "test",
                "body": "",
                "media_paths": "",
                "notes": "",
            },
            runner=fake_runner,
        )

        self.assertEqual(result["jump_target"], "https://example.com/editor")
        self.assertEqual(result["observed_account"], "alt-account")

    def test_build_prompt_requests_optional_guard_fields(self):
        prompt = self.module._build_prompt(
            {
                "job_id": "job-guard",
                "attempt_no": "1",
                "platform": "zhihu",
                "account_alias": "main",
                "content_type": "idea",
                "title": "Guard",
                "body": "Body",
                "media_paths": [],
                "notes": "",
            }
        )

        self.assertIn("jump_target", prompt)
        self.assertIn("observed_account", prompt)

    def test_default_runner_uses_gateway_mode_and_parses_nested_payload_json(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": json.dumps(
                                {
                                    "ok": True,
                                    "result_status": "publish_ok",
                                    "evidence": "https://example.com/post/42",
                                    "notes": "published",
                                },
                                ensure_ascii=False,
                            )
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ) as run_mock:
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-5",
                    "attempt_no": "1",
                    "platform": "zhihu",
                    "account_alias": "main",
                    "content_type": "article",
                    "title": "Matrix test",
                    "body": "Body",
                    "media_paths": "",
                    "notes": "",
                }
            )

        command = run_mock.call_args.args[0]
        self.assertNotIn("--local", command)
        self.assertEqual(result["result_status"], "publish_ok")
        self.assertEqual(result["evidence"], "https://example.com/post/42")
        self.assertEqual(result["notes"], "published")

    def test_default_runner_can_use_local_mode_and_detect_filtered_publish(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": "抱歉，Reddit 內容過濾器已移除此貼文。"
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "MATRIX_ORCHESTRATOR_OPENCLAW_MODE": "local",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ) as run_mock:
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-6",
                    "attempt_no": "1",
                    "platform": "reddit",
                    "account_alias": "main",
                    "content_type": "image_post",
                    "title": "Matrix test",
                    "body": "",
                    "media_paths": "/tmp/a.jpg",
                    "notes": "",
                }
            )

        command = run_mock.call_args.args[0]
        self.assertIn("--local", command)
        self.assertEqual(result["result_status"], "publish_filtered")
        self.assertIn("內容過濾器", result["evidence"])

    def test_plain_text_failure_with_filtered_no_maps_to_publish_failed(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": (
                                "failure | evidence: none | filtered: no | "
                                "reason: social-push does not support zhihu"
                            )
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ):
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-7",
                    "attempt_no": "1",
                    "platform": "zhihu",
                    "account_alias": "main",
                    "content_type": "idea",
                    "title": "Matrix test",
                    "body": "Body",
                    "media_paths": "",
                    "notes": "",
                }
            )

        self.assertEqual(result["result_status"], "publish_failed")
        self.assertIn("filtered: no", result["evidence"])

    def test_local_error_envelope_maps_to_runner_error(self):
        stdout = json.dumps(
            {
                "payloads": [{"text": "LLM request timed out."}],
                "meta": {"durationMs": 28241},
                "stopReason": "error",
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "MATRIX_ORCHESTRATOR_OPENCLAW_MODE": "local",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ):
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-8",
                    "attempt_no": "1",
                    "platform": "zhihu",
                    "account_alias": "main",
                    "content_type": "idea",
                    "title": "Matrix test",
                    "body": "Body",
                    "media_paths": "",
                    "notes": "",
                }
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["result_status"], "runner_error")
        self.assertIn("timed out", result["notes"])

    def test_default_runner_follows_tool_use_session_until_terminal_json_result(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": "我先按 social-push 的知乎想法流程走一遍。"
                        }
                    ],
                    "meta": {
                        "agentMeta": {
                            "sessionId": "session-123"
                        }
                    },
                    "stopReason": "toolUse",
                },
            },
            ensure_ascii=False,
        )

        final_text = json.dumps(
            {
                "ok": False,
                "result_status": "runner_error",
                "evidence": "redirected to signin",
                "notes": "Please log into Zhihu first.",
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ), mock.patch.object(
            self.module,
            "_wait_for_terminal_session_result",
            return_value={
                "stop_reason": "stop",
                "text": final_text,
            },
        ) as wait_mock:
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-9",
                    "attempt_no": "1",
                    "platform": "zhihu",
                    "account_alias": "main",
                    "content_type": "idea",
                    "title": "Matrix test",
                    "body": "Body",
                    "media_paths": "",
                    "notes": "",
                }
            )

        self.assertEqual(result["result_status"], "runner_error")
        self.assertIn("Please log into Zhihu first.", result["notes"])
        wait_mock.assert_called_once()

    def test_plain_text_commentary_without_terminal_success_markers_does_not_map_to_publish_ok(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": "我先按 social-push 的知乎想法流程走一遍，用 chrome-relay 复用登录态。"
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

        with mock.patch.dict(
            self.module.os.environ,
            {
                "MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER": "1",
                "OPENCLAW_BIN": "/tmp/openclaw",
            },
            clear=False,
        ), mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ):
            result = self.module.dispatch_social_push(
                {
                    "job_id": "job-10",
                    "attempt_no": "1",
                    "platform": "zhihu",
                    "account_alias": "main",
                    "content_type": "idea",
                    "title": "Matrix test",
                    "body": "Body",
                    "media_paths": "",
                    "notes": "",
                }
            )

        self.assertEqual(result["result_status"], "publish_failed")
