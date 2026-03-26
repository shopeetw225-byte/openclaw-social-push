from __future__ import annotations


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _supports_job_type(node: dict[str, str], job_type: str) -> bool:
    capabilities = _split_csv(node.get("capabilities", ""))
    return job_type in capabilities


def _supports_platform(node: dict[str, str], platform: str) -> bool:
    platforms = _split_csv(node.get("platforms", ""))
    if not platforms:
        return True
    return platform in platforms or "*" in platforms


def _supports_account(node: dict[str, str], account_alias: str) -> bool:
    if not account_alias:
        return True
    aliases = _split_csv(node.get("account_aliases", ""))
    if not aliases:
        return True
    return account_alias in aliases or "*" in aliases


def _is_ready(node: dict[str, str]) -> bool:
    return node.get("status", "").strip().lower() == "ready"


def _is_local_agent(node: dict[str, str]) -> bool:
    mode = str(node.get("mode", "")).strip().lower()
    return mode in {"", "local_agent"}


def _score_candidate(
    node: dict[str, str],
    *,
    index: int,
    platform: str,
    account_alias: str,
    preferred_node: str,
) -> tuple[int, int, int, int]:
    node_id = node.get("node_id", "").strip()
    aliases = _split_csv(node.get("account_aliases", ""))
    platforms = _split_csv(node.get("platforms", ""))

    preferred_rank = 0 if preferred_node and node_id == preferred_node else 1
    alias_rank = 0 if account_alias and account_alias in aliases else 1
    exclusive_rank = 0 if platforms == [platform] else 1

    return (preferred_rank, alias_rank, exclusive_rank, index)


def select_worker(node_rows: list[dict[str, str]], job: dict[str, str]) -> dict[str, str]:
    job_type = job.get("job_type", "").strip()
    platform = job.get("platform", "").strip()
    account_alias = job.get("account_alias", "").strip()
    preferred_node = job.get("preferred_node", "").strip()

    candidates: list[tuple[tuple[int, int, int, int], dict[str, str]]] = []
    for index, node in enumerate(node_rows):
        if not _is_local_agent(node):
            continue
        if not _is_ready(node):
            continue
        if not _supports_job_type(node, job_type):
            continue
        if not _supports_platform(node, platform):
            continue
        if not _supports_account(node, account_alias):
            continue
        score = _score_candidate(
            node,
            index=index,
            platform=platform,
            account_alias=account_alias,
            preferred_node=preferred_node,
        )
        candidates.append((score, node))

    if not candidates:
        raise ValueError("no_ready_worker")

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]
