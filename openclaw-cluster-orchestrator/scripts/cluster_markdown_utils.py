from __future__ import annotations


def escape_markdown_cell(value: object) -> str:
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    return text


def format_markdown_row(columns: list[str], row: dict[str, object]) -> str:
    cells = [escape_markdown_cell(row.get(column, "")) for column in columns]
    return "| " + " | ".join(cells) + " |"


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if (
            char == "\\"
            and index + 1 < len(stripped)
            and stripped[index + 1] in {"|", "\\"}
        ):
            current.append(stripped[index + 1])
            index += 2
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1

    cells.append("".join(current).strip())
    return cells


def is_separator_row(line: str) -> bool:
    cells = split_markdown_row(line)
    if not cells:
        return False
    for cell in cells:
        if not cell:
            return False
        if any(char not in "-: " for char in cell):
            return False
    return True
