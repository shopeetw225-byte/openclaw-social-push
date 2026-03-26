from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Callable, Mapping, TypeVar


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_markdown_table import load_markdown_table
from markdown_table_utils import format_markdown_row, is_separator_row, split_markdown_row


ALLOWED_ASSIGNMENT_STATUSES = {
    "reserved",
    "queued",
    "running",
    "published",
    "blocked",
    "cancelled",
}
NON_BLOCKING_ASSIGNMENT_STATUSES = {"cancelled", "published"}
ALLOWED_CONFLICT_TYPES = {
    "duplicate_content",
    "target_account_mismatch",
    "browser_identity_mismatch",
}
ALLOWED_CONFLICT_SEVERITIES = {"block"}
ALLOWED_CONFLICT_STATUSES = {"open", "overridden", "cancelled", "resolved"}
SUPPORTED_OVERRIDE_ACTIONS = {"continue_once", "cancel_job"}
T = TypeVar("T")


class DuplicateContentError(ValueError):
    def __init__(
        self,
        *,
        content_fingerprint: str,
        existing_assignment: Mapping[str, str],
    ) -> None:
        super().__init__("duplicate_content")
        self.content_fingerprint = content_fingerprint
        self.existing_assignment = dict(existing_assignment)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_text(value: object) -> str:
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    compact = "\n".join(lines).strip()
    return re.sub(r"[ \t]+", " ", compact)


def _normalize_media_paths(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, set):
        raise ValueError("unsupported_media_paths_set")
    elif isinstance(value, (list, tuple)):
        raw_items = [str(item) for item in value]
    else:
        raw_items = [str(value)]
    return [item.strip() for item in raw_items if item.strip()]


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
    raise ValueError("Ledger must include a markdown table.")


def _read_table(path: str | Path) -> tuple[list[str], list[dict[str, str]], list[str], int, int]:
    ledger_path = Path(path)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    header_index, headers, start, end = _table_bounds(lines)
    rows: list[dict[str, str]] = []
    for line in lines[start:end]:
        if "|" not in line:
            continue
        if is_separator_row(line):
            continue
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append({header: cells[idx] for idx, header in enumerate(headers)})
    return headers, rows, lines, header_index, end


def _write_table(
    handle,
    *,
    headers: list[str],
    rows: list[dict[str, str]],
    original_lines: list[str],
    header_index: int,
    table_end: int,
) -> None:
    rebuilt = list(original_lines[:header_index])
    rebuilt.append("| " + " | ".join(headers) + " |")
    rebuilt.append("| " + " | ".join("---" for _ in headers) + " |")
    rebuilt.extend(format_markdown_row(headers, row) for row in rows)
    rebuilt.extend(original_lines[table_end:])
    handle.seek(0)
    handle.write("\n".join(rebuilt) + "\n")
    handle.truncate()
    handle.flush()


def _validate_allowed(value: str, allowed: set[str], label: str) -> str:
    normalized = value.strip()
    if normalized not in allowed:
        raise ValueError(f"invalid_{label}")
    return normalized


def _mutate_locked_ledger(path: str | Path, mutation: Callable[..., T]) -> T:
    ledger_path = Path(path)
    with ledger_path.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        lines = handle.read().splitlines()
        header_index, headers, start, end = _table_bounds(lines)
        rows: list[dict[str, str]] = []
        for line in lines[start:end]:
            if "|" not in line:
                continue
            if is_separator_row(line):
                continue
            cells = split_markdown_row(line)
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            rows.append({header: cells[idx] for idx, header in enumerate(headers)})
        result = mutation(
            headers=headers,
            rows=rows,
            original_lines=lines,
            header_index=header_index,
            table_end=end,
            handle=handle,
        )
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return result


def _next_prefixed_id(rows: list[dict[str, str]], prefix: str) -> str:
    max_number = 0
    pattern = re.compile(rf"{re.escape(prefix)}-(\d{{4}})$")
    for row in rows:
        match = pattern.fullmatch(str(row.get(f"{prefix}_id", "")).strip())
        if not match:
            continue
        max_number = max(max_number, int(match.group(1)))
    return f"{prefix}-{max_number + 1:04d}"


