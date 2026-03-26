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

from cluster_markdown_utils import format_markdown_row, split_markdown_row


def _load_script_module(script_name: str, module_name: str):
    script_path = SCRIPT_DIR / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_table(path: str | Path) -> tuple[list[str], list[dict[str, str]], list[str]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    table_header_index = -1
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and "|" in lines[idx + 1]:
            table_header_index = idx
            break
    if table_header_index == -1:
        raise ValueError("Queue file must contain a markdown table.")
    headers = split_markdown_row(lines[table_header_index])
    rows: list[dict[str, str]] = []
    for line in lines[table_header_index + 2 :]:
        if "|" not in line:
            break
        cells = split_markdown_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append({header: cells[i] for i, header in enumerate(headers)})
    return headers, rows, lines


def _write_table(path: str | Path, headers: list[str], rows: list[dict[str, str]], original_lines: list[str]) -> None:
    output_path = Path(path)
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
    output_path.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")


def _find_first_pending(rows: list[dict[str, str]]) -> int | None:
    for idx, row in enumerate(rows):
        if row.get("status", "").strip() == "pending":
            return idx
    return None


def _parse_payload_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _append_node_local_job(node_runtime_root: str | Path, node_id: str, cluster_row: dict[str, str]) -> None:
    queue_path = Path(node_runtime_root) / node_id / "matrix" / "job-queue.md"
    headers, rows, original_lines = _read_table(queue_path)
    payload = _parse_payload_json(cluster_row.get("payload_json", ""))
    media_paths = payload.get("media_paths", [])
    media_text = ",".join(str(item).strip() for item in media_paths if str(item).strip()) if isinstance(media_paths, list) else str(media_paths).strip()
    rows.append(
        {
            "job_id": cluster_row["job_id"],
            "attempt_no": cluster_row["attempt_no"],
            "platform": cluster_row["platform"],
            "account_alias": cluster_row["account_alias"],
            "content_type": cluster_row["content_type"],
            "title": str(payload.get("title", "")).strip(),
            "body": str(payload.get("body", "")).strip(),
            "media_paths": media_text,
            "assignment_id": cluster_row.get("assignment_id", "").strip(),
            "content_fingerprint": cluster_row.get("content_fingerprint", "").strip(),
            "status": "pending",
            "notes": "routed_from_cluster",
        }
    )
    _write_table(queue_path, headers, rows, original_lines)


def _cluster_payload(cluster_row: dict[str, str], node_id: str) -> dict[str, Any]:
    payload = _parse_payload_json(cluster_row.get("payload_json", ""))
    media_paths = payload.get("media_paths", [])
    if not isinstance(media_paths, list):
        media_paths = [item.strip() for item in str(media_paths).split(",") if item.strip()]
    return {
        "job_id": cluster_row.get("job_id", "").strip(),
        "attempt_no": cluster_row.get("attempt_no", "").strip(),
        "node_id": node_id,
        "job_type": cluster_row.get("job_type", "").strip(),
        "platform": cluster_row.get("platform", "").strip(),
        "account_alias": cluster_row.get("account_alias", "").strip(),
        "content_type": cluster_row.get("content_type", "").strip(),
        "assignment_id": cluster_row.get("assignment_id", "").strip(),
        "content_fingerprint": cluster_row.get("content_fingerprint", "").strip(),
        "title": str(payload.get("title", "")).strip(),
        "body": str(payload.get("body", "")).strip(),
        "media_paths": media_paths,
        "preferred_node": cluster_row.get("preferred_node", "").strip(),
        "cluster_notes": cluster_row.get("notes", "").strip(),
    }


def _finalize_dispatch_error(
    *,
    headers: list[str],
    rows: list[dict[str, str]],
    original_lines: list[str],
    queue_path: str | Path,
    cluster_result_ledger_path: str | Path | None,
    cluster_run_log_path: str | Path | None,
    ledger_writer: Callable[..., Any],
    run_log_writer: Callable[..., Any],
    job: dict[str, str],
    node_id: str,
    agent_id: str,
    notes: str,
) -> dict[str, Any]:
    job["status"] = "failed"
    job["notes"] = "dispatch_error"
    _write_table(queue_path, headers, rows, original_lines)
    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "dispatch_finished",
            "status": "dispatch_error",
            "notes": notes,
            "timestamp": _timestamp(),
        },
    )
    ledger_writer(
        path=cluster_result_ledger_path or "docs/cluster/cluster-result-ledger.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "agent_id": agent_id,
            "job_type": job["job_type"],
            "result_status": "dispatch_error",
            "evidence": "",
            "notes": notes,
            "timestamp": _timestamp(),
        },
    )
    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "ledger_updated",
            "status": "dispatch_error",
            "notes": notes,
            "timestamp": _timestamp(),
        },
    )
    return {"status": "failed", "reason": "dispatch_error"}


