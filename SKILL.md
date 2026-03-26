---
name: social-push
description: "Use when the user wants to publish content to Instagram, Threads, X/Twitter, Facebook, Xiaohongshu, Weibo, WeChat Official Accounts, Juejin, Reddit, or Zhihu (article/column and idea) through OpenClaw's native browser automation while reusing the login state from their regular Chrome or Chromium browser. Prefer the `chrome-relay` extension relay profile, stage local uploads into `/tmp/openclaw/uploads`, and use the isolated `openclaw` browser only as an explicit fallback."
metadata:
  {
    "openclaw": {
      "emoji": "📣",
      "requires": { "bins": [] }
    }
  }
---

# social-push

使用 OpenClaw 原生 browser CLI 直接完成发布。默认固定优先 `--browser-profile chrome-relay`，通过 OpenClaw Browser Relay 扩展接管你正在使用的浏览器标签页，从而复用真实登录态。

## 伴生 Skills

本仓库不仅包含 `social-push` 本身，还把账号治理与调度层打包在同一个 repo：

- `account-matrix/`
  - 负责账号矩阵、验证矩阵与发布前 checklist 模板
- `matrix-orchestrator/`
  - 负责读取 `docs/matrix/` 的运行时数据、执行 `go / warn / block` 预检，并调度节点内的发布与结果回填
- `openclaw-cluster-orchestrator/`
  - 负责读取 `docs/cluster/` 的节点矩阵与 job queue，选择 worker agent 并把任务 fan-out 到 `docs/nodes/<node_id>/matrix/`

每个目录都包含自己的 `SKILL.md`，可以在所使用的 OpenClaw workspace 中单独注册，从而在需要的时候单独调用其治理、预检或调度逻辑。

## 固定命令路径

某些 OpenClaw channel/gateway 运行环境的 `PATH` 里没有 `openclaw`，所以此 skill 内所有命令都通过显式变量路径调用：

```bash
OPENCLAW_BIN="${OPENCLAW_BIN:-$HOME/.homebrew/bin/openclaw}"
if [ -z "${SKILL_ROOT:-}" ]; then
  if [ -d "$HOME/.openclaw/workspace/skills/social-push" ]; then
    SKILL_ROOT="$HOME/.openclaw/workspace/skills/social-push"
  else
    SKILL_ROOT="$HOME/.openclaw/skills/social-push"
  fi
fi
```

不要依赖裸命令 `openclaw ...`，统一执行 `"$OPENCLAW_BIN" ...`。
本 skill 内的 `references/`、`scripts/`、`docs/` 默认都以 `"$SKILL_ROOT"` 对应的 skill 根目录为基准。

## 核心规则

