## 发布 Threads 动态 workflow

### 实测状态

- `2026-03-19` 已在 live `chrome-relay` 登录态下实测通过 `纯文字` 和 `文字 + 单图` 发帖
- 实际成功链路是：现有 Threads 标签页 -> 首页 inline composer `有什麼新鮮事？` -> `新串文` dialog -> active textbox -> `發佈` -> 页面出现新帖
- 这次实测的验证信号包括：页面命中新帖正文，且新帖链接形如 `/@qiang8513/post/...`
- `文字 + 单图` 复用同一个 `新串文` dialog，图片入口实测文案是 `附加影音內容`

### 怎么用

- 先把模板代码块最上面的变量改成你这次要发的内容
- Threads 优先复用你当前常用浏览器里已经打开的 `threads.com` 标签页；如果还没打开，先手动开一个并确认已登录
- 所有命令都基于当前 live `social-push` skill 的固定二进制路径：`"$OPENCLAW_BIN"`
- Threads 的 tab target 可能会变化，所以模板会先重新找最新的 `threads.com` 标签页，再执行当前 tab 上的操作

### 对话触发示例

下面这些自然语言指令都应该直接命中当前 `social-push -> Threads` workflow：

```text
帮我发一条 Threads，文案是：今晚继续测试 OpenClaw
```

```text
帮我发一条 Threads，文字+图片，文案是：111，图片用 /Users/openclawcn/Desktop/test.jpg
```

```text
帮我发 Threads，文案是：今晚继续测试 OpenClaw，图片用桌面最新那张
```

```text
发一条 Threads，文字+图片，文案：Threads smoke test，图片用这张 /Users/openclawcn/Desktop/telegram-cloud-photo-size-5-6183605501891907011-y.jpg
```

```text
帮我发一条 Threads 纯文字动态：今天继续开发 social-push
```

对话触发时，默认规则是：

- 用户明确提到 `Threads`，就路由到本文件对应 workflow
- 用户只给文案，没有图片，就走 `纯文字`
- 用户给了图片路径、说“用桌面最新那张”或明确说“文字+图片”，就走 `文字 + 单图`
- 如果图片有歧义，先按 `social-push` 主 skill 里的图片优先级去找；只有真有歧义时才追问

### 标准模板：纯文字动态

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
POST_TEXT='把这里替换成你的 Threads 正文'

find_threads_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.threads\.com\//{n;s/^ *id: //p;}' | tail -n1
}

focus_threads_tab() {
  TARGET_ID="$(find_threads_tab)"
  [ -n "$TARGET_ID" ] || {
    echo '当前浏览器里没有可用的 Threads 标签页，请先手动打开 https://www.threads.com/ 后重试'
    exit 1
  }
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
}

SNAP1="/tmp/threads-home-$$.txt"
SNAP2="/tmp/threads-compose-$$.txt"
VERIFY="/tmp/threads-verify-$$.txt"

focus_threads_tab
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2500
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 6000 --out "$SNAP1"

PROMPT_REF="$(rg 'button ".*(文字欄位空白|撰寫新貼文|Text field is empty|write a new post).*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
CREATE_REF="$(rg 'button "(建立|Create|New thread|New Thread|新貼文|新贴文)".*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"

