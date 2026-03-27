from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import split_markdown_row
from check_worker_ready import check_worker_ready as _default_worker_ready_checker


def _load_table(path: str | Path) -> list[dict[str, str]]:
    table_path = Path(path)
    if not table_path.exists():
        return []
    lines = table_path.read_text(encoding="utf-8").splitlines()
    table_header_index = -1
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and "|" in lines[idx + 1]:
            table_header_index = idx
            break
    if table_header_index == -1:
        return []
    headers = split_markdown_row(lines[table_header_index])
    rows: list[dict[str, str]] = []
    for line in lines[table_header_index + 2 :]:
        if "|" not in line:
            break
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append({header: cells[i] for i, header in enumerate(headers)})
    return rows


def _count_by_status(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "").strip()
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _node_readiness_from_status(status: str) -> dict[str, Any]:
    return {"ok": False, "reason": f"node_{status}", "checks": []}


def _node_readiness_from_account_matrix(
    *,
    node_runtime_root: Path,
    node_id: str,
    account_rows: list[dict[str, str]],
    worker_ready_checker: Callable[..., dict[str, object]],
) -> dict[str, Any]:
    if not account_rows:
        return {"ok": False, "reason": "missing_account_matrix", "checks": []}

    checks: list[dict[str, Any]] = []
    all_ok = True
    for account_row in account_rows:
        platform = account_row.get("platform", "").strip()
        account_alias = account_row.get("account_alias", "").strip()
        probe = worker_ready_checker(
            node_runtime_root=node_runtime_root,
            node_id=node_id,
            platform=platform,
            account_alias=account_alias,
        )
        check = {
            "platform": platform,
            "account_alias": account_alias,
            "ok": bool(probe.get("ok", False)),
            "reason": str(probe.get("reason", "")).strip() or "unknown",
        }
        all_ok = all_ok and check["ok"]
        checks.append(check)

    return {
        "ok": all_ok,
        "reason": "ready" if all_ok else "degraded",
        "checks": checks,
    }


def cluster_status(
    *,
    cluster_dir: str | Path = "docs/cluster",
    nodes_root: str | Path = "docs/nodes",
    include_readiness: bool = False,
    worker_ready_checker: Callable[..., dict[str, object]] | None = None,
) -> dict[str, Any]:
    cluster_path = Path(cluster_dir)
    nodes_path = Path(nodes_root)
    active_worker_ready_checker = worker_ready_checker or _default_worker_ready_checker

    queue_rows = _load_table(cluster_path / "cluster-job-queue.md")
    ledger_rows = _load_table(cluster_path / "cluster-result-ledger.md")
    node_rows = _load_table(cluster_path / "node-matrix.md")

    nodes: dict[str, Any] = {}
    for node_row in node_rows:
        node_id = node_row.get("node_id", "").strip()
        if not node_id:
            continue
        queue_rows_local = _load_table(nodes_path / node_id / "matrix" / "job-queue.md")
        node_summary: dict[str, Any] = {
            "agent_id": node_row.get("agent_id", "").strip(),
            "status": node_row.get("status", "").strip(),
            "queue": {
                "total": len(queue_rows_local),
                "by_status": _count_by_status(queue_rows_local),
            },
        }
        if include_readiness:
            node_status = node_summary["status"]
            if node_status != "ready":
                node_summary["readiness"] = _node_readiness_from_status(node_status)
            else:
                account_matrix_path = nodes_path / node_id / "matrix" / "account-matrix.md"
                account_rows = _load_table(account_matrix_path)
                node_summary["readiness"] = _node_readiness_from_account_matrix(
                    node_runtime_root=nodes_path,
                    node_id=node_id,
                    account_rows=account_rows,
                    worker_ready_checker=active_worker_ready_checker,
                )
        nodes[node_id] = node_summary

    return {
        "cluster_queue": {
            "total": len(queue_rows),
            "by_status": _count_by_status(queue_rows),
        },
        "latest_result": ledger_rows[-1] if ledger_rows else None,
        "nodes": nodes,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show a JSON summary of cluster runtime state.")
    parser.add_argument("--cluster-dir", default="docs/cluster")
    parser.add_argument("--nodes-root", default="docs/nodes")
    parser.add_argument("--include-readiness", action="store_true")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    print(
        json.dumps(
            cluster_status(
                cluster_dir=args.cluster_dir,
                nodes_root=args.nodes_root,
                include_readiness=args.include_readiness,
            ),
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
