from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


ALLOWED_RESULT_STATUSES = {
    "preflight_blocked",
    "publish_ok",
    "publish_filtered",
    "publish_failed",
    "runner_error",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _node_matrix_dir(node_id: str) -> str:
    return str(_project_root() / "docs" / "nodes" / node_id / "matrix")


def _build_prompt(node: dict[str, str], payload: dict[str, Any]) -> str:
    node_id = str(node.get("node_id", "")).strip()
    runtime_dir = _node_matrix_dir(node_id)
    matrix_script = _project_root() / "matrix-orchestrator" / "scripts" / "run_next_job.py"
    media_paths = payload.get("media_paths", [])
    if isinstance(media_paths, list):
        media_text = ", ".join(str(item) for item in media_paths) if media_paths else "<none>"
    else:
        media_text = str(media_paths).strip() or "<none>"
    return (
        "Run exactly one pending node-local publish job and do not bypass matrix-orchestrator.\n\n"
        f"node_id: {node_id}\n"
        f"job_id: {str(payload.get('job_id', '')).strip()}\n"
        f"attempt_no: {str(payload.get('attempt_no', '')).strip()}\n"
        f"job_type: {str(payload.get('job_type', '')).strip()}\n"
        f"platform: {str(payload.get('platform', '')).strip()}\n"
        f"account_alias: {str(payload.get('account_alias', '')).strip()}\n"
        f"content_type: {str(payload.get('content_type', '')).strip()}\n"
        f"title: {str(payload.get('title', '')).strip()}\n"
        f"body: {str(payload.get('body', '')).strip()}\n"
        f"media_paths: {media_text}\n"
        f"cluster_notes: {str(payload.get('cluster_notes', '')).strip()}\n\n"
        "Run this exact command once and do not bypass matrix-orchestrator:\n"
        f"MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1 python3 {matrix_script} "
        f"--queue {runtime_dir}/job-queue.md "
        f"--account-matrix {runtime_dir}/account-matrix.md "
        f"--verification-matrix {runtime_dir}/verification-matrix.md "
        f"--result-ledger {runtime_dir}/result-ledger.md "
        f"--run-log {runtime_dir}/run-log.md "
        f"--assignment-ledger {_project_root() / 'docs' / 'ops' / 'content-assignment-ledger.md'} "
        f"--conflict-ledger {_project_root() / 'docs' / 'ops' / 'conflict-ledger.md'} "
        f"--override-ledger {_project_root() / 'docs' / 'ops' / 'operator-override-ledger.md'}\n\n"
        "Return JSON only with this exact shape:\n"
        '{"ok": true, "result_status": "publish_ok", "evidence": "", "notes": ""}\n'
        "Allowed result_status values: preflight_blocked, publish_ok, publish_filtered, publish_failed, runner_error."
    )


def _parse_possible_json(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text) if raw_text else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _extract_payload_text(envelope: dict[str, Any], fallback: str) -> str:
    payload_container = envelope.get("result")
    if not isinstance(payload_container, dict):
        payload_container = envelope
    payloads = payload_container.get("payloads")
    if not isinstance(payloads, list):
        return fallback
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("text", "")).strip()
        if text:
            return text
    return fallback


def _extract_stop_reason(envelope: dict[str, Any]) -> str:
    result = envelope.get("result")
    if isinstance(result, dict):
        stop_reason = str(result.get("stopReason", "")).strip()
        if stop_reason:
            return stop_reason
    return str(envelope.get("stopReason", "")).strip()


def _extract_session_id(envelope: dict[str, Any]) -> str:
    result = envelope.get("result")
    if isinstance(result, dict):
        meta = result.get("meta")
        if isinstance(meta, dict):
            agent_meta = meta.get("agentMeta")
            if isinstance(agent_meta, dict):
                session_id = str(agent_meta.get("sessionId", "")).strip()
                if session_id:
                    return session_id
    meta = envelope.get("meta")
    if isinstance(meta, dict):
        agent_meta = meta.get("agentMeta")
        if isinstance(agent_meta, dict):
            return str(agent_meta.get("sessionId", "")).strip()
    return ""


def _extract_text_blocks(content: Any) -> list[str]:
    if not isinstance(content, list):
        return []
    texts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = str(block.get("text", "")).strip()
        if text:
            texts.append(text)
    return texts