if [ -n "$PROMPT_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$PROMPT_REF"
elif [ -n "$CREATE_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CREATE_REF"
else
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
    const nodes = Array.from(document.querySelectorAll("button,a,div[role=button]"));
    const el = nodes.find((node) => /(有什麼新鮮事|有什么新鲜事|What.s new|New thread|Create|建立|新貼文|新贴文)/i.test((node.getAttribute("aria-label") || node.textContent || "").trim()));
    if (!el) return { ok: false, reason: "composer-entry-not-found" };
    el.click();
    return { ok: true, label: (el.getAttribute("aria-label") || el.textContent || "").trim() };
  }'
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

TEXT_REF="$(rg '(textbox|textarea).*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
POST_REF="$(rg 'button "(發佈|发布|Post)".*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$TEXT_REF" ] || { echo '找不到 Threads 正文输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$TEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$TEXT_REF" "$POST_TEXT" --slowly

if [ -n "$POST_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$POST_REF"
else
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
    const btn = Array.from(document.querySelectorAll("[role=dialog] button, [role=dialog] div[role=button]"))
      .find((el) => /^(Post|发布|發佈)$/.test((el.getAttribute("aria-label") || el.textContent || "").trim()));
    if (!btn) return { ok: false, reason: "publish-button-not-found" };
    const disabled = btn.getAttribute("aria-disabled") === "true" || btn.disabled === true;
    if (disabled) return { ok: false, reason: "publish-button-disabled" };
    btn.click();
    return { ok: true, label: (btn.getAttribute("aria-label") || btn.textContent || "").trim() };
  }'
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3500
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --text "$POST_TEXT" --timeout-ms 8000 || true
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$VERIFY"

if rg -Fq "$POST_TEXT" "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '发布动作已执行，但当前快照没命中正文，建议人工复核'
fi
```

### 标准模板：文字 + 单图动态

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
POST_TEXT='把这里替换成你的 Threads 正文'
IMAGE_SRC='/绝对路径/图片.jpg'

STAGE_SH='/Users/openclawcn/.openclaw/workspace/skills/social-push/scripts/stage_upload_media.sh'
CLEAN_SH='/Users/openclawcn/.openclaw/workspace/skills/social-push/scripts/cleanup_staged_media.sh'

find_threads_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.threads\.com\//{n;s/^ *id: //p;}' | tail -n1
}

focus_threads_tab() {
  TARGET_ID="$(find_threads_tab)"
  [ -n "$TARGET_ID" ] || {
    echo '当前浏览器里没有可用的 Threads 标签页，请先手动打开 https://www.threads.com/ 后重试'
    exit 1
  }
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
}

STAGED=''
cleanup() {
  [ -n "$STAGED" ] && bash "$CLEAN_SH" "$STAGED" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SNAP1="/tmp/threads-home-$$.txt"
SNAP2="/tmp/threads-compose-$$.txt"
SNAP3="/tmp/threads-after-upload-$$.txt"
VERIFY="/tmp/threads-verify-$$.txt"

focus_threads_tab
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2500
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 6000 --out "$SNAP1"

PROMPT_REF="$(rg 'button ".*(文字欄位空白|撰寫新貼文|Text field is empty|write a new post).*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
CREATE_REF="$(rg 'button "(建立|Create|New thread|New Thread|新貼文|新贴文)".*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"

if [ -n "$PROMPT_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$PROMPT_REF"
elif [ -n "$CREATE_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CREATE_REF"
else
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
    const nodes = Array.from(document.querySelectorAll("button,a,div[role=button]"));
    const el = nodes.find((node) => /(有什麼新鮮事|有什么新鲜事|What.s new|New thread|Create|建立|新貼文|新贴文)/i.test((node.getAttribute("aria-label") || node.textContent || "").trim()));
    if (!el) return { ok: false, reason: "composer-entry-not-found" };
    el.click();
    return { ok: true, label: (el.getAttribute("aria-label") || el.textContent || "").trim() };
  }'
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

TEXT_REF="$(rg '(textbox|textarea).*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
UPLOAD_INPUT_REF="$(rg 'input.*file.*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\\[ref=(e[0-9]+).*/\1/' | head -n1)"
ATTACH_REF="$(rg 'button "(附加影音內容|Attach media|Add media|Add photo|Add image|Photo|Image|照片|相片|新增相片|新增照片|加入照片|加入相片)".*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\\[ref=(e[0-9]+).*/\1/' | head -n1)"
POST_REF="$(rg 'button "(發佈|发布|Post)".*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$TEXT_REF" ] || { echo '找不到 Threads 正文输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$TEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$TEXT_REF" "$POST_TEXT" --slowly

STAGED="$(bash "$STAGE_SH" "$IMAGE_SRC" threads)"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => ({
  fileInputs: Array.from(document.querySelectorAll("input[type=file]")).map((el) => ({
    accept: el.accept,
    multiple: el.multiple
  }))
})'

if [ -n "$UPLOAD_INPUT_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --input-ref "$UPLOAD_INPUT_REF" "$STAGED"
elif [ -n "$ATTACH_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --ref "$ATTACH_REF" "$STAGED"
else
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --element 'input[type=file][accept*="image"]' "$STAGED"
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3500
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP3"

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
  const text = document.body.innerText;
  return {
    hasRemove: /Remove|移除|删除/.test(text),
    hasPreviewImage: document.querySelectorAll("img").length > 0
  };
}'

if [ -n "$POST_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$POST_REF"
else
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
    const btn = Array.from(document.querySelectorAll("[role=dialog] button, [role=dialog] div[role=button]"))
      .find((el) => /^(Post|发布|發佈)$/.test((el.getAttribute("aria-label") || el.textContent || "").trim()));
    if (!btn) return { ok: false, reason: "publish-button-not-found" };
    const disabled = btn.getAttribute("aria-disabled") === "true" || btn.disabled === true;
    if (disabled) return { ok: false, reason: "publish-button-disabled" };
    btn.click();
    return { ok: true, label: (btn.getAttribute("aria-label") || btn.textContent || "").trim() };
  }'
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3500
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --text "$POST_TEXT" --timeout-ms 8000 || true
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$VERIFY"

if rg -Fq "$POST_TEXT" "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '发布动作已执行，但当前快照没命中正文，建议人工复核'
fi
```

## 关键提示

- 当前 Threads 首页已经有 inline composer，但实测更稳的路径是先点 `有什麼新鮮事？`，进入 `新串文` dialog 后再操作
- 纯文字和单图都走同一个 `新串文` dialog；单图只是额外执行 `附加影音內容` 上传步骤
- 图片流程优先先用 `evaluate` 确认 `input[type=file]` 存在；能拿到 `input-ref` 就用 `upload --input-ref`，拿不到时再退到 `upload --ref`，最后才用 `--element`
- Threads 第一阶段只支持 `纯文字` 和 `文字+单图`，不支持多图、视频或草稿调度
- 如果页面不是中文也没关系，模板已经同时容忍常见中文 / 英文按钮文案

## 故障恢复

- 找不到 Threads tab：先在你当前常用浏览器里手动打开一个 `https://www.threads.com/` 标签页，再重新执行模板
- 找不到发帖入口：重新 `snapshot`，优先看首页 inline composer 的 `有什麼新鮮事？`，其次再看左侧 / 底部的 `建立`
- 找不到正文框：说明 `新串文` dialog 没有真的打开，重新点击发帖入口并等待
- 上传失败：确认 staged 文件还在 `/tmp/openclaw/uploads`，必要时重新 stage 一次
- 遇到 `gateway closed (1006 abnormal closure)`：先执行 `"$OPENCLAW_BIN" gateway restart`，确认 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay tabs` 恢复正常后再继续
- 发布按钮找不到：先执行下面这句，查看当前弹窗按钮文案

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay evaluate --target-id "$TARGET_ID" --fn '() => Array.from(document.querySelectorAll("[role=dialog] button, [role=dialog] div[role=button]")).map((el) => ({ label: el.getAttribute("aria-label") || el.textContent?.trim(), disabled: el.getAttribute("aria-disabled") }))'
```

- 如果 Threads 页面跳到登录或账号选择，不要切换到隔离浏览器，直接在你当前常用浏览器里手动完成后再继续
