from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import format_markdown_row, split_markdown_row


def _guarded_enqueue_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "matrix-orchestrator" / "scripts" / "enqueue_guarded_job.py"
    spec = importlib.util.spec_from_file_location("enqueue_guarded_job", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _read_queue(path: str | Path) -> tuple[list[str], list[dict[str, str]], list[str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    table_header_index = -1
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and "|" in lines[idx + 1]:
            table_header_index = idx
            break
    if table_header_index == -1:
        raise ValueError("Queue file must contain a markdown table.")
    headers = split_markdown_row(lines[table_header_index])
    rows: list[dict[str, str]] = []
    for line in lines[table_header_index + 2 :]:
        if "|" not in line:
            break
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append({header: cells[i] for i, header in enumerate(headers)})
    return headers, rows, lines


def _write_queue(path: str | Path, headers: list[str], rows: list[dict[str, str]], original_lines: list[str]) -> None:
    output_path = Path(path)
    table_header_index = -1
    table_end_index = len(original_lines)
    for idx in range(len(original_lines) - 1):
        if "|" in original_lines[idx] and "|" in original_lines[idx + 1]:
            table_header_index = idx
            break
    if table_header_index == -1:
        raise ValueError("Queue file must contain a markdown table.")
    for idx in range(table_header_index + 2, len(original_lines)):
        if "|" not in original_lines[idx]:
            table_end_index = idx
            break

    rebuilt = list(original_lines[:table_header_index])
    rebuilt.append("| " + " | ".join(headers) + " |")
    rebuilt.append("| " + " | ".join("---" for _ in headers) + " |")
    rebuilt.extend(format_markdown_row(headers, row) for row in rows)
    rebuilt.extend(original_lines[table_end_index:])
    output_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")


def _next_job_id(rows: list[dict[str, str]]) -> str:
    max_id = 0
    for row in rows:
        match = re.fullmatch(r"cluster-job-(\d{4})", row.get("job_id", "").strip())
        if not match:
            continue
        max_id = max(max_id, int(match.group(1)))
    return f"cluster-job-{max_id + 1:04d}"


def enqueue_cluster_job(
    *,
    queue_path: str | Path,
    platform: str,
    account_alias: str,
    content_type: str,
    title: str,
    body: str,
    media_paths: list[str] | None = None,
    assignment_id: str = "",
    content_fingerprint: str = "",
    preferred_node: str = "",
    notes: str = "",
    job_type: str = "publish",
    job_id: str | None = None,
) -> dict[str, str]:
    if job_type.strip() != "publish":
        raise ValueError("unsupported_job_type")

    headers, rows, original_lines = _read_queue(queue_path)
    actual_job_id = job_id or _next_job_id(rows)
    if any(row.get("job_id", "").strip() == actual_job_id for row in rows):
        raise ValueError("duplicate_job_id")

    payload_json = json.dumps(
        {
            "title": title,
            "body": body,
            "media_paths": media_paths or [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    row = {
        "job_id": actual_job_id,
        "attempt_no": "1",
        "job_type": job_type,
        "platform": platform,
        "account_alias": account_alias,
        "content_type": content_type,
        "assignment_id": assignment_id,
        "content_fingerprint": content_fingerprint,
        "preferred_node": preferred_node,
        "payload_json": payload_json,
        "status": "pending",
        "notes": notes,
    }
    rows.append(row)
    _write_queue(queue_path, headers, rows, original_lines)
    return row


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append one pending cluster job to docs/cluster/cluster-job-queue.md.")
    parser.add_argument("--queue", default="docs/cluster/cluster-job-queue.md")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--account-alias", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--media-path", action="append", default=[])
    parser.add_argument("--assignment-ledger", default="docs/ops/content-assignment-ledger.md")
    parser.add_argument("--conflict-ledger", default="docs/ops/conflict-ledger.md")
    parser.add_argument("--submission-ref", default="")
    parser.add_argument("--assignment-id", default="")
    parser.add_argument("--content-fingerprint", default="")
    parser.add_argument("--preferred-node", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--job-type", default="publish")
    parser.add_argument("--job-id")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    if not args.assignment_id and not args.content_fingerprint:
        guarded_module = _guarded_enqueue_module()
        row = guarded_module.enqueue_guarded_job(
            queue_path=args.queue,
            assignment_ledger_path=args.assignment_ledger,
            conflict_ledger_path=args.conflict_ledger,
            platform=args.platform,
            account_alias=args.account_alias,
            content_type=args.content_type,
            title=args.title,
            body=args.body,
            media_paths=args.media_path,
            preferred_node=args.preferred_node,
            notes=args.notes,
            submission_ref=args.submission_ref,
            job_id=args.job_id,
        )
    else:
        row = enqueue_cluster_job(
            queue_path=args.queue,
            platform=args.platform,
            account_alias=args.account_alias,
            content_type=args.content_type,
            title=args.title,
            body=args.body,
            media_paths=args.media_path,
            assignment_id=args.assignment_id,
            content_fingerprint=args.content_fingerprint,
            preferred_node=args.preferred_node,
            notes=args.notes,
            job_type=args.job_type,
            job_id=args.job_id,
        )
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
