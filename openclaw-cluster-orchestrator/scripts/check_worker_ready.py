from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cluster_markdown_utils import is_separator_row, split_markdown_row


ProbeRunner = Callable[..., dict[str, Any]]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_script_module(script_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_table(path: str | Path) -> list[dict[str, str]]:
    table_path = Path(path)
    if not table_path.exists():
        raise FileNotFoundError(str(table_path))
    lines = table_path.read_text(encoding="utf-8").splitlines()
    headers: list[str] | None = None
    table_start = -1
    for index in range(len(lines) - 1):
        header_line = lines[index]
        separator_line = lines[index + 1]
        if "|" not in header_line or "|" not in separator_line:
            continue
        if not is_separator_row(separator_line):
            continue
        headers = split_markdown_row(header_line)
        table_start = index + 2
        break

    if headers is None:
        return []

    rows: list[dict[str, str]] = []
    for line in lines[table_start:]:
        if "|" not in line:
            break
        if is_separator_row(line):
            continue
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append({header: cells[idx] for idx, header in enumerate(headers)})
    return rows


def _normalize(value: str) -> str:
    return " ".join(str(value or "").split()).strip().casefold()


def _find_account_row(
    rows: list[dict[str, str]],
    *,
    platform: str,
    account_alias: str,
) -> dict[str, str] | None:
    normalized_platform = _normalize(platform)
    normalized_account_alias = _normalize(account_alias)
    for row in rows:
        if _normalize(row.get("platform", "")) != normalized_platform:
            continue
        if _normalize(row.get("account_alias", "")) != normalized_account_alias:
            continue
        return row
    return None


def check_worker_ready(
    *,
    node_runtime_root: str | Path = "docs/nodes",
    node_id: str,
    platform: str,
    account_alias: str,
    browser_probe_runner: ProbeRunner | None = None,
) -> dict[str, str]:
    runtime_root = Path(node_runtime_root)
    account_matrix_path = runtime_root / node_id / "matrix" / "account-matrix.md"
    try:
        account_rows = _load_table(account_matrix_path)
    except FileNotFoundError:
        return {
            "ok": False,
            "reason": "missing_account_matrix",
            "status": "missing_account_matrix",
            "expected_display_name": "",
            "browser_profile": "",
            "observed_account": "",
            "jump_target": "",
            "notes": str(account_matrix_path),
        }

    account_row = _find_account_row(
        account_rows,
        platform=platform,
        account_alias=account_alias,
    )
    if account_row is None:
        return {
            "ok": False,
            "reason": "missing_account_row",
            "status": "missing_account_row",
            "expected_display_name": "",
            "browser_profile": "",
            "observed_account": "",
            "jump_target": "",
            "notes": "",
        }

    expected_display_name = str(account_row.get("display_name", "")).strip()
    browser_profile = str(account_row.get("browser_profile", "")).strip()
    if not browser_profile:
        return {
            "ok": False,
            "reason": "missing_browser_profile",
            "status": "missing_browser_profile",
            "expected_display_name": expected_display_name,
            "browser_profile": "",
            "observed_account": "",
            "jump_target": "",
            "notes": "",
        }
    if not expected_display_name:
        return {
            "ok": False,
            "reason": "missing_display_name",
            "status": "missing_display_name",
            "expected_display_name": "",
            "browser_profile": browser_profile,
            "observed_account": "",
            "jump_target": "",
            "notes": "",
        }

    active_runner = browser_probe_runner
    if active_runner is None:
        probe_module = _load_script_module(
            _project_root() / "matrix-orchestrator" / "scripts" / "probe_browser_identity.py",
            "probe_browser_identity",
        )
        active_runner = probe_module.probe_browser_identity

    probe = active_runner(
        platform=platform,
        expected_display_name=expected_display_name,
        browser_profile=browser_profile,
    )
    probe_status = str(probe.get("status", "")).strip() or "unknown"
    observed_account = str(probe.get("observed_account", "")).strip()
    jump_target = str(probe.get("jump_target", "")).strip()
    notes = str(probe.get("notes", "")).strip()

    if probe_status == "ok" and _normalize(observed_account) == _normalize(expected_display_name):
        return {
            "ok": True,
            "reason": "ready",
            "status": "ok",
            "expected_display_name": expected_display_name,
            "browser_profile": browser_profile,
            "observed_account": observed_account,
            "jump_target": jump_target,
            "notes": notes,
        }

    reason = probe_status
    if probe_status == "ok" and observed_account:
        reason = "account_mismatch"

    return {
        "ok": False,
        "reason": reason,
        "status": reason,
        "expected_display_name": expected_display_name,
        "browser_profile": browser_profile,
        "observed_account": observed_account,
        "jump_target": jump_target,
        "notes": notes,
    }