1. 所有社交发布默认使用 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay ...`。
2. 默认直接发布，不保留"草稿优先"分支。
3. 所有本地图片/文件上传前，先用 `"$SKILL_ROOT/scripts/stage_upload_media.sh"` 中转到 `/tmp/openclaw/uploads`。
4. 需要保存到文件并用 `rg/sed` 稳定提取 ref 时，优先使用 `snapshot --format ai --limit <bytes>`（单页推荐 5000-7000）。
5. 只需要快速读取当前页面可交互元素时，优先使用 `snapshot --efficient --interactive --compact`。
6. 页面发生跳转、弹窗切换或上传完成后，必须重新 `snapshot` 获取最新 ref。
7. 如果 `chrome-relay` 扩展中继不可用，先引导用户把扩展附着到当前浏览器标签页；只有用户明确接受时，才回退到隔离的 `openclaw` profile。
8. 如果发现未登录，优先让用户在自己常用浏览器里完成登录，而不是新开空白浏览器。
9. 文件上传优先级：`upload --input-ref`（快照可见的 file input）> `upload --element 'input[type=file][multiple]'`（快照不可见时用 CSS selector）> `upload --ref`（可见的上传按钮）。
10. 如果图片来自 Telegram、QQ 或其他聊天附件，并且用户明确说"用这张图"，只允许把原图复制到 `/tmp/openclaw/uploads/...` 作为临时副本；不要直接上传聊天原图。
11. 每次任务都要记录本次生成的 staged 路径；发布成功或失败后，都要只删除这些 staged 路径，不要删除原始聊天图片。
12. 不要混用旧版 workflow、外部中转 CLI 或其他浏览器 profile。

## 平台映射

按需读取对应 workflow：

- X (Twitter): `$SKILL_ROOT/references/X推文.md`
- Instagram: `$SKILL_ROOT/references/Instagram图文.md`
- Threads: `$SKILL_ROOT/references/Threads动态.md`
- Facebook: `$SKILL_ROOT/references/Facebook动态.md`
- 小红书图文: `$SKILL_ROOT/references/小红书图文.md`
- 小红书长文: `$SKILL_ROOT/references/小红书长文.md`
- 微博: `$SKILL_ROOT/references/微博.md`
- 微信公众号: `$SKILL_ROOT/references/微信公众号文章.md`
- 掘金: `$SKILL_ROOT/references/掘金文章.md`
- Reddit: `$SKILL_ROOT/references/Reddit帖子.md`
- 知乎文章: `$SKILL_ROOT/references/知乎文章.md`
- 知乎想法: `$SKILL_ROOT/references/知乎想法.md`

仅在需要某个平台细节时读取对应文件，不要一次性全读。

## 范围说明

- Reddit、知乎文章、知乎想法已接入 workflow，可按平台映射直接路由。
- 知乎"回答"当前不在本次实现范围内，不要路由到知乎回答流程。
- 调研结论见（仓库内路径）：`docs/2026-03-23-reddit-zhihu-support-research.md`

## 默认工作流

### 1. 解析任务

至少识别这些字段：

- 目标平台
- 内容类型（短帖、图文、长文、文章）
- 标题
- 正文 / 简介 / 话题
- 是否有图片或封面
- subreddit（仅 Reddit 必填）

信息缺失时先追问；信息足够时直接执行。

新增平台意图解析与路由：

- Reddit 文本帖：如“发 Reddit 帖子到 r/python”且无链接、无图片，路由 Reddit 文本帖
- Reddit 链接帖：如“发 Reddit 链接帖”或请求里有明确 link，路由 Reddit 链接帖
- Reddit 图片帖：如“发 Reddit 图帖”或提供图片，路由 Reddit 图片帖（单图/多图按输入图片数量）
- 知乎文章：如“发知乎文章”，路由知乎文章 workflow
- 知乎专栏 / column：视为知乎文章同义词，统一路由知乎文章 workflow
- 知乎想法：如“发知乎想法”，路由知乎想法 workflow
- 知乎回答：明确告知当前不支持，并引导用户改为知乎文章或知乎想法

必填字段缺失时的追问规则：

- Reddit 请求缺少 `subreddit`：先问“要发到哪个 subreddit（例如 r/test）？”
- 知乎文章/专栏请求缺少 `title`：先问“这篇知乎文章的标题是什么？”

平台级默认解释：

- Reddit：默认 subreddit 帖子；有 link 默认链接帖，有图片默认图片帖，否则默认文本帖；发布前需确认目标 subreddit；`2026-03-23` 已用真实账号完成 Reddit 文本帖发布验证
- 知乎：默认按用户意图在“文章（含专栏别名）/想法”二选一；文章必须有标题；知乎回答不在当前实现范围；`2026-03-23` 已用真实账号完成知乎文章与知乎想法发布验证

Reddit 补充规则：

- Reddit 更稳的入口是当前页直接导航到 `https://www.reddit.com/r/<subreddit>/submit?type=TEXT`，不要优先依赖首页 `建立貼文` 打开新标签页
- 如果 `chrome-relay` 在 Reddit 的新标签页或切换目标页后出现 `tab not found`，优先回到当前已附着页，并在该页内完成整条发布链路
- Reddit 文本帖至少需要标题；正文是可选的，但正文输入区在实际 DOM 中可能是富文本 `div`，不要假设一定是普通 `textarea`
- Reddit 成功信号优先看：页面离开 `/submit` 并进入 subreddit 帖流或新帖详情页；必要时可结合页面中出现新发出的标题文本判断
- Reddit 图帖如果提交后页面出现“內容過濾器已移除此貼文”，说明图帖提交动作本身已成功，但随后被 Reddit 或目标 subreddit 的自动过滤链路移除；这更像账号信誉或社区过滤问题，不等同于 workflow 失败
- 如果文本帖能发、图帖总被移除，优先判断为账号/社区过滤差异，而不是上传或点击流程失败；可尝试更宽松的 subreddit、个人社区，或由版主手动 approve

知乎补充规则：

- 知乎文章：稳定入口为 `https://zhuanlan.zhihu.com/write`；标题和正文填完后，`发布` 从禁用变为可用即可进入真实发布
- 知乎想法：稳定入口优先走顶部 `创作 -> 发想法` 菜单，不要优先依赖首页内嵌创作块
- 知乎想法在独立发布面板里通常包含单独的一组 `标题` / 正文 / `发布` 控件；如果首页本身还残留另一组禁用控件，优先操作最后一组、且当前可见的那组
- 知乎想法填完标题与正文后，可能需要等待前端校验或让输入框失焦，`发布` 才会从禁用变为可用
- 知乎文章成功信号：页面离开 `/write` 并进入文章详情页；知乎想法成功信号更适合结合提交态判断，如 `发布中` 后请求成功
- 如果可读取网络请求，知乎想法成功提交可参考：`POST /api/v4/content/publish` 返回 `200`，并随后出现 `GET /api/v4/pins/<id>` 返回 `200`