def build_content_fingerprint(job_like: dict[str, object]) -> str:
    normalized = {
        "content_type": _normalize_text(job_like.get("content_type", "")).lower(),
        "title": _normalize_text(job_like.get("title", "")),
        "body": _normalize_text(job_like.get("body", "")),
        "media_paths": _normalize_media_paths(job_like.get("media_paths", [])),
    }
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reserve_assignment(
    *,
    assignment_ledger_path: str | Path,
    submission_ref: str = "",
    platform: str = "",
    account_alias: str = "",
    content_type: str = "",
    job_id: str = "",
    notes: str = "",
    job_like: Mapping[str, object] | None = None,
    assignment_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, str]:
    fingerprint_source: dict[str, object] = dict(job_like or {})
    if not fingerprint_source and any([content_type]):
        fingerprint_source["content_type"] = content_type
    fingerprint = build_content_fingerprint(fingerprint_source)

    def _mutation(*, headers, rows, original_lines, header_index, table_end, handle):
        for row in rows:
            existing_fingerprint = row.get("content_fingerprint", "").strip()
            existing_status = _validate_allowed(
                row.get("status", "").strip().lower(),
                ALLOWED_ASSIGNMENT_STATUSES,
                "assignment_status",
            )
            if existing_fingerprint != fingerprint:
                continue
            if existing_status in NON_BLOCKING_ASSIGNMENT_STATUSES:
                continue
            raise DuplicateContentError(
                content_fingerprint=fingerprint,
                existing_assignment=row,
            )

        row = {
            "assignment_id": assignment_id or _next_prefixed_id(rows, "assignment"),
            "submission_ref": submission_ref.strip(),
            "content_fingerprint": fingerprint,
            "platform": str(platform).strip(),
            "account_alias": str(account_alias).strip(),
            "content_type": str(content_type or fingerprint_source.get("content_type", "")).strip(),
            "job_id": str(job_id).strip(),
            "status": "reserved",
            "notes": str(notes).strip(),
            "created_at": (created_at or _timestamp()).strip(),
        }
        _validate_allowed(row["status"], ALLOWED_ASSIGNMENT_STATUSES, "assignment_status")
        rows.append(row)
        _write_table(
            handle,
            headers=headers,
            rows=rows,
            original_lines=original_lines,
            header_index=header_index,
            table_end=table_end,
        )
        return row

    return _mutate_locked_ledger(assignment_ledger_path, _mutation)


def record_conflict(
    *,
    conflict_ledger_path: str | Path,
    assignment_id: str,
    job_id: str,
    attempt_no: int | str,
    conflict_type: str,
    summary: str,
    requested_account: str = "",
    observed_account: str = "",
    jump_target: str = "",
    notes: str = "",
    severity: str = "block",
    status: str = "open",
    conflict_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, str]:
    def _mutation(*, headers, rows, original_lines, header_index, table_end, handle):
        row = {
            "conflict_id": conflict_id or _next_prefixed_id(rows, "conflict"),
            "assignment_id": str(assignment_id).strip(),
            "job_id": str(job_id).strip(),
            "attempt_no": str(attempt_no).strip(),
            "conflict_type": _validate_allowed(
                str(conflict_type).strip(),
                ALLOWED_CONFLICT_TYPES,
                "conflict_type",
            ),
            "severity": _validate_allowed(
                str(severity).strip(),
                ALLOWED_CONFLICT_SEVERITIES,
                "conflict_severity",
            ),
            "status": _validate_allowed(
                str(status).strip(),
                ALLOWED_CONFLICT_STATUSES,
                "conflict_status",
            ),
            "summary": str(summary).strip(),
            "requested_account": str(requested_account).strip(),
            "observed_account": str(observed_account).strip(),
            "jump_target": str(jump_target).strip(),
            "notes": str(notes).strip(),
            "timestamp": str(timestamp or _timestamp()).strip(),
        }
        rows.append(row)
        _write_table(
            handle,
            headers=headers,
            rows=rows,
            original_lines=original_lines,
            header_index=header_index,
            table_end=table_end,
        )
        return row

    return _mutate_locked_ledger(conflict_ledger_path, _mutation)


def find_applicable_override(
    *,
    override_ledger_path: str | Path,
    conflict_id: str,
    job_id: str,
    attempt_no: int | str,
) -> dict[str, str] | None:
    target_conflict_id = str(conflict_id).strip()
    target_job_id = str(job_id).strip()
    target_attempt_no = str(attempt_no).strip()
    rows = load_markdown_table(override_ledger_path)
    for row in reversed(rows):
        if row.get("conflict_id", "").strip() != target_conflict_id:
            continue
        if row.get("job_id", "").strip() != target_job_id:
            continue
        if row.get("attempt_no", "").strip() != target_attempt_no:
            continue
        _validate_allowed(
            row.get("action", "").strip(),
            SUPPORTED_OVERRIDE_ACTIONS,
            "override_action",
        )
        return row
    return None


def sync_assignment_terminal_state(
    *,
    assignment_ledger_path: str | Path,
    assignment_id: str,
    status: str,
    notes: str = "",
) -> None:
    target_assignment_id = str(assignment_id).strip()
    validated_status = _validate_allowed(
        str(status).strip(),
        ALLOWED_ASSIGNMENT_STATUSES,
        "assignment_status",
    )

    def _mutation(*, headers, rows, original_lines, header_index, table_end, handle):
        for row in rows:
            if row.get("assignment_id", "").strip() != target_assignment_id:
                continue
            row["status"] = validated_status
            if notes.strip():
                row["notes"] = notes.strip()
            _write_table(
                handle,
                headers=headers,
                rows=rows,
                original_lines=original_lines,
                header_index=header_index,
                table_end=table_end,
            )
            return None
        raise ValueError("assignment_not_found")

    _mutate_locked_ledger(assignment_ledger_path, _mutation)
