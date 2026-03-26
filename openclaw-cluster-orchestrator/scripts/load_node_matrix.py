from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import is_separator_row, split_markdown_row


REQUIRED_COLUMNS = (
    "node_id",
    "mode",
    "agent_id",
    "platforms",
    "account_aliases",
    "capabilities",
    "status",
)
LIST_COLUMNS = {"platforms", "account_aliases", "capabilities"}
LOWER_COLUMNS = {"mode", "status"}


def _is_table_row(line: str) -> bool:
    return "|" in line


def _normalize_list_cell(value: str) -> str:
    items = [item.strip() for item in value.split(",")]
    normalized = [item for item in items if item]
    return ",".join(normalized)


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        text = value.strip()
        if key in LIST_COLUMNS:
            text = _normalize_list_cell(text)
        if key in LOWER_COLUMNS:
            text = text.lower()
        normalized[key] = text
    return normalized


def load_node_matrix(path: str | Path) -> list[dict[str, str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()

    headers: list[str] | None = None
    table_start = -1
    for index in range(len(lines) - 1):
        header_line = lines[index]
        separator_line = lines[index + 1]
        if not _is_table_row(header_line):
            continue
        if not _is_table_row(separator_line):
            continue
        if not is_separator_row(separator_line):
            continue
        headers = split_markdown_row(header_line)
        table_start = index + 2
        break

    if headers is None:
        return []

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in headers
    ]
    if missing_columns:
        raise ValueError("missing_required_columns")

    rows: list[dict[str, str]] = []
    for line in lines[table_start:]:
        if not _is_table_row(line):
            break
        if is_separator_row(line):
            continue
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        row = {
            header: cells[idx] if idx < len(cells) else ""
            for idx, header in enumerate(headers)
        }
        rows.append(_normalize_row(row))

    return rows
