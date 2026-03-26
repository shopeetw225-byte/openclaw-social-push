from __future__ import annotations

from pathlib import Path
import sys
from typing import Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from markdown_table_utils import format_markdown_row, is_separator_row, split_markdown_row


ALLOWED_STATUSES = {
    "workflow_only",
    "page_verified",
    "submit_ok",
    "real_publish_ok",
    "submit_ok_filtered",
}

KEY_COLUMNS = ("platform", "account_alias", "content_type")
UPDATED_COLUMNS = ("status", "evidence", "notes", "last_verified")
def _is_table_row(line: str) -> bool:
    return "|" in line


def _row_from_cells(headers: list[str], cells: list[str]) -> dict[str, str]:
    normalized = list(cells)
    if len(normalized) < len(headers):
        normalized.extend([""] * (len(headers) - len(normalized)))
    return {header: normalized[idx] for idx, header in enumerate(headers)}
def _table_bounds(lines: list[str]) -> tuple[list[str], int, int]:
    for index in range(len(lines) - 1):
        if not _is_table_row(lines[index]):
            continue
        if not _is_table_row(lines[index + 1]):
            continue
        if not is_separator_row(lines[index + 1]):
            continue
        headers = split_markdown_row(lines[index])
        start = index + 2
        end = start
        while end < len(lines) and _is_table_row(lines[end]):
            end += 1
        return headers, start, end
    raise ValueError("Verification matrix must include a markdown table.")


def update_verification_matrix(path: str | Path, row: Mapping[str, object]) -> None:
    matrix_path = Path(path)
    lines = matrix_path.read_text(encoding="utf-8").splitlines()
    headers, start, end = _table_bounds(lines)

    status = str(row.get("status", "")).strip()
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported verification status: {status!r}")

    candidate: dict[str, str] = {}
    for header in headers:
        candidate[header] = str(row.get(header, ""))

    for column in KEY_COLUMNS:
        candidate[column] = str(row.get(column, "")).strip()

    candidate["status"] = status
    for column in ("evidence", "notes", "last_verified"):
        candidate[column] = str(row.get(column, ""))

    replacement_line = format_markdown_row(headers, candidate)

    for line_index in range(start, end):
        current_line = lines[line_index]
        if is_separator_row(current_line):
            continue
        existing = _row_from_cells(headers, split_markdown_row(current_line))
        if any(existing.get(column, "").strip() != candidate[column] for column in KEY_COLUMNS):
            continue
        updated = dict(existing)
        for column in UPDATED_COLUMNS:
            updated[column] = candidate[column]
        lines[line_index] = format_markdown_row(headers, updated)
        matrix_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.insert(end, replacement_line)
    matrix_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