def _find_terminal_assistant_after_prompt(records: list[dict[str, Any]], prompt: str) -> dict[str, str] | None:
    prompt_index = -1
    for index, record in enumerate(records):
        if record.get("type") != "message":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        texts = _extract_text_blocks(message.get("content"))
        if any(prompt in text for text in texts):
            prompt_index = index
    if prompt_index == -1:
        return None

    for record in records[prompt_index + 1 :]:
        if record.get("type") != "message":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        stop_reason = str(message.get("stopReason", "")).strip()
        if stop_reason not in {"stop", "error", "aborted"}:
            continue
        texts = _extract_text_blocks(message.get("content"))
        return {
            "stop_reason": stop_reason,
            "text": texts[-1] if texts else "",
        }

    return None


def _wait_for_terminal_session_result(
    session_id: str,
    prompt: str,
    agent_id: str,
    timeout_seconds: int,
) -> dict[str, str]:
    session_path = Path.home() / ".openclaw" / "agents" / agent_id / "sessions" / f"{session_id}.jsonl"
    deadline = time.time() + max(timeout_seconds, 30)
    while time.time() < deadline:
        if session_path.exists():
            records: list[dict[str, Any]] = []
            for line in session_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            terminal = _find_terminal_assistant_after_prompt(records, prompt)
            if terminal is not None:
                return terminal
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for terminal session result for {session_id}")


def _normalize_worker_result(stdout: str) -> dict[str, Any]:
    raw_stdout = stdout.strip()
    envelope = _parse_possible_json(raw_stdout)
    payload_text = _extract_payload_text(envelope, raw_stdout).strip()
    stop_reason = _extract_stop_reason(envelope).lower()
    if stop_reason in {"error", "aborted"}:
        raise RuntimeError(payload_text or raw_stdout or "worker dispatch failed")
    if envelope and str(envelope.get("status", "ok")).strip().lower() != "ok":
        detail = (
            str(envelope.get("summary", "")).strip()
            or str(envelope.get("error", "")).strip()
            or payload_text
            or raw_stdout
            or "worker dispatch failed"
        )
        raise RuntimeError(detail)

    payload_json = _parse_possible_json(payload_text)
    result_status = str(payload_json.get("result_status", "")).strip()
    if result_status not in ALLOWED_RESULT_STATUSES:
        return {
            "ok": False,
            "result_status": "runner_error",
            "evidence": payload_text,
            "notes": "worker did not return terminal JSON result",
        }

    evidence = str(payload_json.get("evidence", "")).strip() or payload_text
    notes = str(payload_json.get("notes", "")).strip()
    ok = bool(payload_json.get("ok", result_status in {"publish_ok", "publish_filtered"}))
    return {
        "ok": ok,
        "result_status": result_status,
        "evidence": evidence,
        "notes": notes,
    }


def dispatch_to_worker(node: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    openclaw_bin = os.environ.get("OPENCLAW_BIN", f"{os.environ.get('HOME', '')}/.homebrew/bin/openclaw")
    agent_id = str(node.get("agent_id", "")).strip()
    timeout_seconds = int(os.environ.get("OPENCLAW_CLUSTER_OPENCLAW_TIMEOUT", "600").strip() or "600")
    prompt = _build_prompt(node, payload)
    command = [
        openclaw_bin,
        "agent",
        "--json",
        "--agent",
        agent_id,
        "--timeout",
        str(timeout_seconds),
        "-m",
        prompt,
    ]

    try:
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "result_status": "dispatch_error",
            "evidence": "",
            "notes": str(exc),
        }

    if proc.returncode != 0:
        return {
            "ok": False,
            "result_status": "dispatch_error",
            "evidence": "",
            "notes": proc.stderr.strip() or proc.stdout.strip() or "worker dispatch failed",
        }

    try:
        envelope = _parse_possible_json(proc.stdout.strip())
        if envelope:
            stop_reason = _extract_stop_reason(envelope).lower()
            session_id = _extract_session_id(envelope)
            if stop_reason == "tooluse" and session_id:
                terminal = _wait_for_terminal_session_result(
                    session_id=session_id,
                    prompt=prompt,
                    agent_id=agent_id,
                    timeout_seconds=timeout_seconds,
                )
                if terminal["stop_reason"] in {"error", "aborted"}:
                    raise RuntimeError(terminal["text"] or "worker did not reach a terminal success state")
                return _normalize_worker_result(
                    json.dumps(
                        {
                            "payloads": [{"text": terminal["text"]}],
                            "stopReason": terminal["stop_reason"],
                        },
                        ensure_ascii=False,
                    )
                )

        return _normalize_worker_result(proc.stdout)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "result_status": "dispatch_error",
            "evidence": "",
            "notes": str(exc),
        }
