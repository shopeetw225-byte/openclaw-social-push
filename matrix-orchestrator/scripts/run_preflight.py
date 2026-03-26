from __future__ import annotations

import argparse
import json
from typing import Any


_GO_STATUSES = {"real_publish_ok"}
_WARN_STATUSES = {"submit_ok", "submit_ok_filtered"}
_BLOCK_STATUSES = {"page_verified", "workflow_only"}
_NON_BLOCKING_ASSIGNMENT_STATUSES = {"cancelled", "published"}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _normalize_task_inputs(task_inputs: dict[str, Any]) -> dict[str, str]:
    return {
        "platform": _normalize_text(task_inputs.get("platform")),
        "account_alias": _normalize_text(task_inputs.get("account_alias")),
        "content_type": _normalize_text(task_inputs.get("content_type")),
    }


def _match_rows(
    verification_rows: list[dict[str, Any]], normalized_task_inputs: dict[str, str]
) -> list[dict[str, Any]]:
    target_platform = normalized_task_inputs["platform"]
    target_account_alias = normalized_task_inputs["account_alias"]
    target_content_type = normalized_task_inputs["content_type"]

    matched_rows: list[dict[str, Any]] = []
    for row in verification_rows:
        if _normalize_text(row.get("platform")) != target_platform:
            continue
        if _normalize_text(row.get("account_alias")) != target_account_alias:
            continue
        row_content_type = _normalize_text(row.get("content_type"))
        if target_content_type and row_content_type and row_content_type != target_content_type:
            continue
        matched_rows.append(row)
    return matched_rows


def _find_assignment(
    assignment_rows: list[dict[str, Any]], assignment_id: str
) -> dict[str, Any] | None:
    for row in assignment_rows:
        if _normalize_text(row.get("assignment_id")) == assignment_id:
            return row
    return None


def _find_account_row(
    account_rows: list[dict[str, Any]], normalized_task_inputs: dict[str, str]
) -> dict[str, Any] | None:
    for row in account_rows:
        if _normalize_text(row.get("platform")) != normalized_task_inputs["platform"]:
            continue
        if _normalize_text(row.get("account_alias")) != normalized_task_inputs["account_alias"]:
            continue
        return row
    return None


def _find_existing_conflict(
    conflict_rows: list[dict[str, Any]],
    *,
    assignment_id: str,
    job_id: str,
    attempt_no: str,
    conflict_type: str,
) -> dict[str, Any] | None:
    for row in reversed(conflict_rows):
        if _normalize_text(row.get("assignment_id")) != assignment_id:
            continue
        if _normalize_text(row.get("job_id")) != job_id:
            continue
        if _normalize_text(row.get("attempt_no")) != attempt_no:
            continue
        if _normalize_text(row.get("conflict_type")) != conflict_type:
            continue
        return row
    return None


def _find_matching_override(
    override_rows: list[dict[str, Any]],
    *,
    conflict_id: str,
    job_id: str,
    attempt_no: str,
) -> dict[str, Any] | None:
    for row in reversed(override_rows):
        if _normalize_text(row.get("conflict_id")) != conflict_id:
            continue
        if _normalize_text(row.get("job_id")) != job_id:
            continue
        if _normalize_text(row.get("attempt_no")) != attempt_no:
            continue
        if _normalize_text(row.get("action")) != "continue_once":
            continue
        return row
    return None


