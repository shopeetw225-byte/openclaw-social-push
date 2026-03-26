# Social-Push Skill — 配置与使用指南

## 概述

`social-push` 是 OpenClaw 的可安装 skill（skill 仓库），通过浏览器自动化实现一句话发布内容到 10 个社交平台。你可以通过 **Telegram、QQ、本地终端** 等任意 OpenClaw channel 发送指令，OpenClaw 会自动操控你的 Chrome 浏览器完成发布。

当前仓库除了发布 skill 外，还包含三层辅助能力：

- `account-matrix/`
  - 账号矩阵、验证矩阵、preflight checklist 模板
- `docs/ops/`
  - 内容指派台账、冲突台账、operator override 台账
- `matrix-orchestrator/`
  - 读取运行时矩阵、做节点内预检、调度发布并记录结果
- `openclaw-cluster-orchestrator/`
  - 读取 `docs/cluster/`，选择 worker agent，并把任务 fan-out 到节点本地 `docs/nodes/<node_id>/matrix/`

每个目录内部都含有自己的 `SKILL.md`，可以在 OpenClaw workspace 里注册为独立 skill，方便在需要执行账号治理、节点预检或 cluster 任务时单独调用。

### 支持平台一览

| 平台 | 内容类型 | 实测状态 | 备注 |
|------|---------|---------|------|
| Instagram | 图文（单图/多图） | 单图已实测 (2026-03-19) | 多图模板就绪，暂不支持 Reel/Story/视频 |
| Threads | 短帖（纯文字/文字+图） | 已实测 (2026-03-19) | 暂不支持多图/视频 |
| X (Twitter) | 推文（文字/带图） | 模板就绪 | 最多 4 张图 |
| Facebook | 动态（文字/带图） | 模板就绪 | 最多 40 张图 |
| 小红书 | 图文 / 长文 | 已实测 | 有图→图文，无图→长文 |
| 微博 | 短帖（文字/带图） | 模板就绪 | 最多 9 张图，话题格式 `#话题#` |
| 微信公众号 | 文章 | 模板就绪 | 长文用剪贴板粘贴，支持封面 |
| 掘金 | 文章 | 模板就绪 | Markdown 内容，支持分类/标签/封面 |
| Reddit | 帖子（文本 / 链接 / 图帖） | 文本帖已实测 (2026-03-23)；图帖提交流程已验证 | 支持 subreddit、flair、NSFW、spoiler；图帖支持单图/多图 |
| 知乎 | 文章 / 专栏、想法 | 文章、想法已实测 (2026-03-23) | 文章支持标题+正文，想法支持纯文本 |

### 支持平台详情（新增平台）

| 平台 | 第一阶段已支持范围 |
|------|------------------|
| Reddit | 文本帖 / 链接帖 / 图帖（单图与多图）、subreddit、flair、NSFW、spoiler；其中 Reddit 文本帖已于 `2026-03-23` 完成真实发布验证，图帖提交流程已验证但在 `r/test` 上被內容過濾器移除 |
| 知乎 | 文章 / 专栏、想法；其中知乎文章、知乎想法均已于 `2026-03-23` 完成真实发布验证 |

背景调研见 `docs/2026-03-23-reddit-zhihu-support-research.md`。

> 说明：知乎回答当前仍未接入发布流程，遇到回答类指令时建议引导用户改写成文章/专栏或想法，以便使用已验证的 workflow。

---

## 架构

```text
用户 (QQ / Telegram / 终端)
  ↓ 发送指令
OpenClaw Gateway (本地 :18789)
  ↓ 路由到主控 agent
OpenClaw Cluster Orchestrator (main)
  ↓ 选择 worker agent
Worker Agent (publisher-zhihu / publisher-reddit / ...)
  ↓ 调用 matrix-orchestrator
Node-local Matrix Runtime (docs/nodes/<node_id>/matrix/)
  ↓ 调用 social-push
Browser Relay 扩展 (接管 Chrome 标签页)
  ↓ 操控浏览器
目标平台发布页 (复用已有登录态)
```

核心原理：OpenClaw 不需要各平台的 API key，而是通过 **Browser Relay 浏览器扩展** 直接操控你日常使用的 Chrome 浏览器，复用你已有的登录状态。

---

## 前置配置

### 1. OpenClaw Gateway

确保 gateway 已启动：

```bash
openclaw gateway start
```

验证状态：

```bash
openclaw gateway status
```

