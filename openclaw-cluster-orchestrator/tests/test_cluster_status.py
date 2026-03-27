from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from util import load_script_module


class ClusterStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_script_module("cluster_status.py", "cluster_status")

    def test_exports_cluster_status(self):
        self.assertTrue(hasattr(self.module, "cluster_status"))

    def test_cli_accepts_include_readiness_flag(self):
        args = self.module._build_arg_parser().parse_args(["--include-readiness"])
        self.assertTrue(args.include_readiness)

    def test_summarizes_cluster_queue_and_latest_result_and_node_queues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            cluster_dir = root / "cluster"
            nodes_dir = root / "nodes"
            cluster_dir.mkdir()
            (nodes_dir / "worker-zhihu-01" / "matrix").mkdir(parents=True)
            (nodes_dir / "worker-reddit-01" / "matrix").mkdir(parents=True)

            (cluster_dir / "cluster-job-queue.md").write_text(
                textwrap.dedent(
                    """
                    | job_id | attempt_no | job_type | platform | account_alias | content_type | preferred_node | payload_json | status | notes |
                    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
                    | cluster-job-0001 | 1 | publish | zhihu | main | idea | worker-zhihu-01 | {} | failed | runner_error |
                    | cluster-job-0002 | 1 | publish | reddit | main | text_post | worker-reddit-01 | {} | pending | queued |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-result-ledger.md").write_text(
                textwrap.dedent(
                    """
                    | job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |
                    | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
                    | cluster-job-0001 | 1 | worker-zhihu-01 | publisher-zhihu | publish | runner_error | none | relay missing | 2026-03-25T02:53:23Z |
                    | cluster-job-0002 | 1 | worker-reddit-01 | publisher-reddit | publish | publish_ok | https://example.com/post/2 | ok | 2026-03-25T03:00:00Z |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-run-log.md").write_text(
                textwrap.dedent(
                    """
                    | job_id | attempt_no | node_id | event | status | notes | timestamp |
                    | --- | ---: | --- | --- | --- | --- | --- |
                    | cluster-job-0002 | 1 | worker-reddit-01 | ledger_updated | publish_ok | ok | 2026-03-25T03:00:00Z |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (cluster_dir / "node-matrix.md").write_text(
                textwrap.dedent(
                    """
                    | node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |
                    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
                    | worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | zhihu |
                    | worker-reddit-01 | local_agent | publisher-reddit |  | reddit | main | chrome-relay | publish | ready | reddit |
                    | worker-fallback-01 | local_agent | publisher-fallback |  | zhihu,reddit |  | chrome-relay | publish | paused | fallback |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-zhihu-01" / "matrix" / "job-queue.md").write_text(
                textwrap.dedent(
                    """
                    | job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | status | notes |
                    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
                    | cluster-job-0001 | 1 | zhihu | main | idea | A | B |  | failed | runner_error |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-reddit-01" / "matrix" / "job-queue.md").write_text(
                textwrap.dedent(
                    """
                    | job_id | attempt_no | platform | account_alias | content_type | title | body | media_paths | status | notes |
                    | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
                    | cluster-job-0002 | 1 | reddit | main | text_post | A | B |  | done | publish_ok |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )

            summary = self.module.cluster_status(cluster_dir=cluster_dir, nodes_root=nodes_dir)

            self.assertEqual(summary["cluster_queue"]["total"], 2)
            self.assertEqual(summary["cluster_queue"]["by_status"]["failed"], 1)
            self.assertEqual(summary["cluster_queue"]["by_status"]["pending"], 1)
            self.assertEqual(summary["latest_result"]["job_id"], "cluster-job-0002")
            self.assertEqual(summary["latest_result"]["result_status"], "publish_ok")
            self.assertEqual(summary["nodes"]["worker-zhihu-01"]["queue"]["by_status"]["failed"], 1)
            self.assertEqual(summary["nodes"]["worker-reddit-01"]["queue"]["by_status"]["done"], 1)
            self.assertEqual(summary["nodes"]["worker-fallback-01"]["queue"]["total"], 0)
            self.assertEqual(summary["nodes"]["worker-fallback-01"]["agent_id"], "publisher-fallback")

    def test_json_safe_when_runtime_files_are_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            cluster_dir = root / "cluster"
            nodes_dir = root / "nodes"
            cluster_dir.mkdir()
            nodes_dir.mkdir()

            (cluster_dir / "cluster-job-queue.md").write_text(
                "| job_id | attempt_no | job_type | platform | account_alias | content_type | preferred_node | payload_json | status | notes |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-result-ledger.md").write_text(
                "| job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-run-log.md").write_text(
                "| job_id | attempt_no | node_id | event | status | notes | timestamp |\n| --- | ---: | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "node-matrix.md").write_text(
                "| node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | zhihu |\n",
                encoding="utf-8",
            )

            summary = self.module.cluster_status(cluster_dir=cluster_dir, nodes_root=nodes_dir)

            self.assertEqual(summary["cluster_queue"]["total"], 0)
            self.assertIsNone(summary["latest_result"])
            self.assertEqual(summary["nodes"]["worker-zhihu-01"]["queue"]["total"], 0)

    def test_does_not_probe_readiness_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            cluster_dir = root / "cluster"
            nodes_dir = root / "nodes"
            cluster_dir.mkdir()
            (nodes_dir / "worker-zhihu-01" / "matrix").mkdir(parents=True)

            (cluster_dir / "cluster-job-queue.md").write_text(
                "| job_id | attempt_no | job_type | platform | account_alias | content_type | preferred_node | payload_json | status | notes |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-result-ledger.md").write_text(
                "| job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "node-matrix.md").write_text(
                "| node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | zhihu |\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-zhihu-01" / "matrix" / "account-matrix.md").write_text(
                "| platform | account_alias | display_name | browser_profile |\n| --- | --- | --- | --- |\n| zhihu | main | Main Account | profile-1 |\n",
                encoding="utf-8",
            )

            calls: list[tuple[object, ...]] = []

            def fake_checker(**kwargs):
                calls.append(
                    (
                        kwargs["node_runtime_root"],
                        kwargs["node_id"],
                        kwargs["platform"],
                        kwargs["account_alias"],
                    )
                )
                return {"ok": True, "reason": "ready"}

            summary = self.module.cluster_status(
                cluster_dir=cluster_dir,
                nodes_root=nodes_dir,
                worker_ready_checker=fake_checker,
            )

            self.assertNotIn("readiness", summary["nodes"]["worker-zhihu-01"])
            self.assertEqual(calls, [])

    def test_includes_readiness_for_ready_and_blocked_nodes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            cluster_dir = root / "cluster"
            nodes_dir = root / "nodes"
            cluster_dir.mkdir()
            (nodes_dir / "worker-zhihu-01" / "matrix").mkdir(parents=True)
            (nodes_dir / "worker-reddit-01" / "matrix").mkdir(parents=True)
            (nodes_dir / "worker-fallback-01" / "matrix").mkdir(parents=True)

            (cluster_dir / "cluster-job-queue.md").write_text(
                "| job_id | attempt_no | job_type | platform | account_alias | content_type | preferred_node | payload_json | status | notes |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-result-ledger.md").write_text(
                "| job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "node-matrix.md").write_text(
                textwrap.dedent(
                    """
                    | node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |
                    | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
                    | worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | zhihu |
                    | worker-reddit-01 | local_agent | publisher-reddit |  | reddit | main | chrome-relay | publish | ready | reddit |
                    | worker-fallback-01 | local_agent | publisher-fallback |  | zhihu,reddit |  | chrome-relay | publish | paused | fallback |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-zhihu-01" / "matrix" / "account-matrix.md").write_text(
                textwrap.dedent(
                    """
                    | platform | account_alias | display_name | browser_profile |
                    | --- | --- | --- | --- |
                    | zhihu | main | Main Zhihu | profile-zhihu |
                    | zhihu | alt | Alt Zhihu | profile-zhihu-alt |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-reddit-01" / "matrix" / "account-matrix.md").write_text(
                textwrap.dedent(
                    """
                    | platform | account_alias | display_name | browser_profile |
                    | --- | --- | --- | --- |
                    | reddit | main | Main Reddit | profile-reddit |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )
            (nodes_dir / "worker-fallback-01" / "matrix" / "account-matrix.md").write_text(
                textwrap.dedent(
                    """
                    | platform | account_alias | display_name | browser_profile |
                    | --- | --- | --- | --- |
                    """
                ).strip() + "\n",
                encoding="utf-8",
            )

            calls: list[dict[str, object]] = []

            def fake_checker(**kwargs):
                calls.append(kwargs)
                platform = kwargs["platform"]
                account_alias = kwargs["account_alias"]
                if platform == "zhihu" and account_alias == "main":
                    return {"ok": True, "reason": "ready"}
                if platform == "zhihu" and account_alias == "alt":
                    return {"ok": False, "reason": "browser_profile_mismatch"}
                if platform == "reddit":
                    return {"ok": True, "reason": "ready"}
                return {"ok": False, "reason": "unexpected"}

            summary = self.module.cluster_status(
                cluster_dir=cluster_dir,
                nodes_root=nodes_dir,
                include_readiness=True,
                worker_ready_checker=fake_checker,
            )

            self.assertEqual(
                calls,
                [
                    {
                        "node_runtime_root": nodes_dir,
                        "node_id": "worker-zhihu-01",
                        "platform": "zhihu",
                        "account_alias": "main",
                    },
                    {
                        "node_runtime_root": nodes_dir,
                        "node_id": "worker-zhihu-01",
                        "platform": "zhihu",
                        "account_alias": "alt",
                    },
                    {
                        "node_runtime_root": nodes_dir,
                        "node_id": "worker-reddit-01",
                        "platform": "reddit",
                        "account_alias": "main",
                    },
                ],
            )
            self.assertEqual(summary["nodes"]["worker-zhihu-01"]["readiness"], {
                "ok": False,
                "reason": "degraded",
                "checks": [
                    {"platform": "zhihu", "account_alias": "main", "ok": True, "reason": "ready"},
                    {
                        "platform": "zhihu",
                        "account_alias": "alt",
                        "ok": False,
                        "reason": "browser_profile_mismatch",
                    },
                ],
            })
            self.assertEqual(summary["nodes"]["worker-reddit-01"]["readiness"], {
                "ok": True,
                "reason": "ready",
                "checks": [
                    {"platform": "reddit", "account_alias": "main", "ok": True, "reason": "ready"}
                ],
            })
            self.assertEqual(summary["nodes"]["worker-fallback-01"]["readiness"], {
                "ok": False,
                "reason": "node_paused",
                "checks": [],
            })

    def test_reports_missing_account_matrix_as_not_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            cluster_dir = root / "cluster"
            nodes_dir = root / "nodes"
            cluster_dir.mkdir()
            (nodes_dir / "worker-zhihu-01" / "matrix").mkdir(parents=True)

            (cluster_dir / "cluster-job-queue.md").write_text(
                "| job_id | attempt_no | job_type | platform | account_alias | content_type | preferred_node | payload_json | status | notes |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "cluster-result-ledger.md").write_text(
                "| job_id | attempt_no | node_id | agent_id | job_type | result_status | evidence | notes | timestamp |\n| --- | ---: | --- | --- | --- | --- | --- | --- | --- |\n",
                encoding="utf-8",
            )
            (cluster_dir / "node-matrix.md").write_text(
                "| node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | zhihu |\n",
                encoding="utf-8",
            )

            calls: list[dict[str, object]] = []

            def fake_checker(**kwargs):
                calls.append(kwargs)
                return {"ok": True, "reason": "ready"}

            summary = self.module.cluster_status(
                cluster_dir=cluster_dir,
                nodes_root=nodes_dir,
                include_readiness=True,
                worker_ready_checker=fake_checker,
            )

            self.assertEqual(calls, [])
            self.assertEqual(summary["nodes"]["worker-zhihu-01"]["readiness"], {
                "ok": False,
                "reason": "missing_account_matrix",
                "checks": [],
            })


if __name__ == "__main__":
    unittest.main()
