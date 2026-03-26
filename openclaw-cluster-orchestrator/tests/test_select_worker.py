from __future__ import annotations

import unittest

from util import load_script_module


class SelectWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("select_worker.py", "select_worker")

    def test_exports_select_worker(self):
        self.assertTrue(hasattr(self.module, "select_worker"))

    def test_selects_ready_worker_for_publish_job(self):
        node_rows = [
            {
                "node_id": "worker-a",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "paused",
            },
            {
                "node_id": "worker-b",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": ""}

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-b")

    def test_preferred_node_wins_when_eligible(self):
        node_rows = [
            {
                "node_id": "worker-main",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
            {
                "node_id": "worker-preferred",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {
            "job_type": "publish",
            "platform": "zhihu",
            "account_alias": "",
            "preferred_node": "worker-preferred",
        }

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-preferred")

    def test_raises_when_no_ready_worker(self):
        node_rows = [
            {
                "node_id": "worker-a",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "offline",
            }
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": ""}

        with self.assertRaisesRegex(ValueError, "no_ready_worker"):
            self.module.select_worker(node_rows, job)

    def test_requires_capability_match(self):
        node_rows = [
            {
                "node_id": "worker-a",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "collect_metrics",
                "status": "ready",
            }
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        with self.assertRaisesRegex(ValueError, "no_ready_worker"):
            self.module.select_worker(node_rows, job)

    def test_requires_platform_match(self):
        node_rows = [
            {
                "node_id": "worker-a",
                "platforms": "reddit",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            }
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        with self.assertRaisesRegex(ValueError, "no_ready_worker"):
            self.module.select_worker(node_rows, job)

    def test_exact_account_alias_beats_generic_platform_match(self):
        node_rows = [
            {
                "node_id": "worker-generic",
                "platforms": "zhihu,reddit",
                "account_aliases": "",
                "capabilities": "publish",
                "status": "ready",
            },
            {
                "node_id": "worker-main",
                "platforms": "zhihu,reddit",
                "account_aliases": "main,alt",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-main")

    def test_platform_exclusive_beats_fallback_when_otherwise_equal(self):
        node_rows = [
            {
                "node_id": "worker-fallback",
                "platforms": "zhihu,reddit",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
            {
                "node_id": "worker-zhihu-only",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-zhihu-only")

    def test_keeps_first_matching_worker_for_stable_tie_break(self):
        node_rows = [
            {
                "node_id": "worker-first",
                "platforms": "zhihu,reddit",
                "account_aliases": "",
                "capabilities": "publish",
                "status": "ready",
            },
            {
                "node_id": "worker-second",
                "platforms": "zhihu,reddit",
                "account_aliases": "",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": ""}

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-first")

    def test_raises_when_only_remote_gateway_workers_available(self):
        node_rows = [
            {
                "node_id": "worker-gateway",
                "mode": "remote_gateway",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            }
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        with self.assertRaisesRegex(ValueError, "no_ready_worker"):
            self.module.select_worker(node_rows, job)

    def test_local_workers_preferred_over_remote_gateway(self):
        node_rows = [
            {
                "node_id": "worker-gateway",
                "mode": "remote_gateway",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
            {
                "node_id": "worker-local",
                "mode": "local_agent",
                "platforms": "zhihu",
                "account_aliases": "main",
                "capabilities": "publish",
                "status": "ready",
            },
        ]
        job = {"job_type": "publish", "platform": "zhihu", "account_alias": "main"}

        selected = self.module.select_worker(node_rows, job)
        self.assertEqual(selected["node_id"], "worker-local")


if __name__ == "__main__":
    unittest.main()
