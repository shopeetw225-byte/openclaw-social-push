# Account Matrix Sample

日期：2026-03-23

本文件是基于当前仓库中已记录的信息整理出的 **参考样例**，用于演示 `account-matrix` skill 产出的结构。

注意：

- 这是示例文件，不是运行时模板
- 未在仓库里明确记录的账号信息保持为 `<unknown>`
- 状态词遵循 `account-matrix` skill 中定义的固定 vocabulary
- `matrix-orchestrator` 的运行时数据应放在 `docs/matrix/`，不要直接把本样例当成运行文件使用

## Account Matrix

| account_alias | platform | display_name | browser_profile | default | notes |
|---|---|---|---|---|---|
| `<unknown>` | `instagram` | `qiang8513` | `chrome-relay` | `<unknown>` | 账号标识来自 `references/Instagram图文.md` 的实测记录 |
| `<unknown>` | `threads` | `qiang8513` | `chrome-relay` | `<unknown>` | 账号标识来自 `references/Threads动态.md` 的实测记录 |
| `<unknown>` | `x` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `facebook` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `xiaohongshu` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `weibo` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `wechat-official-account` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `juejin` | `<unknown>` | `chrome-relay` | `<unknown>` | 仓库中未记录具体账号显示名 |
| `<unknown>` | `reddit` | `<unknown>` | `chrome-relay` | `<unknown>` | 文本帖已真实验证，图帖提交流程已验证 |
| `<unknown>` | `zhihu` | `<unknown>` | `chrome-relay` | `<unknown>` | 文章与想法均已真实验证 |

## Verification Matrix

| platform | account_alias | content_type | status | last_verified | evidence | notes |
|---|---|---|---|---|---|---|
| `instagram` | `<unknown>` | `image_post` | `real_publish_ok` | `2026-03-19` | `references/Instagram图文.md` | 当前仓库只明确记录了单图实测 |
| `threads` | `<unknown>` | `short_post` | `real_publish_ok` | `2026-03-19` | `references/Threads动态.md` | 纯文字 Threads 已实测 |
| `threads` | `<unknown>` | `image_post` | `real_publish_ok` | `2026-03-19` | `references/Threads动态.md` | 文字 + 单图已实测 |
| `x` | `<unknown>` | `short_post` | `workflow_only` | `<unknown>` | `references/X推文.md` | workflow 已接入，未记录真实验证 |
| `facebook` | `<unknown>` | `short_post` | `workflow_only` | `<unknown>` | `references/Facebook动态.md` | workflow 已接入，未记录真实验证 |
| `facebook` | `<unknown>` | `image_post` | `workflow_only` | `<unknown>` | `references/Facebook动态.md` | workflow 已接入，未记录真实验证 |
| `xiaohongshu` | `<unknown>` | `longform` | `real_publish_ok` | `<unknown>` | `GUIDE.md` | 仓库写明“已实测”，但未记录更细证据 |
| `xiaohongshu` | `<unknown>` | `image_post` | `real_publish_ok` | `<unknown>` | `GUIDE.md` | 仓库写明“已实测”，但未记录更细证据 |
| `weibo` | `<unknown>` | `short_post` | `workflow_only` | `<unknown>` | `references/微博.md` | workflow 已接入，未记录真实验证 |
| `wechat-official-account` | `<unknown>` | `article` | `workflow_only` | `<unknown>` | `references/微信公众号文章.md` | workflow 已接入，未记录真实验证 |
| `juejin` | `<unknown>` | `article` | `workflow_only` | `<unknown>` | `references/掘金文章.md` | workflow 已接入，未记录真实验证 |
| `reddit` | `<unknown>` | `text_post` | `real_publish_ok` | `2026-03-23` | `references/Reddit帖子.md` | 文本帖真实发布成功 |
| `reddit` | `<unknown>` | `image_post` | `submit_ok_filtered` | `2026-03-23` | `references/Reddit帖子.md` | 图帖提交流程已验证，但在 `r/test` 上被内容过滤器移除 |
| `reddit` | `<unknown>` | `link_post` | `workflow_only` | `<unknown>` | `references/Reddit帖子.md` | 已接入 workflow，未拿到稳定真实验证 |
| `zhihu` | `<unknown>` | `article` | `real_publish_ok` | `2026-03-23` | `references/知乎文章.md` | 真实发布成功 |
| `zhihu` | `<unknown>` | `idea` | `real_publish_ok` | `2026-03-23` | `references/知乎想法.md` | 真实发布成功 |

## 备注

- 这份样例刻意保留 `<unknown>`，因为模板 skill 的目标是避免凭空臆测账号信息
- 如需把它变成你自己的正式账号台账，应在浏览器里核对每个平台的真实显示名后再填充
