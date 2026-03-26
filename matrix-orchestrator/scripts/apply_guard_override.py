from __future__ import annotations

import argparse
import fcntl
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from append_run_log import append_run_log
from content_assignment_guard import SUPPORTED_OVERRIDE_ACTIONS, sync_assignment_terminal_state
from markdown_table_utils import format_markdown_row, is_separator_row, split_markdown_row


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _table_bounds(lines: list[str]) -> tuple[int, list[str], int, int]:
    for index in range(len(lines) - 1):
        if "|" not in lines[index] or "|" not in lines[index + 1]:
            continue
        if not is_separator_row(lines[index + 1]):
            continue
        headers = split_markdown_row(lines[index])
        start = index + 2
        end = start
        while end < len(lines) and "|" in lines[end]:
            end += 1
        return index, headers, start, end
    raise ValueError("markdown_table_missing")


def _mutate_table(path: str | Path, mutation):
    table_path = Path(path)
    with table_path.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        lines = handle.read().splitlines()
        header_index, headers, start, end = _table_bounds(lines)
        rows: list[dict[str, str]] = []
        for line in lines[start:end]:
            if "|" not in line or is_separator_row(line):
                continue
            cells = split_markdown_row(line)
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            rows.append({header: cells[idx] for idx, header in enumerate(headers)})
        result = mutation(rows)
        rebuilt = list(lines[:header_index])
        rebuilt.append("| " + " | ".join(headers) + " |")
        rebuilt.append("| " + " | ".join("---" for _ in headers) + " |")
        rebuilt.extend(format_markdown_row(headers, row) for row in rows)
        rebuilt.extend(lines[end:])
        handle.seek(0)
        handle.write("\n".join(rebuilt) + "\n")
        handle.truncate()
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return result


def _next_override_id(rows: list[dict[str, str]]) -> str:
    max_number = 0
    for row in rows:
        raw_id = row.get("override_id", "").strip()
        if not raw_id.startswith("override-"):
            continue
        try:
            max_number = max(max_number, int(raw_id.split("-", 1)[1]))
        except ValueError:
            continue
    return f"override-{max_number + 1:04d}"


def _append_override_row(
    *,
    override_ledger_path: str | Path,
    conflict_id: str,
    job_id: str,
    attempt_no: str,
    action: str,
    operator_ref: str,
    reason: str,
) -> dict[str, str]:
    def _mutation(rows: list[dict[str, str]]):
        row = {
            "override_id": _next_override_id(rows),
            "conflict_id": conflict_id,
            "job_id": job_id,
            "attempt_no": attempt_no,
            "action": action,
            "operator_ref": operator_ref,
            "reason": reason,
            "timestamp": _timestamp(),
        }
        rows.append(row)
        return row

    return _mutate_table(override_ledger_path, _mutation)


def _update_conflict_status(
    conflict_ledger_path: str | Path,
    *,
    conflict_id: str,
    status: str,
) -> dict[str, str]:
    def _mutation(rows: list[dict[str, str]]):
        for row in rows:
            if row.get("conflict_id", "").strip() != conflict_id:
                continue
            row["status"] = status
            return row
        raise ValueError("conflict_not_found")

    return _mutate_table(conflict_ledger_path, _mutation)


def _update_queue_row(
    queue_path: str | Path,
    *,
    job_id: str,
    attempt_no: str,
    status: str,
    notes: str,
) -> dict[str, str]:
    def _mutation(rows: list[dict[str, str]]):
        for row in rows:
            if row.get("job_id", "").strip() != job_id:
                continue
            if row.get("attempt_no", "").strip() != attempt_no:
                continue
            row["status"] = status
            row["notes"] = notes
            return row
        raise ValueError("queue_row_not_found")

    return _mutate_table(queue_path, _mutation)


def apply_guard_override(
    *,
    queue_path: str | Path,
    assignment_ledger_path: str | Path,
    conflict_ledger_path: str | Path,
    override_ledger_path: str | Path,
    conflict_id: str,
    job_id: str,
    attempt_no: str,
    action: str,
    operator_ref: str,
    reason: str,
    run_log_path: str | Path | None = None,
) -> dict[str, str]:
    normalized_action = action.strip()
    if normalized_action not in SUPPORTED_OVERRIDE_ACTIONS:
        raise ValueError("invalid_override_action")

    conflict_row = _update_conflict_status(
        conflict_ledger_path,
        conflict_id=conflict_id,
        status="overridden" if normalized_action == "continue_once" else "cancelled",
    )
    queue_row = _update_queue_row(
        queue_path,
        job_id=job_id,
        attempt_no=str(attempt_no).strip(),
        status="pending" if normalized_action == "continue_once" else "cancelled",
        notes=normalized_action,
    )

    if normalized_action == "cancel_job":
        sync_assignment_terminal_state(
            assignment_ledger_path=assignment_ledger_path,
            assignment_id=conflict_row.get("assignment_id", "").strip(),
            status="cancelled",
            notes="cancel_job",
        )

    override_row = _append_override_row(
        override_ledger_path=override_ledger_path,
        conflict_id=conflict_id,
        job_id=job_id,
        attempt_no=str(attempt_no).strip(),
        action=normalized_action,
        operator_ref=operator_ref,
        reason=reason,
    )
    if run_log_path:
        append_run_log(
            path=run_log_path,
            row={
                "job_id": queue_row["job_id"],
                "attempt_no": queue_row["attempt_no"],
                "event": "override_applied",
                "status": normalized_action,
                "notes": reason,
                "timestamp": override_row["timestamp"],
            },
        )
    return override_row


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply one explicit content-assignment guard override.")
    parser.add_argument("--queue", default="docs/matrix/job-queue.md")
    parser.add_argument("--assignment-ledger", default="docs/ops/content-assignment-ledger.md")
    parser.add_argument("--conflict-ledger", default="docs/ops/conflict-ledger.md")
    parser.add_argument("--override-ledger", default="docs/ops/operator-override-ledger.md")
    parser.add_argument("--run-log", default="")
    parser.add_argument("--conflict-id", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-no", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--operator-ref", required=True)
    parser.add_argument("--reason", required=True)
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    row = apply_guard_override(
        queue_path=args.queue,
        assignment_ledger_path=args.assignment_ledger,
        conflict_ledger_path=args.conflict_ledger,
        override_ledger_path=args.override_ledger,
        conflict_id=args.conflict_id,
        job_id=args.job_id,
        attempt_no=args.attempt_no,
        action=args.action,
        operator_ref=args.operator_ref,
        reason=args.reason,
        run_log_path=args.run_log or None,
    )
    print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
