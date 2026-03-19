---
name: social-push
description: "Use when the user wants to publish content to Instagram, Threads, X/Twitter, Facebook, Xiaohongshu, Weibo, WeChat Official Accounts, or Juejin through OpenClaw's native browser automation while reusing the login state from their regular Chrome or Chromium browser. Prefer the `chrome-relay` extension relay profile, stage local uploads into `/tmp/openclaw/uploads`, and use the isolated `openclaw` browser only as an explicit fallback."
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

## 固定命令路径

某些 OpenClaw channel/gateway 运行环境的 `PATH` 里没有 `openclaw`，所以此 skill 内所有命令都固定使用绝对路径：

```bash
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
```

不要依赖裸命令 `openclaw ...`，统一执行 `"$OPENCLAW_BIN" ...`。

## 核心规则

1. 所有社交发布默认使用 `”$OPENCLAW_BIN” browser --browser-profile chrome-relay ...`。
2. 默认直接发布，不保留”草稿优先”分支。
3. 所有本地图片/文件上传前，先用 `./scripts/stage_upload_media.sh` 中转到 `/tmp/openclaw/uploads`。
4. 快照优先使用 `snapshot --format ai --limit <bytes>`（单页推荐 5000-7000）。
5. 页面发生跳转、弹窗切换或上传完成后，必须重新 `snapshot` 获取最新 ref。
6. 如果 `chrome-relay` 扩展中继不可用，先引导用户把扩展附着到当前浏览器标签页；只有用户明确接受时，才回退到隔离的 `openclaw` profile。
7. 如果发现未登录，优先让用户在自己常用浏览器里完成登录，而不是新开空白浏览器。
8. 文件上传优先级：`upload --input-ref`（快照可见的 file input）> `upload --element 'input[type=file][multiple]'`（快照不可见时用 CSS selector）> `upload --ref`（可见的上传按钮）。很多平台的 `input[type=file]` 在 `snapshot --format ai` 里不可见，此时必须用 `--element` CSS selector。
9. 如果图片来自 Telegram、QQ 或其他聊天附件，并且用户明确说”用这张图”，只允许把原图复制到 `/tmp/openclaw/uploads/...` 作为临时副本；不要直接上传聊天原图。
10. 每次任务都要记录本次生成的 staged 路径；发布成功或失败后，都要只删除这些 staged 路径，不要删除原始聊天图片。
11. 不要混用旧版 workflow、外部中转 CLI 或其他浏览器 profile。

## 通用自动化规则（所有平台适用）

以下规则从 Instagram、Threads、Facebook 等平台实测中总结，适用于所有 workflow：

### 元素类型兼容

快照中的可点击元素可能是 `button`、`link`、`generic` 等多种类型，**不要假设元素一定是 `button`**。所有 ref 提取 regex 都应兼容多种类型：

```bash
# ✅ 正确：兼容 link 和 button
rg '(link|button) “.*(目标文案).*\[ref=e[0-9]+' “$SNAP”

# ❌ 错误：只匹配 button，会漏掉 link 类型的入口
rg 'button “(目标文案)”.*\[ref=e[0-9]+' “$SNAP”
```

实测案例：Instagram 侧边栏的 “新貼文” 和 “貼文” 都是 `link`；Threads 的部分入口也是 `link`。

### Tab 查找与复用

每个平台 workflow 都应先尝试复用已有标签页，找不到再 `open` 新的。统一模式：

```bash
find_platform_tab() {
  “$OPENCLAW_BIN” browser --browser-profile “$PROFILE” tabs \
    | sed -n '/https:\/\/www\.目标域名\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID=”$(find_platform_tab)”
if [ -z “$TARGET_ID” ]; then
  OPEN_OUT=”$(“$OPENCLAW_BIN” browser --browser-profile “$PROFILE” open '目标URL')”
  TARGET_ID=”$(printf '%s\n' “$OPEN_OUT” | sed -n 's/^id: //p')”
fi
[ -n “$TARGET_ID” ] || { echo '拿不到目标 tab id'; exit 1; }
```

如果 `tabs` 能列出 tab 但 `snapshot` 报 `tab not found`，说明 relay CDP 连接断了，此时应 `open` 新 tab 重试。

### Upload 容错

`upload` 命令可能触发 `gateway timeout after 20000ms`（exit code 1），但文件实际已成功上传到页面。**不要因为 upload 返回非零 exit code 就中断流程**。正确做法：

```bash
“$OPENCLAW_BIN” browser --browser-profile “$PROFILE” upload --target-id “$TARGET_ID” --element 'input[type=file][multiple]' “$STAGED” || true
“$OPENCLAW_BIN” browser --browser-profile “$PROFILE” wait --target-id “$TARGET_ID” --time 4000
# 重新 snapshot 检查页面是否进入了下一步
```

### 发布后中间状态

部分平台点击发布后不会立刻显示成功，会先出现中间状态（如 Instagram 的 `”分享中”` / `Sharing`）。统一模式：

