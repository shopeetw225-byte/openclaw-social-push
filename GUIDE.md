# Social-Push Skill — 配置与使用指南

## 概述

`social-push` 是 OpenClaw 的内置 skill，通过浏览器自动化实现一句话发布内容到 9 个社交平台。你可以通过 **Telegram、QQ、本地终端** 等任意 OpenClaw channel 发送指令，OpenClaw 会自动操控你的 Chrome 浏览器完成发布。

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

---

## 架构

```
用户 (QQ / Telegram / 终端)
  ↓ 发送指令
OpenClaw Gateway (本地 :18789)
  ↓ 路由到 agent
OpenClaw Agent (main)
  ↓ 匹配 social-push skill
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

```
发一条小红书：今天的咖啡超好喝，推荐这家店！#咖啡推荐
```

```
发推特：Just shipped a new feature! Check it out at openclaw.com
```

```
发 Threads：周末愉快！
```

```
发微博：新版本上线了，欢迎体验！ #OpenClaw
```

```
发一篇掘金文章，标题：OpenClaw 浏览器自动化实战，正文：...
```

### 带图发布

**方式一：直接在聊天中发图**

在 Telegram/QQ 中发送图片，然后说：

```
用这张图发一条 Instagram
```

```
把这张图发到小红书，配文：今日穿搭分享
```

**方式二：指定本地图片路径**

```
用 ~/Desktop/product.jpg 发一条 Instagram，配文：新品上市
```

**方式三：多图发布**

在聊天中连续发送多张图片，然后说：

```
用这些图发 Instagram，配文：旅行日记
```

### 文章发布

```
发一篇微信公众号文章
标题：OpenClaw 使用指南
正文：...（长文内容）...
```

```
发掘金文章
标题：如何用 AI 自动化社交媒体发布
分类：人工智能
标签：AI, 自动化
正文：...
```

### 多平台发布

```
把这条内容同时发到 X 和 Threads：Hello World!
```

### 小红书路由规则

- 说 "发小红书" + 有图片 → 自动走 **图文** workflow
- 说 "发小红书" + 无图片 → 自动走 **长文** workflow
- 说 "发小红书图文" → 强制走图文
- 说 "发小红书长文" → 强制走长文

---

## 图片处理机制

OpenClaw 按以下优先级查找图片：

1. `~/.openclaw/media/inbound/` 中最近收到的图片（来自 QQ/TG 消息）
2. 当前聊天消息附件中的图片
3. 用户指定的绝对路径
4. `~/Desktop`、`~/Downloads`、`~/Pictures` 中最近修改的图片

所有图片在上传前会被复制到 `/tmp/openclaw/uploads/` 作为临时副本，发布完成后自动清理。**原始图片永远不会被删除**。

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

```
skills/social-push/
├── SKILL.md                          # skill 主定义（路由规则、通用规则、禁忌）
├── GUIDE.md                          # 本文档
├── references/
│   ├── Instagram图文.md              # Instagram 发布 workflow
│   ├── Threads动态.md                # Threads 发布 workflow
│   ├── X推文.md                      # X/Twitter 发布 workflow
│   ├── Facebook动态.md               # Facebook 发布 workflow
│   ├── 小红书图文.md                  # 小红书图文 workflow
│   ├── 小红书长文.md                  # 小红书长文 workflow
│   ├── 微博.md                       # 微博发布 workflow
│   ├── 微信公众号文章.md              # 微信公众号 workflow
│   └── 掘金文章.md                   # 掘金发布 workflow
└── scripts/
    ├── stage_upload_media.sh          # 图片暂存脚本
    └── cleanup_staged_media.sh        # 暂存清理脚本
```

---

## 安全说明

- OpenClaw 不存储任何平台密码，完全依赖浏览器已有登录态
- 图片仅在 `/tmp/openclaw/uploads/` 临时存储，发布后自动删除
- 聊天原图、桌面原图等原始文件不会被触碰
- 所有发布操作在本地 Chrome 中执行，不经过第三方服务器
- QQ/Telegram channel 支持 `allowFrom` 白名单，只响应授权用户
