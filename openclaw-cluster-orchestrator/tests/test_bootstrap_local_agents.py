from __future__ import annotations

import json
from unittest import mock
import unittest

from util import load_script_module


class BootstrapLocalAgentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module(
            "bootstrap_local_agents.py",
            "bootstrap_local_agents",
        )

    def test_exports_bootstrap_local_agents(self):
        self.assertTrue(hasattr(self.module, "bootstrap_local_agents"))

    def test_creates_missing_local_agents_only(self):
        node_rows = [
            {
                "node_id": "worker-zhihu-01",
                "mode": "local_agent",
                "agent_id": "publisher-zhihu",
            },
            {
                "node_id": "worker-remote-01",
                "mode": "remote_gateway",
                "agent_id": "remote-worker",
            },
            {
                "node_id": "worker-reddit-01",
                "mode": "local_agent",
                "agent_id": "publisher-reddit",
            },
        ]

        list_stdout = json.dumps(
            [
                {
                    "id": "publisher-reddit",
                    "workspace": "/Users/openclawcn/.openclaw/workspace",
                }
            ],
            ensure_ascii=False,
        )

        run_calls: list[list[str]] = []

        def fake_run(command, **_kwargs):
            run_calls.append(command)
            if command[:3] == ["/tmp/openclaw", "agents", "list"]:
                return self.module.subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=list_stdout,
                    stderr="",
                )
            return self.module.subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout='{"agentId":"publisher-zhihu"}',
                stderr="",
            )

        with mock.patch.dict(
            self.module.os.environ,
            {"OPENCLAW_BIN": "/tmp/openclaw"},
            clear=False,
        ), mock.patch.object(self.module.subprocess, "run", side_effect=fake_run):
            result = self.module.bootstrap_local_agents(node_rows, workspace="/tmp/workspace")

        add_calls = [call for call in run_calls if call[:3] == ["/tmp/openclaw", "agents", "add"]]
        self.assertEqual(len(add_calls), 1)
        self.assertIn("publisher-zhihu", add_calls[0])
        self.assertEqual(result["created"], ["publisher-zhihu"])
        self.assertEqual(result["skipped_existing"], ["publisher-reddit"])
        self.assertEqual(result["ignored_non_local"], ["remote-worker"])

    def test_dry_run_does_not_create_agents(self):
        node_rows = [
            {
                "node_id": "worker-zhihu-01",
                "mode": "local_agent",
                "agent_id": "publisher-zhihu",
            }
        ]

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
                stdout="[]",
                stderr="",
            ),
        ) as run_mock:
            result = self.module.bootstrap_local_agents(
                node_rows,
                workspace="/tmp/workspace",
                dry_run=True,
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][:3], ["/tmp/openclaw", "agents", "list"])
        self.assertEqual(result["planned"], ["publisher-zhihu"])


if __name__ == "__main__":
    unittest.main()
