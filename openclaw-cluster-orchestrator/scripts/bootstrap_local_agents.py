from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _list_existing_agents(openclaw_bin: str) -> set[str]:
    proc = subprocess.run(
        [openclaw_bin, "agents", "list", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to list agents")
    try:
        parsed = json.loads(proc.stdout.strip() or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("failed to parse agents list json") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("agents list did not return a JSON array")
    return {
        str(item.get("id", "")).strip()
        for item in parsed
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


def bootstrap_local_agents(
    node_rows: list[dict[str, str]],
    *,
    workspace: str,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    openclaw_bin = os.environ.get("OPENCLAW_BIN", f"{os.environ.get('HOME', '')}/.homebrew/bin/openclaw")
    existing_agents = _list_existing_agents(openclaw_bin)

    created: list[str] = []
    skipped_existing: list[str] = []
    ignored_non_local: list[str] = []
    planned: list[str] = []

    for node in node_rows:
        mode = str(node.get("mode", "")).strip().lower()
        agent_id = str(node.get("agent_id", "")).strip()
        if not agent_id:
            continue
        if mode != "local_agent":
            ignored_non_local.append(agent_id)
            continue
        if agent_id in existing_agents:
            skipped_existing.append(agent_id)
            continue
        if dry_run:
            planned.append(agent_id)
            continue

        command = [
            openclaw_bin,
            "agents",
            "add",
            agent_id,
            "--workspace",
            workspace,
            "--model",
            "openai-official/gpt-5.4",
            "--non-interactive",
            "--json",
        ]
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"failed to add agent {agent_id}")
        created.append(agent_id)

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "ignored_non_local": ignored_non_local,
        "planned": planned,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create missing local worker agents from docs/cluster/node-matrix.md.")
    parser.add_argument("--node-matrix", default="docs/cluster/node-matrix.md")
    parser.add_argument("--workspace", default=f"{Path.home() / '.openclaw' / 'workspace'}")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    from load_node_matrix import load_node_matrix

    result = bootstrap_local_agents(
        load_node_matrix(args.node_matrix),
        workspace=args.workspace,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
