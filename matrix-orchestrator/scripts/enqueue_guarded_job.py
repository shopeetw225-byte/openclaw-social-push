from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from content_assignment_guard import (
    DuplicateContentError,
    record_conflict,
    reserve_assignment,
    sync_assignment_terminal_state,
)


def _load_script_module(script_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _cluster_enqueue_module():
    repo_root = SCRIPT_DIR.parents[1]
    script_path = (
        repo_root
        / "openclaw-cluster-orchestrator"
        / "scripts"
        / "enqueue_cluster_job.py"
    )
    return _load_script_module(script_path, "enqueue_cluster_job")


def _build_jump_target(assignment_ledger_path: str | Path, assignment_id: str) -> str:
    return f"{Path(assignment_ledger_path)}#{assignment_id}"


def enqueue_guarded_job(
    *,
    queue_path: str | Path,
    assignment_ledger_path: str | Path,
    conflict_ledger_path: str | Path,
    platform: str,
    account_alias: str,
    content_type: str,
    title: str,
    body: str = "",
    media_paths: list[str] | None = None,
    preferred_node: str = "",
    notes: str = "",
    submission_ref: str = "",
    job_id: str | None = None,
) -> dict[str, str]:
    cluster_module = _cluster_enqueue_module()
    _headers, rows, _original_lines = cluster_module._read_queue(queue_path)
    actual_job_id = job_id or cluster_module._next_job_id(rows)
    job_like = {
        "content_type": content_type,
        "title": title,
        "body": body,
        "media_paths": media_paths or [],
    }

    try:
        assignment = reserve_assignment(
            assignment_ledger_path=assignment_ledger_path,
            submission_ref=submission_ref,
            platform=platform,
            account_alias=account_alias,
            content_type=content_type,
            job_id=actual_job_id,
            notes="reserved_for_enqueue",
            job_like=job_like,
        )
    except DuplicateContentError as exc:
        existing_assignment = exc.existing_assignment
        record_conflict(
            conflict_ledger_path=conflict_ledger_path,
            assignment_id=existing_assignment.get("assignment_id", "").strip(),
            job_id="",
            attempt_no="",
            conflict_type="duplicate_content",
            summary=(
                "content fingerprint already reserved by "
                f"{existing_assignment.get('assignment_id', '').strip()}"
            ),
            requested_account=account_alias,
            observed_account=existing_assignment.get("account_alias", "").strip(),
            jump_target=_build_jump_target(
                assignment_ledger_path,
                existing_assignment.get("assignment_id", "").strip(),
            ),
            notes="blocked_at_ingress",
        )
        raise

    try:
        row = cluster_module.enqueue_cluster_job(
            queue_path=queue_path,
            platform=platform,
            account_alias=account_alias,
            content_type=content_type,
            title=title,
            body=body,
            media_paths=media_paths,
            assignment_id=assignment["assignment_id"],
            content_fingerprint=assignment["content_fingerprint"],
            preferred_node=preferred_node,
            notes=notes,
            job_id=actual_job_id,
        )
    except Exception:  # noqa: BLE001
        sync_assignment_terminal_state(
            assignment_ledger_path=assignment_ledger_path,
            assignment_id=assignment["assignment_id"],
            status="cancelled",
            notes="enqueue_failed",
        )
        raise

    sync_assignment_terminal_state(
        assignment_ledger_path=assignment_ledger_path,
        assignment_id=assignment["assignment_id"],
        status="queued",
        notes="ingress accepted",
    )
    return row


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reserve content assignment metadata before appending a cluster job."
    )
    parser.add_argument("--queue", default="docs/cluster/cluster-job-queue.md")
    parser.add_argument(
        "--assignment-ledger",
        default="docs/ops/content-assignment-ledger.md",
    )
    parser.add_argument(
        "--conflict-ledger",
        default="docs/ops/conflict-ledger.md",
    )
    parser.add_argument("--platform", required=True)
    parser.add_argument("--account-alias", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--media-path", action="append", default=[])
    parser.add_argument("--preferred-node", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--submission-ref", default="")
    parser.add_argument("--job-id")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    row = enqueue_guarded_job(
        queue_path=args.queue,
        assignment_ledger_path=args.assignment_ledger,
        conflict_ledger_path=args.conflict_ledger,
        platform=args.platform,
        account_alias=args.account_alias,
        content_type=args.content_type,
        title=args.title,
        body=args.body,
        media_paths=args.media_path,
        preferred_node=args.preferred_node,
        notes=args.notes,
        submission_ref=args.submission_ref,
        job_id=args.job_id,
    )
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