### 2. Channel 配置（QQ / Telegram）

在 `~/.openclaw/openclaw.json` 的 `channels` 中配置：

> 说明：本节与 README 使用同一套 channel 命名与示例（`telegram` / `qqbot`）。

**Telegram：**
```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "botToken": "<你的 Bot Token>",
      "allowFrom": [<你的 Telegram User ID>],
      "streaming": "partial"
    }
  }
}
```

获取 Bot Token：找 @BotFather 创建 bot，复制 token。
获取 User ID：给 @userinfobot 发消息即可查看。

**QQ Bot：**
```json
{
  "channels": {
    "qqbot": {
      "enabled": true,
      "appId": "<QQ 开放平台 App ID>",
      "clientSecret": "<Client Secret>",
      "token": "<App ID>:<Token>",
      "allowFrom": ["*"]
    }
  }
}
```

在 [QQ 开放平台](https://q.qq.com/) 注册应用获取凭据。

**启用插件：**
```json
{
  "plugins": {
    "allow": ["openclaw-qqbot", "telegram"],
    "entries": {
      "openclaw-qqbot": { "enabled": true },
      "telegram": { "enabled": true }
    }
  }
}
```

### 3. Agent 绑定

确保 agent 配置中包含 browser 工具权限，并绑定到 channel：

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["exec", "browser", "group:fs", "group:sessions", "group:messaging"]
        }
      }
    ]
  },
  "bindings": [
    {
      "agentId": "main",
      "match": { "channel": "qqbot", "accountId": "default" }
    }
  ]
}
```

### 3.1 多 Agent Cluster（V1）建议

V1 推荐在同一个 Gateway 下创建多个 agent，而不是一开始就上多机器：

```bash
python3 openclaw-cluster-orchestrator/scripts/bootstrap_local_agents.py \
  --node-matrix docs/cluster/node-matrix.md \
  --workspace "$HOME/.openclaw/workspace"
```

说明：

- 主控 agent 继续处理用户入口和 cluster job queue
- worker agent 负责消费节点本地 `docs/nodes/<node_id>/matrix/`
- V1 worker 统一通过 `matrix-orchestrator/scripts/run_next_job.py` 执行，不直接绕过到 `social-push`
- 如果 worker 节点走 `chrome-relay`，目标浏览器标签页必须先把 OpenClaw Browser Relay 扩展点成 `ON`，否则 cluster job 会真实返回 `runner_error`

### 3.2 Cluster Smoke 命令

当 `docs/cluster/cluster-job-queue.md` 中已经有一条 `pending` 任务时，可直接运行：

```bash
python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py
```

如果你只想验证 cluster 主控层状态流转，不调用真实 worker，可直接使用 dry-run：

```bash
python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py \
  --dry-run-result-status publish_ok \
  --dry-run-evidence demo://cluster/publish-ok \
  --dry-run-notes demo
```

主控层会依次做这些事：

1. 读取 `docs/cluster/node-matrix.md`
2. 选择 `ready` 的 worker agent
3. 把任务写入 `docs/nodes/<node_id>/matrix/job-queue.md`
4. 调用目标 worker agent
5. 回写：
   - `docs/cluster/cluster-job-queue.md`
   - `docs/cluster/cluster-result-ledger.md`
   - `docs/cluster/cluster-run-log.md`

### 3.2.0 查看当前 cluster 状态

```bash
python3 openclaw-cluster-orchestrator/scripts/cluster_status.py
```

这个脚本会输出：

- cluster queue 各状态计数
- 最新一条 cluster result
- `node-matrix.md` 中每个节点的 agent id、节点状态与本地 queue 状态计数

### 3.2.1 添加一条 cluster job

推荐使用脚本，而不是手改表格：

```bash
python3 openclaw-cluster-orchestrator/scripts/enqueue_cluster_job.py \
  --platform zhihu \
  --account-alias main \
  --content-type idea \
  --preferred-node worker-zhihu-01 \
  --title "Cluster publish" \
  --body "This is a cluster publish test."
```

如果你要启用内容指派防撞层，优先使用：

```bash
python3 matrix-orchestrator/scripts/enqueue_guarded_job.py \
  --queue docs/cluster/cluster-job-queue.md \
  --assignment-ledger docs/ops/content-assignment-ledger.md \
  --conflict-ledger docs/ops/conflict-ledger.md \
  --platform zhihu \
  --account-alias main \
  --content-type idea \
  --preferred-node worker-zhihu-01 \
  --submission-ref ticket://ops-1001 \
  --title "Guarded cluster publish" \
  --body "This job is reserved before queue append."