```bash
# 第一次等待 + 检查
“$OPENCLAW_BIN” browser --browser-profile “$PROFILE” wait --target-id “$TARGET_ID” --time 5000
“$OPENCLAW_BIN” browser --browser-profile “$PROFILE” snapshot --target-id “$TARGET_ID” --format ai --limit 5000 --out “$VERIFY”

# 如果仍在中间状态，再等一轮
if rg -q '分享中|Sharing|正在发布|Publishing|发送中|Sending' “$VERIFY” && ! rg -q '成功|已分享|shared|Post shared' “$VERIFY”; then
  “$OPENCLAW_BIN” browser --browser-profile “$PROFILE” wait --target-id “$TARGET_ID” --time 5000
  “$OPENCLAW_BIN” browser --browser-profile “$PROFILE” snapshot --target-id “$TARGET_ID” --format ai --limit 5000 --out “$VERIFY”
fi
```

### 多语言文案兼容

所有按钮文案匹配都必须同时兼容**中文繁体、中文简体、英文**三套变体。典型模式：

```bash
# 下一步
rg 'button “(下一步|Next)”'
# 发布/分享
rg 'button “(發佈|发布|Post|分享|Share)”'
# 继续
rg 'button “(繼續|继续|Continue)”'
```

## 平台映射

按需读取对应 workflow：

- X (Twitter): `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/X推文.md`
- Instagram: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/Instagram图文.md`
- Threads: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/Threads动态.md`
- Facebook: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/Facebook动态.md`
- 小红书图文: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/小红书图文.md`
- 小红书长文: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/小红书长文.md`
- 微博: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/微博.md`
- 微信公众号: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/微信公众号文章.md`
- 掘金: `/Users/openclawcn/.openclaw/workspace/skills/social-push/references/掘金文章.md`

仅在需要某个平台细节时读取对应文件，不要一次性全读。

## 默认工作流

### 1. 解析任务
至少识别这些字段：
- 目标平台
- 内容类型（短帖、图文、长文、文章）
- 标题
- 正文 / 简介 / 话题
- 是否有图片或封面

信息缺失时先追问；信息足够时直接执行。

跨平台默认路由规则：
- 用户明确指定了“图文 / 长文 / 文章 / 短帖”时，始终以用户指定为准
- 用户提供了图片、封面或附件时，默认走“带图 / 可上传素材”的发布路径
- 用户没有提供任何图片、封面或附件时，默认走“纯文字”发布路径；对于只有单一 workflow 的平台，直接跳过上传步骤
- 如果平台只有一个 workflow 同时兼容有图和无图（例如 X、微博），不要人为拆成两套流程；同一 workflow 内按是否有图决定是否执行上传
- 如果平台有多个内容形态（例如小红书图文 / 小红书长文），才根据“是否有图”来选具体 workflow

Instagram 细化路由规则：
- 用户发 1 张图：走单图分支
- 用户发 2 张及以上图片：走多图分支
- 图片顺序以用户发送顺序 / 明确路径顺序为准
- 第一版不支持纯文字、Reel、Story 或视频

平台级默认解释：
- Instagram：默认图文；1 张图走单图，2+ 张图走多图，顺序按用户发送顺序 / 明确路径顺序；第一版不支持纯文字、Reel、Story 或视频
- Threads：默认短帖；无图走纯文字，有图走文字+单图；`2026-03-19` 已实测纯文字和文字+单图发帖；第一版不支持多图、视频或草稿调度
- X：默认短帖；有图则在同一 workflow 内附图
- Facebook：默认个人主页短帖；有图则在同一 workflow 内附图
- 微博：默认短帖；有图则在同一 workflow 内附图
- 小红书：有图默认图文；无图默认长文
- 微信公众号：默认文章；封面为可选
- 掘金：默认文章；封面为可选

小红书细化路由规则：
- 用户明确说“小红书图文”或提供了图片：走“小红书图文” workflow
- 用户明确说“小红书长文”：走“小红书长文” workflow
- 用户只说“发小红书”，且没有图片：默认走“小红书长文” workflow
- 小红书长文如果没有单独给标题，默认使用正文前 20 个字；正文很短时标题可直接与正文相同

### 2. 浏览器健康检查
先确认扩展中继是否已准备好：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay tabs
```

如果返回空列表、报未附着、或控制不到当前浏览器：

```bash
"$OPENCLAW_BIN" browser extension install
"$OPENCLAW_BIN" browser extension path
```

然后提示用户完成这一次性设置：
- Chrome/Brave/Edge 打开 `chrome://extensions`
- 启用开发者模式
- Load unpacked 选择 `~/.openclaw/browser/chrome-extension`
- 把 `OpenClaw Browser Relay` 固定到工具栏
- 在目标浏览器标签页上点击扩展图标，直到徽章显示 `ON`

如果用户明确不想接管现有浏览器，再讨论是否回退到 `openclaw` profile。

