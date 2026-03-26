# Node Matrix (Runtime)

Runtime worker inventory for `openclaw-cluster-orchestrator`.

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

| node_id | mode | agent_id | gateway_endpoint | platforms | account_aliases | browser_profiles | capabilities | status | notes |
|---|---|---|---|---|---|---|---|---|---|
| worker-zhihu-01 | local_agent | publisher-zhihu |  | zhihu | main | chrome-relay | publish | ready | Zhihu main account worker |
| worker-reddit-01 | local_agent | publisher-reddit |  | reddit | main | chrome-relay | publish | ready | Reddit main account worker |
| worker-fallback-01 | local_agent | publisher-fallback |  | zhihu,reddit |  | chrome-relay | publish | paused | Generic fallback worker kept disabled in V1 |
