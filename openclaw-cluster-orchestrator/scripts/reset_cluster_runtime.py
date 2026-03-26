from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _is_separator_row(line: str) -> bool:
    return bool(_SEPARATOR_RE.match(line))


def _clear_first_markdown_table_rows(text: str) -> tuple[str, int, bool]:
    lines = text.splitlines()
    header_index = -1
    for idx in range(len(lines) - 1):
        if "|" not in lines[idx]:
            continue
        if not _is_separator_row(lines[idx + 1]):
            continue
        header_index = idx
        break
    if header_index == -1:
        raise ValueError("Runtime file must include a markdown table.")

    rows_start = header_index + 2
    rows_end = rows_start
    while rows_end < len(lines) and "|" in lines[rows_end]:
        rows_end += 1

    removed = rows_end - rows_start
    if removed == 0:
        return text, 0, False

    cleaned_lines = lines[:rows_start] + lines[rows_end:]
    cleaned_text = "\n".join(cleaned_lines) + "\n"
    return cleaned_text, removed, True


def _collect_targets(
    *,
    cluster_queue_path: str | Path,
    cluster_run_log_path: str | Path,
    cluster_result_ledger_path: str | Path,
    node_runtime_root: str | Path,
    ops_assignment_ledger_path: str | Path,
    ops_conflict_ledger_path: str | Path,
    ops_override_ledger_path: str | Path,
) -> list[Path]:
    targets = [
        Path(cluster_queue_path),
        Path(cluster_run_log_path),
        Path(cluster_result_ledger_path),
        Path(ops_assignment_ledger_path),
        Path(ops_conflict_ledger_path),
        Path(ops_override_ledger_path),
    ]
    node_root = Path(node_runtime_root)
    if node_root.exists():
        for node_dir in sorted(node_root.iterdir(), key=lambda item: item.name):
            if not node_dir.is_dir():
                continue
            matrix_dir = node_dir / "matrix"
            for runtime_name in ("job-queue.md", "run-log.md", "result-ledger.md"):
                runtime_path = matrix_dir / runtime_name
                if runtime_path.exists():
                    targets.append(runtime_path)
    return targets


def reset_cluster_runtime(
    *,
    cluster_queue_path: str | Path = "docs/cluster/cluster-job-queue.md",
    cluster_run_log_path: str | Path = "docs/cluster/cluster-run-log.md",
    cluster_result_ledger_path: str | Path = "docs/cluster/cluster-result-ledger.md",
    node_runtime_root: str | Path = "docs/nodes",
    ops_assignment_ledger_path: str | Path = "docs/ops/content-assignment-ledger.md",
    ops_conflict_ledger_path: str | Path = "docs/ops/conflict-ledger.md",
    ops_override_ledger_path: str | Path = "docs/ops/operator-override-ledger.md",
    dry_run: bool = False,
) -> dict[str, object]:
    targets = _collect_targets(
        cluster_queue_path=cluster_queue_path,
        cluster_run_log_path=cluster_run_log_path,
        cluster_result_ledger_path=cluster_result_ledger_path,
        node_runtime_root=node_runtime_root,
        ops_assignment_ledger_path=ops_assignment_ledger_path,
        ops_conflict_ledger_path=ops_conflict_ledger_path,
        ops_override_ledger_path=ops_override_ledger_path,
    )
    rows_removed = 0
    files_modified = 0

    for target in targets:
        if not target.exists():
            continue
        original_text = target.read_text(encoding="utf-8")
        cleaned_text, removed, changed = _clear_first_markdown_table_rows(original_text)
        rows_removed += removed
        if not dry_run and changed:
            target.write_text(cleaned_text, encoding="utf-8")
            files_modified += 1

    return {
        "dry_run": dry_run,
        "targets": [str(path) for path in targets],
        "rows_removed": rows_removed,
        "files_modified": files_modified,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reset cluster runtime queue/log/ledger files to table headers only.")
    parser.add_argument("--cluster-queue", default="docs/cluster/cluster-job-queue.md")
    parser.add_argument("--cluster-run-log", default="docs/cluster/cluster-run-log.md")
    parser.add_argument("--cluster-result-ledger", default="docs/cluster/cluster-result-ledger.md")
    parser.add_argument("--node-runtime-root", default="docs/nodes")
    parser.add_argument("--ops-assignment-ledger", default="docs/ops/content-assignment-ledger.md")
    parser.add_argument("--ops-conflict-ledger", default="docs/ops/conflict-ledger.md")
    parser.add_argument("--ops-override-ledger", default="docs/ops/operator-override-ledger.md")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    result = reset_cluster_runtime(
        cluster_queue_path=args.cluster_queue,
        cluster_run_log_path=args.cluster_run_log,
        cluster_result_ledger_path=args.cluster_result_ledger,
        node_runtime_root=args.node_runtime_root,
        ops_assignment_ledger_path=args.ops_assignment_ledger,
        ops_conflict_ledger_path=args.ops_conflict_ledger,
        ops_override_ledger_path=args.ops_override_ledger,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
