## 发布推文 workflow

1. 确保当前标签页已由 OpenClaw Browser Relay 扩展附着，然后导航到 X 发布页：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay navigate "https://x.com/compose/post"`
2. 不要等待 `networkidle`，改用短等待：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay wait --time 3000`
3. 获取交互快照：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay snapshot --efficient --interactive --compact`
4. 点击正文编辑框：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay click <正文编辑框ref>`
5. 如果编辑框里有旧内容，先清空：
   - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay press "Meta+A"`
   - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay press Backspace`
6. 输入推文内容：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay type <正文编辑框ref> "{推文内容}"`
7. 如果有图片，先重新快照拿到 file input 或上传按钮 ref，再上传 staged 文件：
   - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay upload --input-ref <文件输入ref> "/tmp/openclaw/uploads/<图片文件>"`
   - 或 `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay upload --ref <上传按钮ref> "/tmp/openclaw/uploads/<图片文件>"`
8. 上传后等待并重新快照：
   - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay wait --time 2000`
   - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay snapshot --efficient --interactive --compact`
9. 点击发布按钮：`/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay click <Post按钮ref>`
10. 发布后确认：
    - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay wait --time 1500`
    - `/Users/openclawcn/.homebrew/bin/openclaw browser --browser-profile chrome-relay snapshot --efficient --interactive --compact`

## 重要提示

- 每次输入、上传、弹出菜单后都要重新 `snapshot`
- X 页面常有长连接，`wait --load networkidle` 可能超时；优先使用 `wait --time`、`wait --url` 或直接快照
- 发布按钮不可点时，优先检查是否超字数、是否仍在登录页、图片是否还在处理中
- 如果快照显示登录流程，说明你的常用浏览器当前没有登录 X，先在该标签页手动登录
- 现有浏览器会话上传优先使用 `--input-ref` / `--ref`，不要默认使用 `--element`

## 注意事项

- 推文字数限制：普通用户 **280 字符**（中文每字算 2 字符权重），Premium 用户更多
- 图片支持格式：JPG、PNG、GIF、WebP，最多 4 张图片
- 添加话题标签：直接在推文内容中加入 `#话题`
