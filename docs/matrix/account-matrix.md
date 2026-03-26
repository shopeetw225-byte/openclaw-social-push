# Account Matrix (Runtime)

Runtime account mapping for the orchestrator.

## Purpose

- Maps `platform + account_alias` to the browser identity used by runners.
- Provides deterministic defaults when multiple aliases exist for one platform.

Allowed `platform` values:

- `zhihu`
- `reddit`
- `x`
- `threads`
- `facebook`
- `xiaohongshu`
- `weibo`
- `wechat-official-account`
- `juejin`
- `instagram`

Allowed `default` values:

- `yes`
- `no`

| account_alias | platform | display_name | browser_profile | default | notes |
|---|---|---|---|---|---|
| main | zhihu | 嘤嘤嘤 | chrome-relay | yes | 知乎文章/想法已真实验证 |
| main | reddit | u/Fun_Supermarket9297 | chrome-relay | yes | 文本帖已真实验证，图帖提交流程已验证 |
| main | instagram | qiang8513 | chrome-relay | yes | 单图已真实验证 |
| main | threads | qiang8513 | chrome-relay | yes | 纯文字与单图已真实验证 |
