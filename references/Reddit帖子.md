## 发布 Reddit 帖子 workflow

本参考遵循 `SKILL.md` 中的 `OPENCLAW_BIN` 约定，下文命令里的 `"$OPENCLAW_BIN"` 均指 OpenClaw 可执行文件。

实测记录：`2026-03-23` 已在真实账号 + `chrome-relay` 环境下完成 Reddit 文本帖真实发布验证；图帖提交流程也已走通，但在 `r/test` 上被内容过滤器自动移除。

1. 确保当前标签页已由 OpenClaw Browser Relay 扩展附着，然后进入目标 subreddit（示例 `r/test`）并走到发帖页：
   - 优先直接在当前页导航：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay navigate "https://www.reddit.com/r/<subreddit>/submit?type=TEXT"`
   - 或先到社区页再点 `Create Post`：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay navigate "https://www.reddit.com/r/<subreddit>/"`
2. 短等待并抓交互快照（不要依赖 `networkidle`）：
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay wait --time 3000`
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay snapshot --efficient --interactive --compact`
3. 输入标题（必填）：
   - 点击标题框：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <标题输入框ref>`
   - 清空旧值（如有）：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay press "Meta+A"` 后 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay press Backspace`
   - 输入标题：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay type <标题输入框ref> "{title}"`
4. 选择帖子类型分支（同一流程三选一）：
   - 文本帖：点击 `Post` / `Text` 标签，输入正文（可选）
   - 链接帖：点击 `Link` 标签，输入必填 `{link}`（若该界面提供，可再输入正文）
   - 图片帖：点击 `Images` / `Image` 标签，上传 1 张或多张 `图片`
5. 正文输入（平台允许时可选）：
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <正文输入框ref>`
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay type <正文输入框ref> "{body}"`
6. 图片上传（仅图片帖；支持 staged 文件）：
   - 单图：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay upload --input-ref <文件输入ref> "/tmp/openclaw/uploads/<image-1>"`
   - 多图（一次上传，顺序固定）：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay upload --input-ref <文件输入ref> "/tmp/openclaw/uploads/<image-1>" "/tmp/openclaw/uploads/<image-2>" ...`
   - 如果只有上传按钮 ref：改用 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay upload --ref <上传按钮ref> "/tmp/openclaw/uploads/<image-1>" "/tmp/openclaw/uploads/<image-2>" ...`
   - 图片顺序以 `images[]` 顺序 / 用户发送顺序为准；多图发布顺序按该顺序保持
7. 如果社区要求选择 post flair，先选 flair 再发布：
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <Add flair按钮ref>`
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <目标flair选项ref>`
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <Apply/保存ref>`
8. 按需切换 NSFW / spoiler：
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <NSFW开关ref>`
   - `"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <spoiler开关ref>`
9. 点击发布并执行发布后确认：
   - 发布：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay click <Post按钮ref>`
   - 发布后确认：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay wait --time 2000`
   - 发布后确认：`"$OPENCLAW_BIN" browser --browser-profile chrome-relay snapshot --efficient --interactive --compact`
   - 发布后确认：优先检查当前 URL 是否包含 `/comments/`，且页面标题或 H1 是否与刚发布的 `{title}` 一致

## 重要提示

- 每次切换帖子类型、输入、上传、开关、选 flair 后都要重新 `snapshot`，不要复用旧 `ref`
- `chrome-relay` 在 Reddit 上更稳的方式是“同页导航 + 同页发布”；如果通过 `建立貼文` 打开新标签页后频繁出现 `tab not found`，优先回到当前已附着页并直接导航到 `/submit`
- Reddit 发帖类型标签会随 UI 变化，可能显示为 `Post`、`Text`、`Link`、`Images`、`Image`；实际操作以最新一次 `snapshot` 里可见标签为准
- Poll / 投票 当前明确不在本 workflow 支持范围（out of scope）
- 链接帖的 `{link}` 为必填；正文是否允许附加取决于 Reddit 当前界面和社区配置，允许时再填 body
- 文本帖至少需要标题；正文是可选的，但正文输入区在实际 DOM 里可能是富文本 `div`
- 图片帖必须区分单图和多图；多图上传使用同一次 `upload` 并保持 `images[]` 顺序
- 如果图帖发布后页面提示“抱歉，Reddit 內容過濾器已移除此貼文”，优先判断为 Reddit/社区过滤，而不是 skill 上传或点击失败

## 故障恢复

- **未登录**：快照出现登录页或登录弹窗时，先在当前浏览器会话手动登录 Reddit，再回到 subreddit 发帖页
- **subreddit 限制发帖类型**：如果看不到 `Text/Link/Images` 某个标签，说明该社区不允许该类型，改用允许的类型或换社区
- **flair 必选**：发布按钮禁用且提示需 flair 时，先完成 flair 选择再发帖
- **账号年龄 / karma / 邮箱验证限制**：若出现社区门槛提示，自动化无法绕过，需更换账号或满足条件后重试
- **图片仍在处理中**：上传后 `Post` 按钮不可点或有 processing 提示时，继续 `wait --time` + `snapshot`，确认缩略图稳定后再发布
- **图帖被內容過濾器移除**：若帖子已提交回到 subreddit 帖流，但正文位置显示“內容過濾器已移除此貼文”，说明提交流程已完成，只是被 Reddit 或社区过滤；可换更宽松的 subreddit、个人社区，或等待版主 approve
