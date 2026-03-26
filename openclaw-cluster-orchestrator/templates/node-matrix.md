# Node Matrix Template

Local worker inventory for `openclaw-cluster-orchestrator`.

Required columns:

- `node_id`
- `mode`
- `agent_id`
- `gateway_endpoint`
- `platforms`
- `account_aliases`
- `browser_profiles`
- `capabilities`
- `status`
- `notes`

Allowed `mode` values:

- `local_agent`
- `remote_gateway`

Allowed `status` values:

- `ready`
- `paused`
- `offline`

V1 notes:

- only `local_agent` is executable in V1
- `platforms`, `account_aliases`, and `capabilities` use comma-separated values
- empty `platforms` or `account_aliases` mean generic fallback coverage

| node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |
|---|---|---|---|---|---|---|---|---|---|
| `worker-zhihu-01` | `local_agent` | `publisher-zhihu` |  | `zhihu` | `main` | `chrome-relay` | `publish` | `ready` | `Zhihu publish worker` |
| `worker-reddit-01` | `local_agent` | `publisher-reddit` |  | `reddit` | `main` | `chrome-relay` | `publish` | `ready` | `Reddit publish worker` |
