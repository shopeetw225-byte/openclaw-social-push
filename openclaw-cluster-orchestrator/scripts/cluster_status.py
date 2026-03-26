from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import split_markdown_row


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


def cluster_status(*, cluster_dir: str | Path = "docs/cluster", nodes_root: str | Path = "docs/nodes") -> dict[str, Any]:
    cluster_path = Path(cluster_dir)
    nodes_path = Path(nodes_root)

    queue_rows = _load_table(cluster_path / "cluster-job-queue.md")
    ledger_rows = _load_table(cluster_path / "cluster-result-ledger.md")
    node_rows = _load_table(cluster_path / "node-matrix.md")

    nodes: dict[str, Any] = {}
    for node_row in node_rows:
        node_id = node_row.get("node_id", "").strip()
        if not node_id:
            continue
        queue_rows_local = _load_table(nodes_path / node_id / "matrix" / "job-queue.md")
        nodes[node_id] = {
            "agent_id": node_row.get("agent_id", "").strip(),
            "status": node_row.get("status", "").strip(),
            "queue": {
                "total": len(queue_rows_local),
                "by_status": _count_by_status(queue_rows_local),
            },
        }

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
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    print(json.dumps(cluster_status(cluster_dir=args.cluster_dir, nodes_root=args.nodes_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
