from __future__ import annotations

import json
from unittest import mock
import unittest

from util import load_script_module


class DispatchToWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("dispatch_to_worker.py", "dispatch_to_worker")

    def test_exports_dispatch_to_worker(self):
        self.assertTrue(hasattr(self.module, "dispatch_to_worker"))

    def test_gateway_runner_builds_expected_command(self):
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

        node = {
            "node_id": "worker-zhihu-01",
            "agent_id": "publisher-zhihu",
        }
        payload = {
            "job_id": "cluster-job-1",
            "attempt_no": "1",
            "node_id": "worker-zhihu-01",
            "job_type": "publish",
            "platform": "zhihu",
            "account_alias": "main",
            "content_type": "idea",
            "title": "Hello",
            "body": "Body",
            "media_paths": [],
            "cluster_notes": "",
        }

        with mock.patch.dict(
            self.module.os.environ,
            {"OPENCLAW_BIN": "/tmp/openclaw"},
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
            result = self.module.dispatch_to_worker(node, payload)

        command = run_mock.call_args.args[0]
        self.assertEqual(command[:5], ["/tmp/openclaw", "agent", "--json", "--agent", "publisher-zhihu"])
        prompt = command[-1]
        self.assertIn("/matrix-orchestrator/scripts/run_next_job.py", prompt)
        self.assertIn("MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1 python3", prompt)
        self.assertIn("/docs/nodes/worker-zhihu-01/matrix/job-queue.md", prompt)
        self.assertIn("/docs/nodes/worker-zhihu-01/matrix/account-matrix.md", prompt)
        self.assertIn("/docs/ops/content-assignment-ledger.md", prompt)
        self.assertIn("/docs/ops/conflict-ledger.md", prompt)
        self.assertIn("/docs/ops/operator-override-ledger.md", prompt)
        self.assertNotIn("/docs/matrix/job-queue.md", prompt)
        self.assertEqual(result["result_status"], "publish_ok")
        self.assertEqual(result["evidence"], "https://example.com/post/42")

    def test_follows_tool_use_until_terminal_session_result(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [{"text": "Routing to worker runtime now."}],
                    "meta": {"agentMeta": {"sessionId": "session-123"}},
                    "stopReason": "toolUse",
                },
            },
            ensure_ascii=False,
        )

        final_text = json.dumps(
            {
                "ok": False,
                "result_status": "runner_error",
                "evidence": "signin redirect",
                "notes": "Please log in first.",
            },
            ensure_ascii=False,
        )

        node = {"node_id": "worker-zhihu-01", "agent_id": "publisher-zhihu"}
        payload = {
            "job_id": "cluster-job-2",
            "attempt_no": "1",
            "node_id": "worker-zhihu-01",
            "job_type": "publish",
            "platform": "zhihu",
            "account_alias": "main",
            "content_type": "idea",
            "title": "Hello",
            "body": "Body",
            "media_paths": [],
            "cluster_notes": "",
        }

        with mock.patch.object(
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
            return_value={"stop_reason": "stop", "text": final_text},
        ) as wait_mock:
            result = self.module.dispatch_to_worker(node, payload)

        self.assertEqual(result["result_status"], "runner_error")
        wait_mock.assert_called_once()

    def test_wait_for_terminal_session_uses_node_agent(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [{"text": "Routing to worker runtime now."}],
                    "meta": {"agentMeta": {"sessionId": "session-456"}},
                    "stopReason": "toolUse",
                },
            },
            ensure_ascii=False,
        )

        terminal_text = json.dumps(
            {
                "ok": True,
                "result_status": "publish_ok",
                "evidence": "https://example.com/post/99",
                "notes": "toolUse finished",
            },
            ensure_ascii=False,
        )

        node = {"node_id": "worker-zhihu-01", "agent_id": "publisher-zhihu"}
        payload = {"job_id": "cluster-job-5"}

        with mock.patch.object(
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
            return_value={"stop_reason": "stop", "text": terminal_text},
        ) as wait_mock:
            result = self.module.dispatch_to_worker(node, payload)

        self.assertEqual(result["result_status"], "publish_ok")
        self.assertEqual(wait_mock.call_args.kwargs["agent_id"], "publisher-zhihu")

    def test_maps_subprocess_failure_to_dispatch_error(self):
        node = {"node_id": "worker-zhihu-01", "agent_id": "publisher-zhihu"}
        payload = {"job_id": "cluster-job-3"}

        with mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="gateway down",
            ),
        ):
            result = self.module.dispatch_to_worker(node, payload)

        self.assertFalse(result["ok"])
        self.assertEqual(result["result_status"], "dispatch_error")
        self.assertIn("gateway down", result["notes"])

    def test_plain_commentary_is_not_treated_as_publish_ok(self):
        stdout = json.dumps(
            {
                "status": "ok",
                "result": {
                    "payloads": [
                        {
                            "text": "I will now run the worker's node-local matrix-orchestrator."
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

        node = {"node_id": "worker-zhihu-01", "agent_id": "publisher-zhihu"}
        payload = {"job_id": "cluster-job-4"}

        with mock.patch.object(
            self.module.subprocess,
            "run",
            return_value=self.module.subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=stdout,
                stderr="",
            ),
        ):
            result = self.module.dispatch_to_worker(node, payload)

        self.assertEqual(result["result_status"], "runner_error")


if __name__ == "__main__":
    unittest.main()
