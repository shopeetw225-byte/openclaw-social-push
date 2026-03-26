from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable


Runner = Callable[[dict[str, Any]], dict[str, Any]]
ALLOWED_RESULT_STATUSES = {
    "publish_ok",
    "publish_filtered",
    "publish_failed",
    "runner_error",
}


def _normalize_payload(job: dict[str, Any]) -> dict[str, Any]:
    media_paths_raw = str(job.get("media_paths", "")).strip()
    media_paths = [item.strip() for item in media_paths_raw.split(",") if item.strip()]
    return {
        "job_id": str(job.get("job_id", "")).strip(),
        "attempt_no": str(job.get("attempt_no", "")).strip(),
        "platform": str(job.get("platform", "")).strip(),
        "account_alias": str(job.get("account_alias", "")).strip(),
        "content_type": str(job.get("content_type", "")).strip(),
        "title": str(job.get("title", "")).strip(),
        "body": str(job.get("body", "")).strip(),
        "media_paths": media_paths,
        "notes": str(job.get("notes", "")).strip(),
    }


def _build_prompt(payload: dict[str, Any]) -> str:
    media_paths = ", ".join(payload["media_paths"]) if payload["media_paths"] else "<none>"
    return (
        "Use $social-push to publish this job.\n\n"
        f"platform: {payload['platform']}\n"
        f"account_alias: {payload['account_alias']}\n"
        f"content_type: {payload['content_type']}\n"
        f"title: {payload['title']}\n"
        f"body: {payload['body']}\n"
        f"media_paths: {media_paths}\n"
        f"notes: {payload['notes']}\n\n"
        "Return JSON only with this exact shape:\n"
        '{"ok": true, "result_status": "publish_ok", "evidence": "", "notes": "", "jump_target": "", "observed_account": ""}\n'
        "Allowed result_status values: publish_ok, publish_filtered, publish_failed, runner_error.\n"
        "Use publish_filtered only when the content was actually submitted then filtered/removed.\n"
        "If you can observe the current page URL or another reliable locator, return it in jump_target.\n"
        "If you can observe the currently logged-in or visible account identity, return it in observed_account."
    )


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
    meta_container = envelope.get("result")
    if isinstance(meta_container, dict):
        meta = meta_container.get("meta")
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


def _parse_possible_json(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text) if raw_text else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _infer_result_status_from_text(payload_text: str) -> str:
    lowered = payload_text.lower()
    if "內容過濾器已移除此貼文" in payload_text:
        return "publish_filtered"
    if re.search(r"\bfiltered\s*:\s*(yes|true)\b", lowered):
        return "publish_filtered"

    failure_markers = [
        "publish_failed",
        "failure",
        "failed",
        "error",
        "unsupported",
        "not support",
        "does not support",
        "不支持",
        "未支持",
        "失败",
        "失敗",
        "无法",
    ]
    if re.search(r"\bfiltered\s*:\s*(no|false)\b", lowered):
        if any(marker in lowered for marker in failure_markers) or any(
            marker in payload_text for marker in ["不支持", "未支持", "失败", "失敗", "无法"]
        ):
            return "publish_failed"
        return "publish_failed"

    if "filtered" in lowered:
        return "publish_filtered"
    if any(marker in lowered for marker in failure_markers) or any(
        marker in payload_text for marker in ["不支持", "未支持", "失败", "失敗", "无法"]
    ):
        return "publish_failed"

    success_markers = [
        "publish_ok",
        "published successfully",
        "post shared",
        "发布成功",
        "發佈成功",
        "已发布",
        "已發佈",
        "真实发布成功",
        "real publish confirmed",
    ]
    if any(marker in lowered for marker in success_markers) or any(
        marker in payload_text for marker in ["发布成功", "發佈成功", "已发布", "已發佈", "真实发布成功"]
    ):
        return "publish_ok"

    if re.search(r"https?://", payload_text):
        return "publish_ok"

    return "publish_failed"