```

guard 运行时状态会写入：

- `docs/ops/content-assignment-ledger.md`
- `docs/ops/conflict-ledger.md`
- `docs/ops/operator-override-ledger.md`

如果 guard 产生阻断，控制 OpenClaw 的人可以通过：

```bash
python3 matrix-orchestrator/scripts/apply_guard_override.py \
  --queue docs/matrix/job-queue.md \
  --assignment-ledger docs/ops/content-assignment-ledger.md \
  --conflict-ledger docs/ops/conflict-ledger.md \
  --override-ledger docs/ops/operator-override-ledger.md \
  --conflict-id conflict-0001 \
  --job-id job-0001 \
  --attempt-no 1 \
  --action continue_once \
  --operator-ref op://openclaw-controller \
  --reason "checked and approved"
```

### 3.2.2 预览本地 worker bootstrap

如果你只想先确认 node matrix 会创建哪些 worker：

```bash
python3 openclaw-cluster-orchestrator/scripts/bootstrap_local_agents.py \
  --node-matrix docs/cluster/node-matrix.md \
  --workspace "$HOME/.openclaw/workspace" \
  --dry-run
```

### 3.2.3 重置 cluster runtime

如果你想把 cluster queue / cluster ledger / cluster run-log、节点本地 queue / ledger / run-log，以及 `docs/ops/*` 的 assignment / conflict / override 台账一起清空回表头：

```bash
# 先预览会清哪些文件
python3 openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py --dry-run

# 再执行真实重置
python3 openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py
```

当前 CLI 参数为：

- `--cluster-queue`
- `--cluster-run-log`
- `--cluster-result-ledger`
- `--node-runtime-root`
- `--dry-run`

### 3.3 当前已验证到哪一步

V1 当前已经验证：

- 单 Gateway 多 agent 的主控模型可工作
- `publisher-zhihu`、`publisher-reddit` 这样的 worker agent 可以被主控调度
- cluster 失败不会被误报为成功

当前真实 smoke 暴露出的运行前置条件也已经明确：

- 如果 worker 没有启用 node-local `matrix-orchestrator` 的默认 runner，会得到真实 `runner_error`
- 如果没有附着可用的 `chrome-relay` 浏览器标签页，也会得到真实 `runner_error`

这些都是业务环境前置条件，不再是 cluster 主控层本身的误判问题

### 4. Browser Relay 扩展安装（一次性）

这是最关键的一步——安装浏览器扩展，让 OpenClaw 能接管你的 Chrome 标签页。

```bash
# 安装扩展文件
openclaw browser extension install

# 查看扩展路径
openclaw browser extension path
# → ~/.openclaw/browser/chrome-extension
```

然后在 Chrome（或 Brave/Edge）中：

1. 打开 `chrome://extensions`
2. 打开右上角 **开发者模式**
3. 点击 **加载已解压的扩展程序**
4. 选择 `~/.openclaw/browser/chrome-extension` 目录
5. 将 **OpenClaw Browser Relay** 固定到工具栏

### 5. 平台登录

在你日常使用的 Chrome 中，登录以下需要发布的平台：

- Instagram: https://www.instagram.com/
- Threads: https://www.threads.com/
- X: https://x.com/
- Facebook: https://www.facebook.com/
- 小红书: https://creator.xiaohongshu.com/
- 微博: https://weibo.com/
- 微信公众号: https://mp.weixin.qq.com/
- 掘金: https://juejin.cn/
- Reddit: https://www.reddit.com/
- 知乎: https://www.zhihu.com/

登录一次即可，OpenClaw 会复用浏览器中的登录态。

### 6. 激活扩展

每次需要发布时，在 Chrome 中：

1. 点击工具栏上的 **OpenClaw Browser Relay** 图标
2. 确认徽章显示为 **ON**

验证连接：

```bash
openclaw browser --browser-profile chrome-relay tabs
```

如果能列出当前浏览器的标签页，说明连接成功。

---

## 使用方法

### 基本指令格式

通过 QQ、Telegram 或终端向 OpenClaw 发送自然语言指令即可。不需要记任何命令。

### 纯文字发布

```text
发一条小红书：今天的咖啡超好喝，推荐这家店！#咖啡推荐
```

```text
发推特：Just shipped a new feature! Check it out at openclaw.com
```

```text
发 Threads：周末愉快！
```

```text
发微博：新版本上线了，欢迎体验！ #OpenClaw
```

```text
发一篇掘金文章，标题：OpenClaw 浏览器自动化实战，正文：...
```

### 带图发布

**方式一：直接在聊天中发图**

在 Telegram/QQ 中发送图片，然后说：

```text
用这张图发一条 Instagram
```

```text
把这张图发到小红书，配文：今日穿搭分享
```

**方式二：指定本地图片路径**

```text
用 ~/Desktop/product.jpg 发一条 Instagram，配文：新品上市
```

**方式三：多图发布**

在聊天中连续发送多张图片，然后说：

```text
用这些图发 Instagram，配文：旅行日记
```

### 文章发布

```text
发一篇微信公众号文章
标题：OpenClaw 使用指南
正文：...（长文内容）...
```

```text
发掘金文章
标题：如何用 AI 自动化社交媒体发布
分类：人工智能
标签：AI, 自动化
正文：...
```

### 多平台发布

```text
把这条内容同时发到 X 和 Threads：Hello World!
```

---

## 常见问题

### Q: 扩展显示 ON 但 `tabs` 命令返回空？

重新点击扩展图标关闭再开启，或刷新当前页面后重试。

### Q: 提示未登录？

在你的 Chrome 浏览器中直接登录对应平台，然后再次下达指令。OpenClaw 不会代你登录。

### Q: 上传图片超时但发布成功了？

这是已知行为。`upload` 命令可能报 gateway timeout（20s），但图片实际已上传成功。OpenClaw 会在上传后重新检查页面状态，不会因超时中断流程。

### Q: 发布后显示 "分享中" / "Sharing"？

部分平台（如 Instagram）发布后有中间状态。OpenClaw 会自动等待并二次确认，直到出现成功提示。

### Q: snapshot 报 "tab not found"？

relay CDP 连接可能断开。OpenClaw 会自动打开新标签页重试。如果持续失败，检查扩展是否仍为 ON 状态。

### Q: 能在手机上通过 QQ/TG 远程发布吗？

可以。只要：
1. 本地 Mac 上 OpenClaw gateway 在运行
2. Chrome 浏览器打开且扩展为 ON
3. 对应平台已登录

你就可以在手机上通过 QQ/Telegram 给 bot 发消息来触发发布。

### Q: 支持定时发布吗？

当前版本默认直接发布，不保留草稿。部分平台自身支持定时发布功能，但本 skill 暂未集成。

---

## 文件结构

```text
skills/social-push/
├── SKILL.md                          # skill 主定义（路由规则、通用规则、禁忌）
├── GUIDE.md                          # 本文档
├── account-matrix/                   # 独立账号矩阵 skill
├── matrix-orchestrator/              # 独立调度与预检 skill
├── docs/
│   └── 2026-03-23-reddit-zhihu-support-research.md
├── references/
│   ├── Instagram图文.md              # Instagram 发布 workflow
│   ├── Threads动态.md                # Threads 发布 workflow
│   ├── X推文.md                      # X/Twitter 发布 workflow
│   ├── Facebook动态.md               # Facebook 发布 workflow
│   ├── 小红书图文.md                  # 小红书图文 workflow
│   ├── 小红书长文.md                  # 小红书长文 workflow
│   ├── 微博.md                       # 微博发布 workflow
│   ├── 微信公众号文章.md              # 微信公众号 workflow
│   ├── 掘金文章.md                   # 掘金发布 workflow
│   ├── Reddit帖子.md                 # Reddit 发帖 workflow
│   ├── 知乎文章.md                    # 知乎文章 workflow
│   └── 知乎想法.md                    # 知乎想法 workflow
└── scripts/
    ├── stage_upload_media.sh          # 图片暂存脚本
    └── cleanup_staged_media.sh        # 暂存清理脚本
```

矩阵相关补充文档：

- `docs/account-matrix-sample.md`
- `docs/matrix-system-roadmap.md`

---

## 安全说明

- OpenClaw 不存储任何平台密码，完全依赖浏览器已有登录态
- 图片仅在 `/tmp/openclaw/uploads/` 临时存储，发布后自动删除
- 聊天原图、桌面原图等原始文件不会被触碰
- 所有发布操作在本地 Chrome 中执行，不经过第三方服务器
- QQ/Telegram channel 支持 `allowFrom` 白名单，只响应授权用户
