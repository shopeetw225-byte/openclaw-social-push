from __future__ import annotations

from pathlib import Path
import sys
from typing import Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from markdown_table_utils import format_markdown_row, is_separator_row


RUN_LOG_COLUMNS = ["job_id", "attempt_no", "event", "status", "notes", "timestamp"]


def _table_bounds(lines: list[str]) -> tuple[int, int]:
    for index in range(len(lines) - 1):
        if "|" not in lines[index] or "|" not in lines[index + 1]:
            continue
        if not is_separator_row(lines[index + 1]):
            continue
        start = index + 2
        end = start
        while end < len(lines) and "|" in lines[end]:
            end += 1
        return index, end
    return -1, -1


def append_run_log(path: str | Path, row: Mapping[str, object]) -> None:
    log_path = Path(path)
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    if not lines:
        lines = [
            "| " + " | ".join(RUN_LOG_COLUMNS) + " |",
            "| " + " | ".join("---" for _ in RUN_LOG_COLUMNS) + " |",
        ]
        _, table_end = 0, 2
    else:
        header_index, table_end = _table_bounds(lines)
        if header_index == -1:
            lines.extend(
                [
                    "| " + " | ".join(RUN_LOG_COLUMNS) + " |",
                    "| " + " | ".join("---" for _ in RUN_LOG_COLUMNS) + " |",
                ]
            )
            _, table_end = _table_bounds(lines)

    lines.insert(table_end, format_markdown_row(RUN_LOG_COLUMNS, dict(row)))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
