# Account Matrix Template

Use this file to track which account should be used for which platform.

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

Suggested `account_alias` values:

- `main`
- `alt`
- `brand`
- `test`

Guidelines:

- `display_name` should match what is visible in the browser UI
- `browser_profile` should describe how the browser session is controlled, such as `chrome-relay`
- `default` should be `yes` or `no`
- Keep `notes` factual and short

| account_alias | platform | display_name | browser_profile | default | notes |
|---|---|---|---|---|---|
| `<main>` | `<zhihu>` | `<visible browser name>` | `<chrome-relay>` | `<yes>` | `<optional note>` |
| `<alt>` | `<reddit>` | `<visible browser name>` | `<chrome-relay>` | `<no>` | `<optional note>` |
