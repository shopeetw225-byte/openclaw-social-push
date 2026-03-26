# Verification Matrix (Runtime)

Runtime verification coverage for orchestrator preflight decisions.

## Scope Key

- Uniqueness key: `platform + account_alias + content_type`
- Preflight reads this matrix before dispatching jobs from `job-queue.md`.

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

Allowed `content_type` values:

- `article`
- `column`
- `idea`
- `text_post`
- `image_post`
- `link_post`
- `longform`
- `short_post`

Allowed `status` values:

- `workflow_only`
- `page_verified`
- `submit_ok`
- `real_publish_ok`
- `submit_ok_filtered`

| platform | account_alias | content_type | status | last_verified | evidence | notes |
|---|---|---|---|---|---|---|
| zhihu | main | article | real_publish_ok | 2026-03-23 | https://zhuanlan.zhihu.com/p/2019407805270995401 | 真实发布成功 |
| zhihu | main | idea | real_publish_ok | 2026-03-23 | POST /api/v4/content/publish = 200; GET /api/v4/pins/2019419989824782684 = 200 | 真实发布成功 |
| reddit | main | text_post | real_publish_ok | 2026-03-23 | r/test 帖流中出现新帖标题 OpenClaw Reddit test post via chrome-relay | 真实发布成功 |
| reddit | main | image_post | submit_ok_filtered | 2026-03-23 | 图帖提交后页面提示內容過濾器已移除此貼文 | 提交流程已验证，但在 r/test 被过滤 |
| reddit | main | link_post | workflow_only |  | references/Reddit帖子.md | workflow 已接入，未稳定完成真实验证 |
| instagram | main | image_post | real_publish_ok | 2026-03-19 | references/Instagram图文.md | 单图已真实验证 |
| threads | main | short_post | real_publish_ok | 2026-03-19 | references/Threads动态.md | 纯文字已真实验证 |
| threads | main | image_post | real_publish_ok | 2026-03-19 | references/Threads动态.md | 文字+单图已真实验证 |
