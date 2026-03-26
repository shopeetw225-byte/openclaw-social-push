# Verification Matrix (Runtime)

Runtime verification coverage for node `worker-reddit-01`.

| platform | account_alias | content_type | status | last_verified | evidence | notes |
|---|---|---|---|---|---|---|
| reddit | main | text_post | real_publish_ok | 2026-03-23 | r/test 帖流中出现新帖标题 OpenClaw Reddit test post via chrome-relay | 真实发布成功 |
| reddit | main | image_post | submit_ok_filtered | 2026-03-23 | 图帖提交后页面提示內容過濾器已移除此貼文 | 提交流程已验证，但在 r/test 被过滤 |
| reddit | main | link_post | workflow_only |  | references/Reddit帖子.md | workflow 已接入，未稳定完成真实验证 |
