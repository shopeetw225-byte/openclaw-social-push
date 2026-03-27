from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import format_markdown_row, split_markdown_row


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


def _find_matching_rows(rows: list[dict[str, str]], job_id: str, attempt_no: str | None) -> list[dict[str, str]]:
    matching = [row for row in rows if row.get("job_id", "").strip() == job_id]
    if attempt_no is not None:
        matching = [row for row in matching if row.get("attempt_no", "").strip() == attempt_no.strip()]
    return matching


def _attempt_value(row: dict[str, str]) -> int:
    raw = row.get("attempt_no", "").strip()
    if not re.fullmatch(r"\d+", raw):
        raise ValueError(f"invalid_attempt_no:{raw}")
    return int(raw)


def _next_attempt_no(rows: list[dict[str, str]], job_id: str) -> str:
    matching = _find_matching_rows(rows, job_id, None)
    if not matching:
        raise ValueError(f"job_not_found:{job_id}")
    return str(max(_attempt_value(row) for row in matching) + 1)


def _source_row_for_retry(
    rows: list[dict[str, str]],
    *,
    job_id: str,
    attempt_no: str | None,
) -> dict[str, str]:
    matching = _find_matching_rows(rows, job_id, attempt_no)
    if not matching:
        if attempt_no is None:
            raise ValueError(f"job_not_found:{job_id}")
        raise ValueError(f"attempt_not_found:{job_id}:{attempt_no}")
    if attempt_no is None:
        source_row = max(matching, key=_attempt_value)
    else:
        source_row = matching[-1]
    status = source_row.get("status", "").strip()
    if status not in {"failed", "blocked"}:
        raise ValueError(f"source_status_not_retryable:{status}")
    return source_row


def requeue_cluster_job(
    *,
    queue_path: str | Path,
    job_id: str,
    attempt_no: str | None = None,
    notes: str = "",
) -> dict[str, str]:
    headers, rows, original_lines = _read_queue(queue_path)
    source_row = _source_row_for_retry(rows, job_id=job_id, attempt_no=attempt_no)
    next_attempt = _next_attempt_no(rows, job_id)
    new_row = {
        "job_id": source_row.get("job_id", "").strip(),
        "attempt_no": next_attempt,
        "job_type": source_row.get("job_type", "").strip(),
        "platform": source_row.get("platform", "").strip(),
        "account_alias": source_row.get("account_alias", "").strip(),
        "content_type": source_row.get("content_type", "").strip(),
        "assignment_id": source_row.get("assignment_id", "").strip(),
        "content_fingerprint": source_row.get("content_fingerprint", "").strip(),
        "preferred_node": source_row.get("preferred_node", "").strip(),
        "payload_json": source_row.get("payload_json", "").strip(),
        "status": "pending",
        "notes": notes if notes else f"retry_of:{source_row.get('attempt_no', '').strip()}",
    }
    rows.append(new_row)
    _write_queue(queue_path, headers, rows, original_lines)
    return new_row


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a retry attempt to a cluster job queue markdown table.")
    parser.add_argument("--queue", default="docs/cluster/cluster-job-queue.md")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-no")
    parser.add_argument("--notes", default="")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    row = requeue_cluster_job(
        queue_path=args.queue,
        job_id=args.job_id,
        attempt_no=args.attempt_no,
        notes=args.notes,
    )
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