def _guard_result(
    *,
    normalized_task_inputs: dict[str, str],
    conflict_type: str,
    summary: str,
    requested_account: str = "",
    observed_account: str = "",
    jump_target: str = "",
    conflict_rows: list[dict[str, Any]],
    override_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    assignment_id = _normalize_text(normalized_task_inputs.get("assignment_id"))
    job_id = _normalize_text(normalized_task_inputs.get("job_id"))
    attempt_no = _normalize_text(normalized_task_inputs.get("attempt_no"))
    existing_conflict = _find_existing_conflict(
        conflict_rows,
        assignment_id=assignment_id,
        job_id=job_id,
        attempt_no=attempt_no,
        conflict_type=conflict_type,
    )
    conflict_id = ""
    if existing_conflict is not None:
        conflict_id = str(existing_conflict.get("conflict_id", "")).strip()
        if not jump_target:
            jump_target = str(existing_conflict.get("jump_target", "")).strip()
        override = _find_matching_override(
            override_rows,
            conflict_id=conflict_id,
            job_id=job_id,
            attempt_no=attempt_no,
        )
        if override is not None:
            return {
                "decision": "go",
                "reason": "continue_once",
                "conflict_type": conflict_type,
                "conflict_id": conflict_id,
                "summary": summary,
                "requested_account": requested_account,
                "observed_account": observed_account,
                "jump_target": jump_target,
            }
    return {
        "decision": "block",
        "reason": conflict_type,
        "conflict_type": conflict_type,
        "conflict_id": conflict_id,
        "summary": summary,
        "requested_account": requested_account,
        "observed_account": observed_account,
        "jump_target": jump_target,
    }


def run_preflight(
    verification_rows: list[dict[str, Any]],
    task_inputs: dict[str, Any],
    assignment_rows: list[dict[str, Any]] | None = None,
    account_rows: list[dict[str, Any]] | None = None,
    conflict_rows: list[dict[str, Any]] | None = None,
    override_rows: list[dict[str, Any]] | None = None,
    allow_warn: bool = False,
) -> dict[str, Any]:
    normalized_task_inputs = _normalize_task_inputs(task_inputs)
    normalized_task_inputs.update(
        {
            "job_id": _normalize_text(task_inputs.get("job_id")),
            "attempt_no": _normalize_text(task_inputs.get("attempt_no")),
            "assignment_id": _normalize_text(task_inputs.get("assignment_id")),
            "content_fingerprint": _normalize_text(task_inputs.get("content_fingerprint")),
            "observed_account": _normalize_text(task_inputs.get("observed_account")),
            "jump_target": str(task_inputs.get("jump_target", "")).strip(),
        }
    )
    matched_rows = _match_rows(verification_rows, normalized_task_inputs)

    if not matched_rows:
        return {
            "decision": "block",
            "reason": "missing_verification_row",
            "matched_rows": [],
            "normalized_task_inputs": normalized_task_inputs,
        }

    assignment_rows = assignment_rows or []
    account_rows = account_rows or []
    conflict_rows = conflict_rows or []
    override_rows = override_rows or []
    assignment_id = normalized_task_inputs["assignment_id"]
    if assignment_rows and assignment_id:
        assignment = _find_assignment(assignment_rows, assignment_id)
        if assignment is None:
            return {
                "decision": "block",
                "reason": "missing_assignment_row",
                "matched_rows": matched_rows,
                "normalized_task_inputs": normalized_task_inputs,
            }

        assignment_account_alias = _normalize_text(assignment.get("account_alias"))
        if assignment_account_alias != normalized_task_inputs["account_alias"]:
            result = _guard_result(
                normalized_task_inputs=normalized_task_inputs,
                conflict_type="target_account_mismatch",
                summary="job account alias does not match assignment target account",
                requested_account=str(task_inputs.get("account_alias", "")).strip(),
                observed_account=str(assignment.get("account_alias", "")).strip(),
                jump_target=str(task_inputs.get("jump_target", "")).strip(),
                conflict_rows=conflict_rows,
                override_rows=override_rows,
            )
            result.update(
                {
                    "matched_rows": matched_rows,
                    "normalized_task_inputs": normalized_task_inputs,
                }
            )
            return result

        content_fingerprint = normalized_task_inputs["content_fingerprint"]
        if content_fingerprint:
            for row in assignment_rows:
                if _normalize_text(row.get("assignment_id")) == assignment_id:
                    continue
                if _normalize_text(row.get("content_fingerprint")) != content_fingerprint:
                    continue
                if _normalize_text(row.get("status")) in _NON_BLOCKING_ASSIGNMENT_STATUSES:
                    continue
                result = _guard_result(
                    normalized_task_inputs=normalized_task_inputs,
                    conflict_type="duplicate_content",
                    summary=(
                        "content fingerprint already reserved by "
                        f"{str(row.get('assignment_id', '')).strip()}"
                    ),
                    requested_account=str(task_inputs.get("account_alias", "")).strip(),
                    observed_account=str(row.get("account_alias", "")).strip(),
                    jump_target=str(task_inputs.get("jump_target", "")).strip(),
                    conflict_rows=conflict_rows,
                    override_rows=override_rows,
                )
                result.update(
                    {
                        "matched_rows": matched_rows,
                        "normalized_task_inputs": normalized_task_inputs,
                    }
                )
                return result

    observed_account = normalized_task_inputs["observed_account"]
    if account_rows and observed_account:
        account_row = _find_account_row(account_rows, normalized_task_inputs)
        expected_display_name = (
            _normalize_text(account_row.get("display_name")) if account_row else ""
        )
        if expected_display_name and expected_display_name != observed_account:
            result = _guard_result(
                normalized_task_inputs=normalized_task_inputs,
                conflict_type="browser_identity_mismatch",
                summary="observed browser identity does not match account matrix display name",
                requested_account=str(task_inputs.get("account_alias", "")).strip(),
                observed_account=str(task_inputs.get("observed_account", "")).strip(),
                jump_target=str(task_inputs.get("jump_target", "")).strip(),
                conflict_rows=conflict_rows,
                override_rows=override_rows,
            )
            result.update(
                {
                    "matched_rows": matched_rows,
                    "normalized_task_inputs": normalized_task_inputs,
                }
            )
            return result

    status = _normalize_text(
        matched_rows[0].get("preflight_status", matched_rows[0].get("status"))
    )
    if status in _GO_STATUSES:
        decision = "go"
        reason = status
    elif status in _WARN_STATUSES:
        if allow_warn:
            decision = "go"
            reason = "warn_allowed"
        else:
            decision = "warn"
            reason = status
    elif status in _BLOCK_STATUSES:
        decision = "block"
        reason = status
    else:
        decision = "block"
        reason = "unknown_preflight_status"

    return {
        "decision": decision,
        "reason": reason,
        "matched_rows": matched_rows,
        "normalized_task_inputs": normalized_task_inputs,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run matrix-orchestrator preflight on one job payload."
    )
    parser.add_argument(
        "--job-json",
        required=True,
        help="JSON object containing at least platform, account_alias, and content_type.",
    )
    parser.add_argument(
        "--verification-matrix",
        default="docs/matrix/verification-matrix.md",
        help="Path to verification matrix markdown file.",
    )
    parser.add_argument(
        "--allow-warn",
        action="store_true",
        help="Promote warn results to go when explicitly allowed.",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    loader_path = Path(__file__).resolve().parent / "load_markdown_table.py"
    spec = spec_from_file_location("load_markdown_table", loader_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    job = json.loads(args.job_json)
    verification_rows = module.load_markdown_table(args.verification_matrix)
    result = run_preflight(
        verification_rows=verification_rows,
        task_inputs=job,
        allow_warn=args.allow_warn,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
