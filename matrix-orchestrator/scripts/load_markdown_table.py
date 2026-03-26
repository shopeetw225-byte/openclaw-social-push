from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from markdown_table_utils import is_separator_row, split_markdown_row


def _is_table_row(line: str) -> bool:
    return "|" in line


def load_markdown_table(path: str | Path) -> list[dict[str, str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()

    header_cells: list[str] | None = None
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
        header_cells = split_markdown_row(header_line)
        table_start = index + 2
        break

    if header_cells is None:
        return []

    rows: list[dict[str, str]] = []
    for line in lines[table_start:]:
        if not _is_table_row(line):
            break
        if is_separator_row(line):
            continue
        cells = split_markdown_row(line)
        if len(cells) < len(header_cells):
            cells.extend([""] * (len(header_cells) - len(cells)))
        row = {
            header: cells[idx] if idx < len(cells) else ""
            for idx, header in enumerate(header_cells)
        }
        rows.append(row)

    return rows
