# OpenClaw Social-Push 使用文档

> 从零开始，一条命令发布到 10 个社交平台；Reddit 与知乎已进入第一阶段支持

---

## 目录

1. [项目简介](#1-项目简介)
2. [系统架构](#2-系统架构)
3. [环境准备](#3-环境准备)
4. [安装 Chrome 浏览器中继插件](#4-安装-chrome-浏览器中继插件)
5. [安装 Social-Push Skill](#5-安装-social-push-skill)
6. [配置消息通道](#6-配置消息通道)
7. [登录社交平台账号](#7-登录社交平台账号)
8. [发布内容](#8-发布内容)
9. [支持平台详情](#9-支持平台详情)
10. [图片处理机制](#10-图片处理机制)
11. [常见问题排查](#11-常见问题排查)
12. [安全说明](#12-安全说明)

---

## 1. 项目简介

**Social-Push** 是一个 OpenClaw 可安装 Skill（skill 仓库），让你通过一条自然语言指令，把内容同时发布到多个社交平台。

**核心特点：**

- 当前支持 10 个平台：X (Twitter)、Instagram、Threads、Facebook、小红书、微博、微信公众号、掘金、Reddit、知乎
- Reddit 第一阶段支持文本帖/链接帖/图帖（单图与多图）、subreddit、flair、NSFW、spoiler
- 知乎第一阶段支持文章/专栏与想法发布
- 仓库现已包含五层能力：`social-push` 发布层、`account-matrix` 账号治理层、`content-assignment-guard` 内容指派防撞层、`matrix-orchestrator` 节点内调度层、`openclaw-cluster-orchestrator` 主控调度层
- 不需要任何平台 API Key，直接复用浏览器登录状态
- 支持文字、图片、长文章等多种内容形式
- 所有操作在本地执行，不经过第三方服务器
- 通过 Telegram、QQ 或终端发送指令

**工作原理：** 你在 Chrome 浏览器里登录各平台账号，OpenClaw 通过浏览器中继插件（Browser Relay Extension）操控浏览器自动完成发布流程。

---

## 2. 系统架构

```text
你的指令 (Telegram / QQ / 终端)
        ↓
OpenClaw Gateway (localhost:18789)
        ↓
Agent 进程 (解析自然语言意图)
        ↓
Browser Relay 插件 (操控 Chrome)
        ↓
目标社交平台 (自动填写 & 发布)
```

---

## 3. 环境准备

### 3.1 安装 OpenClaw

如果还未安装 OpenClaw，请先完成安装：

```bash
# macOS (Homebrew)
brew install openclaw
```

### 3.2 启动 Gateway

Gateway 是 OpenClaw 的本地网关服务，所有指令通过它路由：

```bash
openclaw gateway start
```

验证是否启动成功：

```bash
# Gateway 默认监听 localhost:18789
curl http://localhost:18789/health
```

> **提示：** 每次重启电脑后需要重新启动 Gateway。

---

## 4. 安装 Chrome 浏览器中继插件

这是最关键的一步。Browser Relay 插件让 OpenClaw 能控制你的 Chrome 浏览器。

### 4.1 安装插件文件

```bash
openclaw browser extension install
```

这会将插件文件下载到 `~/.openclaw/browser/chrome-extension/` 目录。

### 4.2 在 Chrome 中加载插件

1. 打开 Chrome，地址栏输入 `chrome://extensions/`
2. 右上角开启 **「开发者模式」**（Developer mode）
3. 点击 **「加载已解压的扩展程序」**（Load unpacked）
4. 选择文件夹：`~/.openclaw/browser/chrome-extension/`
5. 插件加载成功后，工具栏会出现 Browser Relay 图标

### 4.3 激活插件

- 点击工具栏的 **Browser Relay 图标**
- 图标显示 **"ON"** 表示已激活
- 激活状态下，OpenClaw 可以操控当前浏览器

> **注意：** 每次关闭并重新打开 Chrome 后，可能需要重新点击图标激活。

### 4.4 验证插件是否正常工作

```bash
# 在终端执行，如果能截取到浏览器页面快照，说明插件工作正常
openclaw browser snapshot
```

---

## 5. 安装 Social-Push Skill

### 5.1 从 GitHub 安装

在 OpenClaw workspace 根目录执行：

```bash
# 克隆仓库到 workspace 下的 skills 目录
git clone https://github.com/shopeetw225-byte/openclaw-social-push.git \
  skills/social-push
```

> 说明：本文档与 GUIDE 统一使用 workspace 相对路径 `skills/social-push/` 表示 skill 仓库位置。

### 5.2 验证 Skill 已加载

```bash
openclaw skills list
```

应能看到 `social-push` 出现在列表中。

### 5.3 Skill 文件结构

```text
skills/social-push/
├── SKILL.md                     # Skill 定义与架构说明
├── GUIDE.md                     # 配置与使用指南
├── account-matrix/              # 独立账号矩阵 skill
├── matrix-orchestrator/         # 独立节点内调度与预检 skill
├── openclaw-cluster-orchestrator/ # 独立 cluster 主控 skill
├── docs/
│   ├── cluster/                 # cluster runtime
│   ├── nodes/                   # node-local runtime
│   ├── ops/                     # content-assignment ledgers / conflicts / overrides
│   └── 2026-03-23-reddit-zhihu-support-research.md
├── scripts/
│   ├── stage_upload_media.sh    # 图片暂存脚本
│   └── cleanup_staged_media.sh  # 临时文件清理脚本
└── references/                  # 各平台自动化流程定义
    ├── X推文.md
    ├── Instagram图文.md
    ├── Threads动态.md
    ├── Facebook动态.md
    ├── 小红书图文.md
    ├── 小红书长文.md
    ├── 微博.md
    ├── 微信公众号文章.md
    ├── 掘金文章.md
    ├── Reddit帖子.md
    ├── 知乎文章.md
    └── 知乎想法.md
```

---

## 6. 配置消息通道

你可以通过 **Telegram**、**QQ** 或 **终端** 向 OpenClaw 发送发布指令。至少配置一个通道。

### 6.0 Content Assignment Guard（多人多号防撞）

当你需要多人协作、提前指定目标账号、并防止重复内容/发错号时，先走 guard 层再入队：

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
  --title "Guarded publish" \
  --body "This job is reserved before it becomes runnable."
```

运行时会把状态写到：

- `docs/ops/content-assignment-ledger.md`
- `docs/ops/conflict-ledger.md`
- `docs/ops/operator-override-ledger.md`

如果发现重复内容、目标账号不一致、或后续浏览器身份不一致，系统会默认阻断；只有 OpenClaw 控制人可以通过 override 继续一次或取消任务。

### 6.1 配置 Telegram

**第一步：创建 Telegram Bot**

1. 在 Telegram 中搜索 `@BotFather`，发送 `/newbot`
2. 按提示设置 Bot 名称和用户名
3. 记录返回的 **Bot Token**（格式：`123456789:ABCdefGhIjKlMnOpQrStUvWxYz`）

**第二步：获取你的 User ID**

1. 在 Telegram 中搜索 `@userinfobot`
2. 向它发送任意消息
3. 它会返回你的 **User ID**（纯数字）

**第三步：写入配置**

编辑 `~/.openclaw/openclaw.json`：

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "botToken": "<你的 Bot Token>",
      "allowFrom": ["<你的 Telegram User ID>"],
      "streaming": "partial"
    }
  }
}
```

### 6.2 配置 QQ Bot

编辑 `~/.openclaw/openclaw.json`：

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

> 说明：README 与 GUIDE 已统一使用 `telegram` / `qqbot` 的 channel 命名与配置示例。

### 6.3 直接使用终端

无需额外配置，直接在终端与 OpenClaw 交互即可。

---

## 7. 登录社交平台账号

Social-Push 复用你 Chrome 浏览器中的登录状态，因此你需要 **手动登录** 每个要发布的平台。

在 Chrome 中逐个打开以下网站并登录：

| 平台 | 登录网址 |
|------|---------|
| X (Twitter) | https://x.com |
| Instagram | https://www.instagram.com |
| Threads | https://www.threads.com/ |
| Facebook | https://www.facebook.com |
| 小红书 | https://creator.xiaohongshu.com/ |
| 微博 | https://weibo.com |
| 微信公众号 | https://mp.weixin.qq.com |
| 掘金 | https://juejin.cn |
| Reddit | https://www.reddit.com |
| 知乎 | https://www.zhihu.com |

> **重要：**
> - 只需登录你想要发布的平台，不用全部登录
> - 登录后保持登录状态（勾选「记住我」），不要手动退出
> - 如果登录过期，重新登录即可

---

## 8. 发布内容

### 8.1 确认一切就绪

发布前的检查清单：

- [x] OpenClaw Gateway 已启动 (`openclaw gateway start`)
- [x] Chrome 浏览器已打开
- [x] Browser Relay 插件已激活（图标显示 "ON"）
- [x] 目标平台已登录

### 8.2 使用示例

**发布纯文字：**

```text
发一条推特：Hello World! 这是我的第一条自动发布
```

```text
发微博：今天天气真好 #随手拍
```

**发布带图片的内容：**

```text
把桌面上的 photo.jpg 发到 Instagram，配文：周末的阳光
```

```text
发一条小红书图文，图片用 ~/Pictures/outfit.jpg，标题：今日穿搭分享
```

**多平台同时发布：**

```text
把这条内容同时发到 X 和 Threads：新产品正式上线了！
```

**发布长文章：**

```text
发一篇掘金文章，标题：《从零搭建自动化发布系统》，正文：...
```

```text
发一篇微信公众号文章，标题：周报，正文：本周进展...
```

### 8.3 通过 Telegram 发送

1. 打开与你创建的 Bot 的对话
2. 直接发送自然语言指令
3. 图片可以作为 Telegram 消息附件发送

### 8.4 通过终端发送

```bash
openclaw chat "发一条微博：终端发布测试"
```

---

## 9. 支持平台详情

### X (Twitter)

| 项目 | 限制 |
|------|------|
| 文字 | 最多 280 字符（中文 1 字 = 2 字符） |
| 图片 | 最多 4 张 |
| 格式 | 纯文本 + 图片 |

### Instagram

| 项目 | 限制 |
|------|------|
| 图片 | 必须至少 1 张，支持多图轮播 |
| 说明文字 | 支持长文配文 |
| 注意 | 纯文字帖子不支持 |

### Threads

| 项目 | 限制 |
|------|------|
| 文字 | 支持纯文字帖子 |
| 图片 | 最多 1 张 |
| 格式 | 文字 或 文字+单图 |

### Facebook

| 项目 | 限制 |
|------|------|
| 文字 | 无明确字数限制 |
| 图片 | 支持多图 |
| 格式 | 时间线动态 |

### 小红书

| 项目 | 限制 |
|------|------|
| 图文笔记 | 标题最多 20 字，支持多图 |
| 长文笔记 | 无图片时自动切换为长文模式 |
| 标签 | 支持 #标签 |
| 智能路由 | 有图 → 图文模式 / 无图 → 长文模式 |

### 微博

| 项目 | 限制 |
|------|------|
| 文字 | 普通用户 140 字，会员 2000 字 |
| 图片 | 最多 9 张 |
| 标签 | 格式为 `#内容#` |

### 微信公众号

| 项目 | 限制 |
|------|------|
| 格式 | 文章（标题 + 正文） |
| 封面 | 可选封面图 |
| 注意 | 仅支持已认证的公众号 |

### 掘金

| 项目 | 限制 |
|------|------|
| 格式 | 文章（标题 + 正文） |
| 封面 | 可选封面图 |
| 分类 | 需要选择文章分类 |

### Reddit

| 项目 | 支持范围 |
|------|---------|
| 帖子类型 | 文本帖 / 链接帖 / 图帖 |
| 图片能力 | 单图 / 多图图帖 |
| 发布参数 | subreddit、flair、NSFW、spoiler |
| 实测状态 | Reddit 文本帖已于 `2026-03-23` 完成真实发布验证；图帖提交流程已验证，但在 `r/test` 上被內容過濾器移除 |

### 账号与调度层

当前仓库除发布 skill 外，还额外提供：

- `account-matrix/`
  - 用于账号矩阵、验证矩阵、发布前检查清单模板
- `matrix-orchestrator/`
  - 用于读取 `docs/matrix/` 运行时数据、做 `go / warn / block` 预检，并为节点内发布和结果回填提供执行层
- `openclaw-cluster-orchestrator/`
  - 用于读取 `docs/cluster/` 节点矩阵与 cluster job queue，选择本地 worker agent，并把任务 fan-out 到 `docs/nodes/<node_id>/matrix/`

这些子目录各自包含 `SKILL.md`，可以在 OpenClaw workspace 中单独注册，以便在需要的时候激活对应的治理、预检、调度流程。

### OpenClaw Cluster（V1）

第一版 cluster 不是多机器集群，而是：

- 单个 OpenClaw Gateway
- 多个独立 agent
- 一个主控 agent + 多个 worker agent

推荐角色：

- `main` 或 `main-orchestrator`
  - 负责 cluster 控制面
- `publisher-zhihu`
  - 负责知乎节点
- `publisher-reddit`
  - 负责 Reddit 节点

V1 的执行链路固定为：

```text
openclaw-cluster-orchestrator
  -> worker agent
  -> matrix-orchestrator
  -> social-push
```

### 知乎

| 项目 | 支持范围 |
|------|---------|
| 内容类型 | 文章 / 专栏、想法 |
| 文章能力 | 标题 + 正文发布 |
| 想法能力 | 纯文本想法发布 |
| 实测状态 | 知乎文章、知乎想法已于 `2026-03-23` 完成真实发布验证 |

调研背景见：`docs/2026-03-23-reddit-zhihu-support-research.md`

推荐配合阅读：

- `docs/account-matrix-sample.md`
- `docs/matrix-system-roadmap.md`
- `docs/cluster/node-matrix.md`
- `docs/cluster/cluster-job-queue.md`

> 说明：当前仅在知乎文章/专栏与知乎想法上接入发布流程，知乎回答尚未纳入，请引导用户将回答类意图改写成文章或想法。

---

## Cluster Quickstart

如果你要开始用 V1 的 OpenClaw cluster 主控层，最短路径是：

```bash
# 1. 创建本地 worker agents
python3 openclaw-cluster-orchestrator/scripts/bootstrap_local_agents.py \
  --node-matrix docs/cluster/node-matrix.md \
  --workspace "$HOME/.openclaw/workspace"

# 2. 加一条 cluster job
python3 openclaw-cluster-orchestrator/scripts/enqueue_cluster_job.py \
  --platform zhihu \
  --account-alias main \
  --content-type idea \
  --preferred-node worker-zhihu-01 \
  --title "Cluster publish" \
  --body "This is a cluster publish test."

# 3. 确认 skill 已加载
openclaw skills check

# 4. 查看当前 cluster 状态
python3 openclaw-cluster-orchestrator/scripts/cluster_status.py

# 5. 执行一条 cluster job
python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py
```

如果你想先验证 queue / ledger / log 变化，不触发真实 worker，可用 dry-run：

```bash
python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py \
  --dry-run-result-status publish_filtered \
  --dry-run-evidence demo://cluster/filter \
  --dry-run-notes demo
```

如果你只想预览会创建哪些本地 worker agents：

```bash
python3 openclaw-cluster-orchestrator/scripts/bootstrap_local_agents.py \
  --node-matrix docs/cluster/node-matrix.md \
  --workspace "$HOME/.openclaw/workspace" \
  --dry-run
```

如果你想看每个 worker 当前是否真的 ready，可把 readiness 一起打出来：

```bash
python3 openclaw-cluster-orchestrator/scripts/cluster_status.py --include-readiness
```

如果某条 cluster job 已经 `blocked` 或 `failed`，并且环境已经修好，可以直接追加新的 retry attempt：

```bash
python3 openclaw-cluster-orchestrator/scripts/requeue_cluster_job.py \
  --job-id cluster-job-0003
```

如果你想清空 cluster runtime 与 node-local runtime，只保留表头：

```bash
python3 openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py --dry-run
python3 openclaw-cluster-orchestrator/scripts/reset_cluster_runtime.py
```

V1 目前已经验证：

- 主控可以选择 worker agent
- 主控可以把 job fan-out 到 `docs/nodes/<node_id>/matrix/`
- worker 可以继续调用 `matrix-orchestrator` 和 `social-push`
- 真实失败原因会被准确记录到 cluster ledger / log

运行前置条件：

- 目标 worker 使用的账号必须已经登录到对应平台
- 如果该节点依赖 `chrome-relay`，目标浏览器标签页上的 OpenClaw Browser Relay 必须是 `ON`
- 主控会在写入 node-local queue 前先检查 worker 的浏览器身份；如果没有附着可用标签页、未登录或账号不匹配，cluster queue 会直接记为 `blocked`，cluster ledger 会记一条 `routing_blocked`

## 10. 图片处理机制

### 10.1 图片来源优先级

Social-Push 按以下顺序查找图片：

1. `~/.openclaw/media/inbound/` — 最近接收的文件（如 Telegram 收到的图片）
2. 当前消息的附件（Telegram / QQ 消息中的图片）
3. 用户指定的绝对路径（如 `~/Desktop/photo.jpg`）
4. 桌面/下载/图片文件夹中的最近文件

### 10.2 暂存机制

为保护原始文件，所有图片在上传前会被复制到临时目录：

```text
原始文件                              暂存文件
~/Desktop/photo.jpg  ──复制──>  /tmp/openclaw/uploads/social-push-1711216423.jpg
```

- 原始文件 **永远不会被删除或修改**
- 发布成功后，暂存文件自动清理
- 暂存目录：`/tmp/openclaw/uploads/`

---

## 11. 常见问题排查

### Q: 插件图标没有显示 "ON"

- 重新点击 Browser Relay 图标
- 确认 Chrome 开发者模式已开启
- 尝试卸载重装插件

### Q: 发布时提示登录失效

- 在 Chrome 中手动打开对应平台，检查是否仍处于登录状态
- 如果已退出，重新登录即可
- 某些平台（如微信公众号）登录有效期较短，可能需要频繁重新登录

### Q: 图片上传失败

- 确认图片文件存在且路径正确
- 检查图片格式是否为 JPG / PNG（部分平台不支持 WebP）
- 查看 `/tmp/openclaw/uploads/` 中是否生成了暂存文件
- 注意：即使终端显示超时（exit code 1），图片可能已成功上传，系统会自动重新截图验证

### Q: Gateway 无法启动

```bash
# 检查端口是否被占用
lsof -i :18789

# 重启 Gateway
openclaw gateway stop
openclaw gateway start
```

### Q: 页面元素找不到（ref 失效）

- 这是正常现象，页面导航或内容变化后元素引用会失效
- 系统会自动重新截取页面快照并获取新的元素引用
- 如果持续失败，可能是平台更新了页面结构，需要更新对应的 reference 文件

### Q: 多平台发布中某个平台失败

- 系统会逐个平台执行，某个失败不影响其他平台
- 检查失败平台的登录状态
- 重新发送只针对失败平台的发布指令

---

## 12. 安全说明

| 安全特性 | 说明 |
|---------|------|
| 无密码存储 | 不保存任何平台的账号密码 |
| 会话复用 | 仅依赖浏览器已有的登录状态 |
| 本地执行 | 所有操作在本机完成，不经过外部服务器 |
| 临时文件 | 暂存图片发布后自动清理 |
| 原始文件保护 | 永远不删除用户的原始文件 |
| 安全删除限制 | 清理脚本仅允许删除 `/tmp/openclaw/uploads/` 下的文件 |
