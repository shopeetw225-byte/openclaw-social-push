# Verification Matrix Template

Use this file to record what has actually been verified for each account and content shape.

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

Evidence examples:

- published URL
- content id
- page screenshot path
- request result such as `POST /api/v4/content/publish = 200`

| platform | account_alias | content_type | status | last_verified | evidence | notes |
|---|---|---|---|---|---|---|
| `<zhihu>` | `<main>` | `<article>` | `<real_publish_ok>` | `<YYYY-MM-DD>` | `<url or request evidence>` | `<short note>` |
| `<reddit>` | `<main>` | `<image_post>` | `<submit_ok_filtered>` | `<YYYY-MM-DD>` | `<page text or request evidence>` | `<short note>` |