def _normalize_openclaw_result(stdout: str) -> dict[str, Any]:
    raw_stdout = stdout.strip()
    envelope = _parse_possible_json(raw_stdout)
    payload_text = _extract_payload_text(envelope, raw_stdout).strip()
    stop_reason = str(envelope.get("stopReason", "")).strip().lower()
    if stop_reason == "error":
        raise RuntimeError(payload_text or raw_stdout or "social-push dispatch failed")
    if envelope and str(envelope.get("status", "ok")).strip().lower() != "ok":
        detail = (
            str(envelope.get("summary", "")).strip()
            or str(envelope.get("error", "")).strip()
            or payload_text
            or raw_stdout
            or "social-push dispatch failed"
        )
        raise RuntimeError(detail)

    payload_json = _parse_possible_json(payload_text)

    result_status = str(payload_json.get("result_status", "")).strip()
    if result_status in ALLOWED_RESULT_STATUSES:
        evidence = str(payload_json.get("evidence", "")).strip() or payload_text
        notes = str(payload_json.get("notes", "")).strip()
        jump_target = str(payload_json.get("jump_target", "")).strip()
        observed_account = str(payload_json.get("observed_account", "")).strip()
        ok = bool(
            payload_json.get(
                "ok",
                result_status in {"publish_ok", "publish_filtered"},
            )
        )
        return {
            "ok": ok,
            "result_status": result_status,
            "evidence": evidence,
            "notes": notes,
            "jump_target": jump_target,
            "observed_account": observed_account,
        }

    result_status = _infer_result_status_from_text(payload_text)

    return {
        "ok": result_status in {"publish_ok", "publish_filtered"},
        "result_status": result_status,
        "evidence": payload_text,
        "notes": "",
    }


def _default_runner(payload: dict[str, Any]) -> dict[str, Any]:
    openclaw_bin = os.environ.get("OPENCLAW_BIN", f"{os.environ.get('HOME', '')}/.homebrew/bin/openclaw")
    openclaw_mode = os.environ.get("MATRIX_ORCHESTRATOR_OPENCLAW_MODE", "gateway").strip().lower()
    agent_id = os.environ.get("MATRIX_ORCHESTRATOR_OPENCLAW_AGENT", "main").strip() or "main"
    timeout_seconds = os.environ.get("MATRIX_ORCHESTRATOR_OPENCLAW_TIMEOUT", "600").strip() or "600"
    prompt = _build_prompt(payload)
    command = [openclaw_bin, "agent"]
    if openclaw_mode == "local":
        command.append("--local")

    session_id = os.environ.get("MATRIX_ORCHESTRATOR_OPENCLAW_SESSION_ID", "").strip()
    command.extend(["--json", "--agent", agent_id])
    if session_id and openclaw_mode != "local":
        command.extend(["--session-id", session_id])
    command.extend(["--timeout", timeout_seconds, "-m", prompt])

    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "social-push dispatch failed")

    envelope = _parse_possible_json(proc.stdout.strip())
    if envelope:
        stop_reason = _extract_stop_reason(envelope).lower()
        session_id = _extract_session_id(envelope)
        if stop_reason == "tooluse" and session_id:
            terminal = _wait_for_terminal_session_result(
                session_id=session_id,
                prompt=prompt,
                agent_id=agent_id,
                timeout_seconds=int(timeout_seconds),
            )
            if terminal["stop_reason"] in {"error", "aborted"}:
                raise RuntimeError(terminal["text"] or "social-push dispatch did not reach a terminal success state")
            return _normalize_openclaw_result(
                json.dumps(
                    {
                        "payloads": [{"text": terminal["text"]}],
                        "stopReason": terminal["stop_reason"],
                    },
                    ensure_ascii=False,
                )
            )

    return _normalize_openclaw_result(proc.stdout)


def dispatch_social_push(
    job: dict[str, Any], runner: Runner | None = None
) -> dict[str, Any]:
    payload = _normalize_payload(job)

    if runner is None:
        if os.environ.get("MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER") == "1":
            runner = _default_runner
        else:
            return {
                "ok": False,
                "result_status": "runner_error",
                "evidence": "",
                "notes": "social-push runner not configured",
                "jump_target": "",
                "observed_account": "",
                "payload": payload,
            }

    try:
        result = runner(payload)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "result_status": "runner_error",
            "evidence": "",
            "notes": str(exc),
            "jump_target": "",
            "observed_account": "",
            "payload": payload,
        }

    normalized = {
        "ok": bool(result.get("ok", False)),
        "result_status": str(result.get("result_status", "runner_error")),
        "evidence": str(result.get("evidence", "")),
        "notes": str(result.get("notes", "")),
        "jump_target": str(result.get("jump_target", "")),
        "observed_account": str(result.get("observed_account", "")),
        "payload": payload,
    }
    return normalized