def run_next_cluster_job(
    queue_path: str | Path,
    node_matrix_rows: list[dict[str, str]] | None = None,
    dispatch_runner: Callable[[dict[str, str], dict[str, Any]], dict[str, Any]] | None = None,
    ledger_writer: Callable[..., Any] | None = None,
    run_log_writer: Callable[..., Any] | None = None,
    node_runtime_root: str | Path = "docs/nodes",
    node_matrix_path: str | Path | None = None,
    cluster_result_ledger_path: str | Path | None = None,
    cluster_run_log_path: str | Path | None = None,
    dry_run_result_status: str | None = None,
    dry_run_evidence: str = "",
    dry_run_notes: str = "",
) -> dict[str, Any]:
    if node_matrix_rows is None:
        loader_module = _load_script_module("load_node_matrix.py", "load_node_matrix")
        node_matrix_rows = loader_module.load_node_matrix(node_matrix_path or "docs/cluster/node-matrix.md")
    if dispatch_runner is None:
        if dry_run_result_status:
            def _dry_run_dispatch(_node: dict[str, str], _payload: dict[str, Any]):
                return {
                    "ok": dry_run_result_status in {"publish_ok", "publish_filtered"},
                    "result_status": dry_run_result_status,
                    "evidence": dry_run_evidence,
                    "notes": dry_run_notes,
                }
            dispatch_runner = _dry_run_dispatch
        else:
            dispatch_module = _load_script_module("dispatch_to_worker.py", "dispatch_to_worker")
            dispatch_runner = dispatch_module.dispatch_to_worker
    if ledger_writer is None:
        ledger_module = _load_script_module("append_cluster_result_ledger.py", "append_cluster_result_ledger")
        ledger_writer = ledger_module.append_cluster_result_ledger
    if run_log_writer is None:
        run_log_module = _load_script_module("append_cluster_run_log.py", "append_cluster_run_log")
        run_log_writer = run_log_module.append_cluster_run_log
    selector_module = _load_script_module("select_worker.py", "select_worker")

    headers, rows, original_lines = _read_table(queue_path)
    if any(row.get("status", "").strip() == "running" for row in rows):
        return {"status": "blocked", "reason": "running_job_exists"}

    pending_index = _find_first_pending(rows)
    if pending_index is None:
        return {"status": "blocked", "reason": "no_pending_job"}

    job = rows[pending_index]
    job["status"] = "routing"
    _write_table(queue_path, headers, rows, original_lines)
    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": "",
            "event": "job_started",
            "status": "ok",
            "notes": "",
            "timestamp": _timestamp(),
        },
    )

    if job.get("job_type", "").strip() != "publish":
        job["status"] = "blocked"
        job["notes"] = "unsupported_job_type"
        _write_table(queue_path, headers, rows, original_lines)
        ledger_writer(
            path=cluster_result_ledger_path or "docs/cluster/cluster-result-ledger.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "node_id": "",
                "agent_id": "",
                "job_type": job["job_type"],
                "result_status": "routing_blocked",
                "evidence": "",
                "notes": "unsupported_job_type",
                "timestamp": _timestamp(),
            },
        )
        run_log_writer(
            path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "node_id": "",
                "event": "ledger_updated",
                "status": "routing_blocked",
                "notes": "unsupported_job_type",
                "timestamp": _timestamp(),
            },
        )
        return {"status": "blocked", "reason": "unsupported_job_type"}

    try:
        worker = selector_module.select_worker(node_matrix_rows, job)
    except ValueError as exc:
        job["status"] = "blocked"
        job["notes"] = str(exc)
        _write_table(queue_path, headers, rows, original_lines)
        ledger_writer(
            path=cluster_result_ledger_path or "docs/cluster/cluster-result-ledger.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "node_id": "",
                "agent_id": "",
                "job_type": job["job_type"],
                "result_status": "routing_blocked",
                "evidence": "",
                "notes": str(exc),
                "timestamp": _timestamp(),
            },
        )
        run_log_writer(
            path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
            row={
                "job_id": job["job_id"],
                "attempt_no": job["attempt_no"],
                "node_id": "",
                "event": "ledger_updated",
                "status": "routing_blocked",
                "notes": str(exc),
                "timestamp": _timestamp(),
            },
        )
        return {"status": "blocked", "reason": str(exc)}

    node_id = worker.get("node_id", "").strip()
    agent_id = worker.get("agent_id", "").strip()
    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "worker_selected",
            "status": "ok",
            "notes": agent_id,
            "timestamp": _timestamp(),
        },
    )

    try:
        _append_node_local_job(node_runtime_root, node_id, job)
    except Exception as exc:
        return _finalize_dispatch_error(
            headers=headers,
            rows=rows,
            original_lines=original_lines,
            queue_path=queue_path,
            cluster_result_ledger_path=cluster_result_ledger_path,
            cluster_run_log_path=cluster_run_log_path,
            ledger_writer=ledger_writer,
            run_log_writer=run_log_writer,
            job=job,
            node_id=node_id,
            agent_id=agent_id,
            notes=f"worker_runtime_error: {exc}",
        )

    job["status"] = "running"
    job["notes"] = worker.get("node_id", "").strip()
    _write_table(queue_path, headers, rows, original_lines)

    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "dispatch_started",
            "status": "running",
            "notes": agent_id,
            "timestamp": _timestamp(),
        },
    )

    payload = _cluster_payload(job, node_id)
    try:
        dispatch = dispatch_runner(worker, payload)
    except Exception as exc:
        return _finalize_dispatch_error(
            headers=headers,
            rows=rows,
            original_lines=original_lines,
            queue_path=queue_path,
            cluster_result_ledger_path=cluster_result_ledger_path,
            cluster_run_log_path=cluster_run_log_path,
            ledger_writer=ledger_writer,
            run_log_writer=run_log_writer,
            job=job,
            node_id=node_id,
            agent_id=agent_id,
            notes=f"worker_runtime_error: {exc}",
        )

    result_status = str(dispatch.get("result_status", "dispatch_error")).strip()
    if result_status in {"publish_ok", "publish_filtered"}:
        job["status"] = "done"
    elif result_status in {"preflight_blocked"}:
        job["status"] = "blocked"
    else:
        job["status"] = "failed"
    job["notes"] = result_status
    _write_table(queue_path, headers, rows, original_lines)

    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "dispatch_finished",
            "status": result_status,
            "notes": str(dispatch.get("notes", "")),
            "timestamp": _timestamp(),
        },
    )

    ledger_writer(
        path=cluster_result_ledger_path or "docs/cluster/cluster-result-ledger.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "agent_id": agent_id,
            "job_type": job["job_type"],
            "result_status": result_status,
            "evidence": str(dispatch.get("evidence", "")),
            "notes": str(dispatch.get("notes", "")),
            "timestamp": _timestamp(),
        },
    )
    run_log_writer(
        path=cluster_run_log_path or "docs/cluster/cluster-run-log.md",
        row={
            "job_id": job["job_id"],
            "attempt_no": job["attempt_no"],
            "node_id": node_id,
            "event": "ledger_updated",
            "status": result_status,
            "notes": str(dispatch.get("notes", "")),
            "timestamp": _timestamp(),
        },
    )

    return {"status": job["status"], "reason": result_status}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the next pending cluster job from docs/cluster/cluster-job-queue.md.")
    parser.add_argument("--queue", default="docs/cluster/cluster-job-queue.md")
    parser.add_argument("--node-matrix", default="docs/cluster/node-matrix.md")
    parser.add_argument("--result-ledger", default="docs/cluster/cluster-result-ledger.md")
    parser.add_argument("--run-log", default="docs/cluster/cluster-run-log.md")
    parser.add_argument("--node-runtime-root", default="docs/nodes")
    parser.add_argument(
        "--dry-run-result-status",
        choices=[
            "preflight_blocked",
            "publish_ok",
            "publish_filtered",
            "publish_failed",
            "runner_error",
        ],
    )
    parser.add_argument("--dry-run-evidence", default="")
    parser.add_argument("--dry-run-notes", default="")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    dispatch_runner = None
    if args.dry_run_result_status:
        def _dry_run_dispatch(_node: dict[str, str], _payload: dict[str, Any]):
            return {
                "ok": args.dry_run_result_status in {"publish_ok", "publish_filtered"},
                "result_status": args.dry_run_result_status,
                "evidence": args.dry_run_evidence,
                "notes": args.dry_run_notes,
            }
        dispatch_runner = _dry_run_dispatch
    result = run_next_cluster_job(
        queue_path=args.queue,
        dispatch_runner=dispatch_runner,
        node_matrix_path=args.node_matrix,
        cluster_result_ledger_path=args.result_ledger,
        cluster_run_log_path=args.run_log,
        node_runtime_root=args.node_runtime_root,
        dry_run_result_status=args.dry_run_result_status,
        dry_run_evidence=args.dry_run_evidence,
        dry_run_notes=args.dry_run_notes,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
