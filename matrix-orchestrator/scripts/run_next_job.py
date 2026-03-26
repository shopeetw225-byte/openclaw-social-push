from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from markdown_table_utils import format_markdown_row, split_markdown_row
from content_assignment_guard import record_conflict, sync_assignment_terminal_state


RESULT_STATUS_FOR_BLOCK = "preflight_blocked"


def _load_script_module(script_name: str, module_name: str):
    script_path = Path(__file__).resolve().parent / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_queue(queue_path: str | Path) -> tuple[list[str], list[dict[str, str]], list[str]]:
    path = Path(queue_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    table_header_index = -1
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and "|" in lines[idx + 1]:
            table_header_index = idx
            break
    if table_header_index == -1:
        raise ValueError("Queue file must contain a markdown table.")
    headers = split_markdown_row(lines[table_header_index])
    table_rows: list[dict[str, str]] = []
    for line in lines[table_header_index + 2 :]:
        if "|" not in line:
            break
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        table_rows.append({header: cells[i] for i, header in enumerate(headers)})
    return headers, table_rows, lines


def _write_queue(
    queue_path: str | Path,
    headers: list[str],
    rows: list[dict[str, str]],
    original_lines: list[str],
) -> None:
    path = Path(queue_path)
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
    path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")


def _find_first_pending(rows: list[dict[str, str]]) -> int | None:
    for idx, row in enumerate(rows):
        if row.get("status", "").strip() == "pending":
            return idx
    return None


def run_next_job(
    queue_path: str | Path,
    preflight_runner: Callable[..., dict[str, Any]] | None = None,
    dispatch_runner: Callable[..., dict[str, Any]] | None = None,
    ledger_writer: Callable[..., Any] | None = None,
    run_log_writer: Callable[..., Any] | None = None,
    verification_updater: Callable[..., Any] | None = None,
    account_matrix_path: str | Path | None = None,
    verification_matrix_path: str | Path | None = None,
    result_ledger_path: str | Path | None = None,
    run_log_path: str | Path | None = None,
    assignment_ledger_path: str | Path | None = None,
    conflict_ledger_path: str | Path | None = None,
    override_ledger_path: str | Path | None = None,
    browser_probe_runner: Callable[..., dict[str, Any]] | None = None,
    allow_warn: bool = False,
    update_verification: bool = True,
) -> dict[str, Any]:
    if preflight_runner is None or ledger_writer is None or run_log_writer is None or verification_updater is None:
        loader_module = _load_script_module("load_markdown_table.py", "load_markdown_table")
        if preflight_runner is None:
            preflight_module = _load_script_module("run_preflight.py", "run_preflight")
            verification_rows = loader_module.load_markdown_table(
                verification_matrix_path or "docs/matrix/verification-matrix.md"
            )
            account_rows = loader_module.load_markdown_table(
                account_matrix_path or "docs/matrix/account-matrix.md"
            )
            assignment_rows = loader_module.load_markdown_table(
                assignment_ledger_path or "docs/ops/content-assignment-ledger.md"
            )
            conflict_rows = loader_module.load_markdown_table(
                conflict_ledger_path or "docs/ops/conflict-ledger.md"
            )
            override_rows = loader_module.load_markdown_table(
                override_ledger_path or "docs/ops/operator-override-ledger.md"
            )
            probe_module = None
            if browser_probe_runner is None:
                probe_module = _load_script_module(
                    "probe_browser_identity.py",
                    "probe_browser_identity",
                )

            def _default_preflight(job: dict[str, Any], allow_warn: bool = False):
                job_with_probe = dict(job)
                has_account = any(
                    row.get("platform", "").strip().lower() == job["platform"].strip().lower()
                    and row.get("account_alias", "").strip().lower() == job["account_alias"].strip().lower()
                    for row in account_rows
                )
                if not has_account:
                    return {
                        "decision": "block",
                        "reason": "missing_account_row",
                        "matched_rows": [],
                        "normalized_task_inputs": {
                            "platform": str(job.get("platform", "")).strip().lower(),
                            "account_alias": str(job.get("account_alias", "")).strip().lower(),
                            "content_type": str(job.get("content_type", "")).strip().lower(),
                        },
                    }
                account_row = next(
                    (
                        row
                        for row in account_rows
                        if row.get("platform", "").strip().lower() == job["platform"].strip().lower()
                        and row.get("account_alias", "").strip().lower() == job["account_alias"].strip().lower()
                    ),
                    None,
                )
                if account_row is not None and not str(job_with_probe.get("observed_account", "")).strip():
                    browser_profile = str(account_row.get("browser_profile", "")).strip()
                    expected_display_name = str(account_row.get("display_name", "")).strip()
                    if browser_profile and expected_display_name:
                        probe_runner = browser_probe_runner or probe_module.probe_browser_identity
                        probe = probe_runner(
                            platform=job["platform"],
                            expected_display_name=expected_display_name,
                            browser_profile=browser_profile,
                        )
                        observed_account = str(probe.get("observed_account", "")).strip()
                        jump_target = str(probe.get("jump_target", "")).strip()
                        if observed_account:
                            job_with_probe["observed_account"] = observed_account
                        if jump_target:
                            job_with_probe["jump_target"] = jump_target
                has_verification = any(
                    row.get("platform", "").strip().lower() == job["platform"].strip().lower()
                    and row.get("account_alias", "").strip().lower() == job["account_alias"].strip().lower()
                    and row.get("content_type", "").strip().lower() == job["content_type"].strip().lower()
                    for row in verification_rows
                )
                if not has_verification:
                    return {
                        "decision": "block",
                        "reason": "missing_verification_row",
                        "matched_rows": [],
                        "normalized_task_inputs": {
                            "platform": str(job.get("platform", "")).strip().lower(),
                            "account_alias": str(job.get("account_alias", "")).strip().lower(),
                            "content_type": str(job.get("content_type", "")).strip().lower(),
                        },
                    }
                return preflight_module.run_preflight(
                    verification_rows,
                    job_with_probe,
                    assignment_rows=assignment_rows,
                    account_rows=account_rows,
                    conflict_rows=conflict_rows,
                    override_rows=override_rows,
                    allow_warn=allow_warn,
                )

            preflight_runner = _default_preflight

        if ledger_writer is None:
            ledger_module = _load_script_module("append_result_ledger.py", "append_result_ledger")
            ledger_writer = ledger_module.append_result_ledger
        if run_log_writer is None:
            run_log_module = _load_script_module("append_run_log.py", "append_run_log")
            run_log_writer = run_log_module.append_run_log
        if verification_updater is None:
            verification_module = _load_script_module(
                "update_verification_matrix.py",
                "update_verification_matrix",
            )
            verification_updater = verification_module.update_verification_matrix

    if dispatch_runner is None:
        dispatch_module = _load_script_module("dispatch_social_push.py", "dispatch_social_push")

        def _default_dispatch(job: dict[str, Any]):
            return dispatch_module.dispatch_social_push(job)

        dispatch_runner = _default_dispatch

    headers, rows, original_lines = _read_queue(queue_path)

    if any(row.get("status", "").strip() == "running" for row in rows):
        return {"status": "blocked", "reason": "running_job_exists"}

    pending_index = _find_first_pending(rows)
    if pending_index is None:
        return {"status": "blocked", "reason": "no_pending_job"}

    job = rows[pending_index]
    job["status"] = "running"
    _write_queue(queue_path, headers, rows, original_lines)

    run_log_writer(
        path=run_log_path or "docs/matrix/run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "event": "job_started",
            "status": "ok",
            "notes": "",
            "timestamp": _timestamp(),
        },
    )
    if assignment_ledger_path and job.get("assignment_id", "").strip():
        sync_assignment_terminal_state(
            assignment_ledger_path=assignment_ledger_path,
            assignment_id=job["assignment_id"],
            status="running",
            notes="job_started",
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "assignment_updated",
                "status": "running",
                "notes": "job_started",
                "timestamp": _timestamp(),
            },
        )

    preflight = preflight_runner(job, allow_warn=allow_warn)
    run_log_writer(
        path=run_log_path or "docs/matrix/run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "event": "decision_made",
            "status": preflight["decision"],
            "notes": preflight["reason"],
            "timestamp": _timestamp(),
        },
    )

    if preflight["decision"] == "block":
        conflict_id = str(preflight.get("conflict_id", "")).strip()
        jump_target = str(preflight.get("jump_target", "")).strip()
        if conflict_ledger_path and preflight.get("conflict_type"):
            if not conflict_id:
                conflict = record_conflict(
                    conflict_ledger_path=conflict_ledger_path,
                    assignment_id=job.get("assignment_id", "").strip(),
                    job_id=job["job_id"],
                    attempt_no=job["attempt_no"],
                    conflict_type=str(preflight.get("conflict_type", "")).strip(),
                    summary=str(preflight.get("summary", preflight["reason"])).strip(),
                    requested_account=str(preflight.get("requested_account", job.get("account_alias", ""))).strip(),
                    observed_account=str(preflight.get("observed_account", "")).strip(),
                    jump_target=jump_target,
                    notes=str(preflight["reason"]).strip(),
                )
                conflict_id = conflict["conflict_id"]
                if not jump_target:
                    jump_target = conflict.get("jump_target", "")
            run_log_writer(
                path=run_log_path or "docs/matrix/run-log.md",
                row={
                    "job_id": job["job_id"],
                    "attempt_no": job["attempt_no"],
                    "event": "guard_conflict_recorded",
                    "status": str(preflight.get("conflict_type", "")).strip() or preflight["reason"],
                    "notes": conflict_id,
                    "timestamp": _timestamp(),
                },
            )
        job["status"] = "blocked"
        job["notes"] = preflight["reason"]
        _write_queue(queue_path, headers, rows, original_lines)
        if assignment_ledger_path and job.get("assignment_id", "").strip():
            sync_assignment_terminal_state(
                assignment_ledger_path=assignment_ledger_path,
                assignment_id=job["assignment_id"],
                status="blocked",
                notes=str(preflight["reason"]).strip(),
            )
            run_log_writer(
                path=run_log_path or "docs/matrix/run-log.md",
                row={
                    "job_id": job["job_id"],
                    "attempt_no": job["attempt_no"],
                    "event": "assignment_updated",
                    "status": "blocked",
                    "notes": str(preflight["reason"]).strip(),
                    "timestamp": _timestamp(),
                },
            )
        ledger_writer(
            path=result_ledger_path or "docs/matrix/result-ledger.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "platform": job["platform"],
                "account_alias": job["account_alias"],
                "content_type": job["content_type"],
                "decision": "block",
                "result_status": RESULT_STATUS_FOR_BLOCK,
                "conflict_id": conflict_id,
                "jump_target": jump_target,
                "evidence": "",
                "notes": preflight["reason"],
                "timestamp": _timestamp(),
            },
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "ledger_updated",
                "status": RESULT_STATUS_FOR_BLOCK,
                "notes": preflight["reason"],
                "timestamp": _timestamp(),
            },
        )
        return {"status": "blocked", "reason": preflight["reason"]}

    if preflight["decision"] == "warn" and not allow_warn:
        job["status"] = "blocked"
        job["notes"] = "warn_not_allowed"
        _write_queue(queue_path, headers, rows, original_lines)
        if assignment_ledger_path and job.get("assignment_id", "").strip():
            sync_assignment_terminal_state(
                assignment_ledger_path=assignment_ledger_path,
                assignment_id=job["assignment_id"],
                status="blocked",
                notes="warn_not_allowed",
            )
            run_log_writer(
                path=run_log_path or "docs/matrix/run-log.md",
                row={
                    "job_id": job["job_id"],
                    "attempt_no": job["attempt_no"],
                    "event": "assignment_updated",
                    "status": "blocked",
                    "notes": "warn_not_allowed",
                    "timestamp": _timestamp(),
                },
            )
        ledger_writer(
            path=result_ledger_path or "docs/matrix/result-ledger.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "platform": job["platform"],
                "account_alias": job["account_alias"],
                "content_type": job["content_type"],
                "decision": "warn",
                "result_status": RESULT_STATUS_FOR_BLOCK,
                "conflict_id": "",
                "jump_target": "",
                "evidence": "",
                "notes": "warn_not_allowed",
                "timestamp": _timestamp(),
            },
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "ledger_updated",
                "status": RESULT_STATUS_FOR_BLOCK,
                "notes": "warn_not_allowed",
                "timestamp": _timestamp(),
            },
        )
        return {"status": "blocked", "reason": "warn_not_allowed"}

    run_log_writer(
        path=run_log_path or "docs/matrix/run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "event": "dispatch_started",
            "status": "running",
            "notes": "",
            "timestamp": _timestamp(),
        },
    )
    dispatch = dispatch_runner(job)
    run_log_writer(
        path=run_log_path or "docs/matrix/run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "event": "dispatch_finished",
            "status": dispatch["result_status"],
            "notes": dispatch.get("notes", ""),
            "timestamp": _timestamp(),
        },
    )

    result_status = dispatch["result_status"]
    if result_status in {"publish_ok", "publish_filtered"}:
        job["status"] = "done"
    else:
        job["status"] = "failed"
    job["notes"] = result_status
    _write_queue(queue_path, headers, rows, original_lines)
    if assignment_ledger_path and job.get("assignment_id", "").strip():
        assignment_status = "published" if result_status == "publish_ok" else "blocked"
        sync_assignment_terminal_state(
            assignment_ledger_path=assignment_ledger_path,
            assignment_id=job["assignment_id"],
            status=assignment_status,
            notes=result_status,
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "assignment_updated",
                "status": assignment_status,
                "notes": result_status,
                "timestamp": _timestamp(),
            },
        )

    ledger_writer(
        path=result_ledger_path or "docs/matrix/result-ledger.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "platform": job["platform"],
            "account_alias": job["account_alias"],
            "content_type": job["content_type"],
            "decision": "go",
            "result_status": result_status,
            "conflict_id": "",
            "jump_target": str(dispatch.get("jump_target", "")).strip(),
            "evidence": dispatch.get("evidence", ""),
            "notes": dispatch.get("notes", ""),
            "timestamp": _timestamp(),
        },
    )
    run_log_writer(
        path=run_log_path or "docs/matrix/run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "event": "ledger_updated",
            "status": result_status,
            "notes": dispatch.get("notes", ""),
            "timestamp": _timestamp(),
        },
    )

    if result_status == "publish_ok" and update_verification:
        verification_updater(
            path=verification_matrix_path or "docs/matrix/verification-matrix.md",
            row={
                "platform": job["platform"],
                "account_alias": job["account_alias"],
                "content_type": job["content_type"],
                "status": "real_publish_ok",
                "last_verified": _timestamp().split("T")[0],
                "evidence": dispatch.get("evidence", ""),
                "notes": dispatch.get("notes", ""),
            },
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "verification_updated",
                "status": "real_publish_ok",
                "notes": dispatch.get("notes", ""),
                "timestamp": _timestamp(),
            },
        )
    elif result_status == "publish_filtered" and update_verification:
        verification_updater(
            path=verification_matrix_path or "docs/matrix/verification-matrix.md",
            row={
                "platform": job["platform"],
                "account_alias": job["account_alias"],
                "content_type": job["content_type"],
                "status": "submit_ok_filtered",
                "last_verified": _timestamp().split("T")[0],
                "evidence": dispatch.get("evidence", ""),
                "notes": dispatch.get("notes", ""),
            },
        )
        run_log_writer(
            path=run_log_path or "docs/matrix/run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "event": "verification_updated",
                "status": "submit_ok_filtered",
                "notes": dispatch.get("notes", ""),
                "timestamp": _timestamp(),
            },
        )

    return {"status": job["status"], "reason": result_status}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the next pending job from docs/matrix/job-queue.md."
    )
    parser.add_argument(
        "--queue",
        default="docs/matrix/job-queue.md",
        help="Path to job queue markdown file.",
    )
    parser.add_argument(
        "--account-matrix",
        default="docs/matrix/account-matrix.md",
        help="Path to account matrix markdown file.",
    )
    parser.add_argument(
        "--verification-matrix",
        default="docs/matrix/verification-matrix.md",
        help="Path to verification matrix markdown file.",
    )
    parser.add_argument(
        "--result-ledger",
        default="docs/matrix/result-ledger.md",
        help="Path to result ledger markdown file.",
    )
    parser.add_argument(
        "--run-log",
        default="docs/matrix/run-log.md",
        help="Path to run log markdown file.",
    )
    parser.add_argument(
        "--assignment-ledger",
        default="docs/ops/content-assignment-ledger.md",
        help="Path to content assignment ledger markdown file.",
    )
    parser.add_argument(
        "--conflict-ledger",
        default="docs/ops/conflict-ledger.md",
        help="Path to conflict ledger markdown file.",
    )
    parser.add_argument(
        "--override-ledger",
        default="docs/ops/operator-override-ledger.md",
        help="Path to operator override ledger markdown file.",
    )
    parser.add_argument(
        "--allow-warn",
        action="store_true",
        help="Allow warn-level jobs to dispatch.",
    )
    parser.add_argument(
        "--dry-run-result-status",
        choices=[
            "publish_ok",
            "publish_filtered",
            "publish_failed",
            "runner_error",
        ],
        help="Use a fake dispatch result instead of calling the real dispatch path.",
    )
    parser.add_argument(
        "--dry-run-evidence",
        default="",
        help="Optional evidence string used together with --dry-run-result-status.",
    )
    parser.add_argument(
        "--dry-run-notes",
        default="",
        help="Optional notes string used together with --dry-run-result-status.",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    dispatch_runner = None
    if args.dry_run_result_status:
        def _dry_run_dispatch(_job: dict[str, Any]):
            return {
                "ok": args.dry_run_result_status in {"publish_ok", "publish_filtered"},
                "result_status": args.dry_run_result_status,
                "evidence": args.dry_run_evidence,
                "notes": args.dry_run_notes,
            }

        dispatch_runner = _dry_run_dispatch
    result = run_next_job(
        queue_path=args.queue,
        dispatch_runner=dispatch_runner,
        account_matrix_path=args.account_matrix,
        verification_matrix_path=args.verification_matrix,
        result_ledger_path=args.result_ledger,
        run_log_path=args.run_log,
        assignment_ledger_path=args.assignment_ledger,
        conflict_ledger_path=args.conflict_ledger,
        override_ledger_path=args.override_ledger,
        allow_warn=args.allow_warn,
        update_verification=not bool(args.dry_run_result_status),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
