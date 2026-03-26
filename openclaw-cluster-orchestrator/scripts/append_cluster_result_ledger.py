from __future__ import annotations

from pathlib import Path
import sys
from typing import Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import format_markdown_row, is_separator_row, split_markdown_row


TERMINAL_RESULT_STATUSES = {
    "routing_blocked",
    "dispatch_error",
    "runner_error",
    "preflight_blocked",
    "publish_ok",
    "publish_filtered",
    "publish_failed",
}


def _row_from_cells(headers: list[str], cells: list[str]) -> dict[str, str]:
    normalized = list(cells)
    if len(normalized) < len(headers):
        normalized.extend([""] * (len(headers) - len(normalized)))
    return {header: normalized[idx] for idx, header in enumerate(headers)}


def _table_bounds(lines: list[str]) -> tuple[list[str], int, int]:
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
        return headers, start, end
    raise ValueError("Ledger must include a markdown table.")


def append_cluster_result_ledger(path: str | Path, row: Mapping[str, object]) -> None:
    ledger_path = Path(path)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    headers, start, end = _table_bounds(lines)
    key_job_id = str(row.get("job_id", ""))
    key_attempt_no = str(row.get("attempt_no", ""))

    for line in lines[start:end]:
        if "|" not in line:
            continue
        existing = _row_from_cells(headers, split_markdown_row(line))
        if existing.get("job_id", "") != key_job_id:
            continue
        if existing.get("attempt_no", "") != key_attempt_no:
            continue
        if existing.get("result_status", "").strip() in TERMINAL_RESULT_STATUSES:
            raise ValueError(
                "Refusing to append for an existing terminal cluster ledger key "
                f"{key_job_id}:{key_attempt_no}."
            )

    lines.insert(end, format_markdown_row(headers, dict(row)))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