### 3. 打开目标页面并建立基线快照
在已附着的现有浏览器标签页上执行：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay navigate "<publish-url>"
"$OPENCLAW_BIN" browser --browser-profile chrome-relay wait --time 2000
"$OPENCLAW_BIN" browser --browser-profile chrome-relay snapshot --efficient --interactive --compact
```

如果页面是 X、微博、公众号后台这类长连接页面，不要硬等 `networkidle`。优先用短等待、`wait --url`、`wait --text` 或直接 `snapshot` 判断页面是否已可交互。

### 4. 确认登录态
如果快照显示登录页、扫码页或“登录”入口：
- 提示用户直接在自己当前浏览器标签页里完成登录
- 登录完成后重新 `wait` + `snapshot`
- 不要自动切回隔离 profile，除非用户明确同意

### 5. 上传暂存规则
凡是要上传的本地文件，必须先执行：

```bash
/Users/openclawcn/.openclaw/workspace/skills/social-push/scripts/stage_upload_media.sh "<原始路径>" [前缀]
```

然后只使用脚本输出的新路径上传。`"$OPENCLAW_BIN" browser upload` 只接受 `/tmp/openclaw/uploads/...` 下的路径。
如果图片来自 Telegram、QQ 或当前聊天附件，也视为“原始路径”，必须先复制出 staged 副本，再上传 staged 副本；不要直接上传聊天原图。
如果是现有浏览器会话，上传命令优先使用：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay upload --input-ref <文件输入ref> "/tmp/openclaw/uploads/<file>"
```

或：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay upload --ref <上传按钮ref> "/tmp/openclaw/uploads/<file>"
```

把每次任务生成的 staged 路径记下来。任务结束时统一执行：

```bash
bash /Users/openclawcn/.openclaw/workspace/skills/social-push/scripts/cleanup_staged_media.sh "/tmp/openclaw/uploads/<file1>" ["/tmp/openclaw/uploads/<file2>" ...]
```

只传本次任务新生成的 staged 路径，不要把聊天原图或用户绝对路径传给 cleanup 脚本。

### 6. 发布前最终检查
点击发布前至少确认：
- 当前账号是正确账号
- 标题 / 正文 / 标签是最终版
- 上传的图片或封面是本次任务对应文件
- 发布按钮处于可点击状态

### 7. 发布后确认
点击发布后优先做：
- `wait --text "<成功提示>"`，如果页面有明确成功文案
- 或 `wait --time 1500` 后重新 `snapshot`
- 或检查发布弹窗关闭、编辑器清空、页面跳转到列表页

返回给用户：成功 / 失败、失败原因、是否需要补登录或重试。

## 图片处理

当用户发了图片或要求带图发布时，按以下优先级找图：

1. `~/.openclaw/media/inbound/` 中最近收到的图片
2. 当前消息附件中的图片路径（如 QQ/Telegram 下载路径）
3. 用户明确给出的绝对路径
4. `~/Desktop`、`~/Downloads`、`~/Pictures` 里最近修改的图片

除非存在歧义，否则不要为了“图片路径”来回折腾用户。

Telegram、QQ 与其他聊天平台统一遵循同一条规则：
- 用户明确指定“用这张图”时，把这张图当作原始输入
- 先复制到 `/tmp/openclaw/uploads/...` 生成 staged 副本
- 浏览器上传只使用 staged 副本
- 任务彻底结束后，只删除本次 staged 副本
- 不删除 `~/.openclaw/media/inbound/` 原图、不删除 Telegram 下载原图、不删除 QQ 下载原图、不删除用户桌面原图

任务彻底结束后，删除本次生成的 staged 文件；只删本次文件，不清空整个 `/tmp/openclaw/uploads`。

## 失败恢复

- `ref` 失效：重新 `snapshot --efficient --interactive --compact`
- 上传失败：确认 staged 路径仍在 `/tmp/openclaw/uploads`，必要时重新 stage 一次
- 任务失败结束：在返回结果前，仍然删除本次 staged 副本；不要保留临时副本在 `/tmp/openclaw/uploads`
- 扩展未附着：提示用户点击当前标签页上的 OpenClaw Browser Relay 扩展，徽章需显示 `ON`
- 登录失效：提示用户在自己常用浏览器里手动登录后继续
- browser service 不可达：停止重试，提示用户检查 gateway、扩展附着状态或重新打开浏览器
- 页面结构变更：先用最新快照找到新 ref，再更新对应 workflow

## 禁忌

- 不要调用任何外部中转浏览器 CLI
- 不要默认切回隔离的 `openclaw` 浏览器
- 不要在未附着扩展的情况下假设已经接管了用户浏览器
- 不要直接上传工作区外路径或聊天下载目录原文件
- 不要删除 Telegram、QQ、`~/.openclaw/media/inbound/` 或用户桌面里的原始图片
- 不要在未确认登录态的情况下点击发布
- 不要在页面变化后继续使用旧 ref

## 维护说明

这是 workspace 覆盖版 skill，当前维护 Instagram、Threads、X、Facebook、小红书、微博、微信公众号、掘金的原生 OpenClaw 发布链路，并默认复用用户现有浏览器登录态。
新增或修改此 skill 后，如果会话仍命中旧说明，需要重启 gateway 并刷新旧 session。
