from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable


ProbeRunner = Callable[[str, str], dict[str, Any]]


def _default_runner(browser_profile: str, platform: str) -> dict[str, Any]:
    openclaw_bin = os.environ.get("OPENCLAW_BIN", f"{os.environ.get('HOME', '')}/.homebrew/bin/openclaw")
    script = (
        "() => {"
        " const pick = (items) => items.map((item) => (item?.textContent || item?.getAttribute?.('aria-label') || '')"
        "   .replace(/\\s+/g, ' ').trim()).filter(Boolean).slice(0, 80);"
        " return {"
        "   url: location.href,"
        "   title: document.title || '',"
        "   text: (document.body?.innerText || '').slice(0, 4000),"
        "   candidates: pick(Array.from(document.querySelectorAll('header a, header button, nav a, nav button, [role=\"button\"], a[href*=\"/@\"], a[href*=\"/user/\"], a[href*=\"/u/\"]')))"
        " };"
        "}"
    )
    command = [
        openclaw_bin,
        "browser",
        "--browser-profile",
        browser_profile,
        "evaluate",
        "--fn",
        script,
    ]
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "browser_probe_failed")
    try:
        parsed = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"browser_probe_invalid_json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("browser_probe_invalid_payload")
    return parsed


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _detect_not_logged_in(url: str, text: str, title: str) -> bool:
    haystack = " ".join([url.lower(), text.lower(), title.lower()])
    patterns = [
        "signin",
        "sign in",
        "log in",
        "login",
        "登录",
        "登入",
        "注册",
    ]
    return any(pattern in haystack for pattern in patterns)


def _extract_reddit_account(texts: list[str]) -> str:
    joined = " ".join(texts)
    match = re.search(r"\bu/[A-Za-z0-9_-]+\b", joined)
    return match.group(0) if match else ""


def _extract_handle_account(texts: list[str]) -> str:
    joined = " ".join(texts)
    match = re.search(r"@[A-Za-z0-9._-]+", joined)
    return match.group(0) if match else ""


def probe_browser_identity(
    *,
    platform: str,
    expected_display_name: str,
    browser_profile: str,
    runner: ProbeRunner | None = None,
) -> dict[str, str]:
    active_runner = runner or _default_runner
    try:
        raw = active_runner(browser_profile, platform)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "probe_error",
            "observed_account": "",
            "jump_target": "",
            "notes": str(exc),
        }

    url = _normalize(str(raw.get("url", "")))
    title = _normalize(str(raw.get("title", "")))
    text = _normalize(str(raw.get("text", "")))
    candidates_raw = raw.get("candidates", [])
    candidates = [
        _normalize(str(item))
        for item in candidates_raw
        if _normalize(str(item))
    ] if isinstance(candidates_raw, list) else []
    texts = [title, text, *candidates]
    expected = _normalize(expected_display_name)

    if _detect_not_logged_in(url, text, title):
        return {
            "status": "not_logged_in",
            "observed_account": "not_logged_in",
            "jump_target": url,
            "notes": "",
        }

    if expected and any(expected in chunk for chunk in texts):
        return {
            "status": "ok",
            "observed_account": expected_display_name,
            "jump_target": url,
            "notes": "",
        }

    observed_account = ""
    normalized_platform = _normalize(platform).lower()
    if normalized_platform == "reddit":
        observed_account = _extract_reddit_account(texts)
    elif normalized_platform in {"instagram", "threads", "x", "facebook"}:
        observed_account = _extract_handle_account(texts)

    return {
        "status": "ok" if observed_account else "unknown",
        "observed_account": observed_account,
        "jump_target": url,
        "notes": "",
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe current browser identity for a platform/account pair.")
    parser.add_argument("--platform", required=True)
    parser.add_argument("--expected-display-name", required=True)
    parser.add_argument("--browser-profile", default="chrome-relay")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    result = probe_browser_identity(
        platform=args.platform,
        expected_display_name=args.expected_display_name,
        browser_profile=args.browser_profile,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
