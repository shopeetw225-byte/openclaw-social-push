## 发布 Facebook 个人主页动态 workflow

### 实测状态

- `2026-03-19` 纯文字发帖和单图发帖模板已就绪，尚未 live 实测
- 多图模板为新增，基于单图模板扩展，尚未 live 实测
- 发布按钮使用 `evaluate` JS 点击，兼容中文繁体/简体/英文三套文案

### 怎么用

- 先把模板代码块最上面的变量改成你这次要发的内容
- 整段从上到下执行，不要跳步，不要复用旧 `ref`
- 默认通过 `chrome-relay` 复用你常用浏览器里的 Facebook 登录态
- 如果页面不是中文也没关系，模板已经兼容常见的中文 / 英文按钮文案
- Facebook 优先复用你当前常用浏览器里已经打开的 `facebook.com` 标签页；如果还没打开，自动 `open` 一个新的

### 标准模板：纯文字动态

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
POST_TEXT='把这里替换成你的动态内容'
PROFILE_URL='https://www.facebook.com/me'

find_facebook_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.facebook\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID="$(find_facebook_tab)"
if [ -z "$TARGET_ID" ]; then
  OPEN_OUT="$("$OPENCLAW_BIN" browser --browser-profile "$PROFILE" open 'https://www.facebook.com/')"
  TARGET_ID="$(printf '%s\n' "$OPEN_OUT" | sed -n 's/^id: //p')"
fi
[ -n "$TARGET_ID" ] || { echo '拿不到 Facebook tab id'; exit 1; }

SNAP1="/tmp/fb-home-$$.txt"
SNAP2="/tmp/fb-dialog-$$.txt"
VERIFY="/tmp/fb-verify-$$.txt"

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" 'https://www.facebook.com/'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$SNAP1"

ENTRY_REF="$(rg 'button ".*(在想些什麼|在想些什么|What.s on your mind).*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$ENTRY_REF" ] || { echo '找不到发帖入口 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$ENTRY_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

TEXT_REF="$(rg 'textbox .*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | tail -n1)"
CONTINUE_REF="$(rg 'button "(繼續|继续|Continue)".*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$TEXT_REF" ] || { echo '找不到正文输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$TEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$TEXT_REF" "$POST_TEXT" --slowly

if [ -n "$CONTINUE_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CONTINUE_REF"
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2200
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
  const btn = Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button"))
    .find((el) => ["發佈", "发布", "发帖", "Post"].includes((el.getAttribute("aria-label") || el.textContent || "").trim()));
  if (!btn) return { ok: false, reason: "publish button not found" };
  const disabled = btn.getAttribute("aria-disabled") === "true" || btn.disabled === true;
  if (disabled) return { ok: false, reason: "publish button disabled" };
  btn.click();
  return { ok: true };
}'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4500

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" "$PROFILE_URL"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$VERIFY"

rg -F "$POST_TEXT" "$VERIFY" >/dev/null && echo "发布成功: $POST_TEXT" || echo '发布动作已执行，但主页验证没命中正文，建议人工复核'
```

### 标准模板：文字 + 单图动态

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
if [ -d "$HOME/.openclaw/workspace/skills/social-push" ]; then
  SKILL_ROOT="$HOME/.openclaw/workspace/skills/social-push"
else
  SKILL_ROOT="$HOME/.openclaw/skills/social-push"
fi
POST_TEXT='把这里替换成你的动态内容'
IMAGE_SRC='/绝对路径/图片.jpg'
PROFILE_URL='https://www.facebook.com/me'

STAGE_SH="$SKILL_ROOT/scripts/stage_upload_media.sh"
CLEAN_SH="$SKILL_ROOT/scripts/cleanup_staged_media.sh"

find_facebook_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.facebook\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID="$(find_facebook_tab)"
if [ -z "$TARGET_ID" ]; then
  OPEN_OUT="$("$OPENCLAW_BIN" browser --browser-profile "$PROFILE" open 'https://www.facebook.com/')"
  TARGET_ID="$(printf '%s\n' "$OPEN_OUT" | sed -n 's/^id: //p')"
fi
[ -n "$TARGET_ID" ] || { echo '拿不到 Facebook tab id'; exit 1; }

STAGED=''
cleanup() {
  [ -n "$STAGED" ] && bash "$CLEAN_SH" "$STAGED" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SNAP1="/tmp/fb-home-$$.txt"
SNAP2="/tmp/fb-dialog-$$.txt"
SNAP3="/tmp/fb-after-upload-$$.txt"
VERIFY="/tmp/fb-verify-$$.txt"

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" 'https://www.facebook.com/'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$SNAP1"

ENTRY_REF="$(rg 'button ".*(在想些什麼|在想些什么|What.s on your mind).*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$ENTRY_REF" ] || { echo '找不到发帖入口 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$ENTRY_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

TEXT_REF="$(rg 'textbox .*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | tail -n1)"
PHOTO_REF="$(rg 'button ".*(相片／影片|相片/影片|Photo/video|Photo\/video|照片/视频).*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
FILE_INPUT_REF="$(rg 'input .*type=file.*accept=.*image.*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$TEXT_REF" ] || { echo '找不到正文输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$TEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$TEXT_REF" "$POST_TEXT" --slowly

STAGED="$(bash "$STAGE_SH" "$IMAGE_SRC" facebook)"
if [ -n "$FILE_INPUT_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --input-ref "$FILE_INPUT_REF" "$STAGED"
elif [ -n "$PHOTO_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --ref "$PHOTO_REF" "$STAGED"
else
  echo '找不到图片上传入口 ref'; exit 1
fi
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP3"

rg -q '編輯影音內容|编辑照片/视频|移除貼文附件|Remove post attachment|Edit photo/video|Edit all' "$SNAP3" || {
  echo '图片未确认附着成功'
  exit 1
}

CONTINUE_REF="$(rg 'button "(繼續|继续|Continue)".*\\[ref=e[0-9]+' "$SNAP3" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
if [ -n "$CONTINUE_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CONTINUE_REF"
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2200
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
  const btn = Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button"))
    .find((el) => ["發佈", "发布", "发帖", "Post"].includes((el.getAttribute("aria-label") || el.textContent || "").trim()));
  if (!btn) return { ok: false, reason: "publish button not found" };
  const disabled = btn.getAttribute("aria-disabled") === "true" || btn.disabled === true;
  if (disabled) return { ok: false, reason: "publish button disabled" };
  btn.click();
  return { ok: true };
}'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4500

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" "$PROFILE_URL"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$VERIFY"

if rg -Fq "$POST_TEXT" "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '发布动作已执行，但主页验证没命中正文，建议人工复核'
fi
```

### 标准模板：文字 + 多图动态

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
if [ -d "$HOME/.openclaw/workspace/skills/social-push" ]; then
  SKILL_ROOT="$HOME/.openclaw/workspace/skills/social-push"
else
  SKILL_ROOT="$HOME/.openclaw/skills/social-push"
fi
POST_TEXT='把这里替换成你的动态内容'
IMAGE_PATHS=(
  '/绝对路径/图片1.jpg'
  '/绝对路径/图片2.jpg'
)
PROFILE_URL='https://www.facebook.com/me'

STAGE_SH="$SKILL_ROOT/scripts/stage_upload_media.sh"
CLEAN_SH="$SKILL_ROOT/scripts/cleanup_staged_media.sh"

find_facebook_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.facebook\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID="$(find_facebook_tab)"
if [ -z "$TARGET_ID" ]; then
  OPEN_OUT="$("$OPENCLAW_BIN" browser --browser-profile "$PROFILE" open 'https://www.facebook.com/')"
  TARGET_ID="$(printf '%s\n' "$OPEN_OUT" | sed -n 's/^id: //p')"
fi
[ -n "$TARGET_ID" ] || { echo '拿不到 Facebook tab id'; exit 1; }
[ "${#IMAGE_PATHS[@]}" -ge 2 ] || { echo '多图模板至少需要 2 张图片，单图请用单图模板'; exit 1; }

STAGED_PATHS=()
cleanup() {
  [ "${#STAGED_PATHS[@]}" -gt 0 ] && bash "$CLEAN_SH" "${STAGED_PATHS[@]}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SNAP1="/tmp/fb-home-$$.txt"
SNAP2="/tmp/fb-dialog-$$.txt"
SNAP3="/tmp/fb-after-upload-$$.txt"
VERIFY="/tmp/fb-verify-$$.txt"

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" 'https://www.facebook.com/'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$SNAP1"

ENTRY_REF="$(rg 'button ".*(在想些什麼|在想些什么|What.s on your mind).*\\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$ENTRY_REF" ] || { echo '找不到发帖入口 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$ENTRY_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

TEXT_REF="$(rg 'textbox .*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | tail -n1)"
PHOTO_REF="$(rg 'button ".*(相片／影片|相片/影片|Photo/video|Photo\/video|照片/视频).*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
FILE_INPUT_REF="$(rg 'input .*type=file.*accept=.*image.*\\[ref=e[0-9]+' "$SNAP2" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$TEXT_REF" ] || { echo '找不到正文输入框 ref'; exit 1; }

# 先输入文字
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$TEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$TEXT_REF" "$POST_TEXT" --slowly

# 按顺序 stage 所有图片
STAGED_FILES=()
for i in "${!IMAGE_PATHS[@]}"; do
  STAGED_FILES+=("$(bash "$STAGE_SH" "${IMAGE_PATHS[$i]}" "facebook-$((i + 1))")")
done
STAGED_PATHS+=("${STAGED_FILES[@]}")

# 一次上传所有 staged 图片
if [ -n "$FILE_INPUT_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --input-ref "$FILE_INPUT_REF" "${STAGED_FILES[@]}"
elif [ -n "$PHOTO_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --ref "$PHOTO_REF" "${STAGED_FILES[@]}"
else
  echo '找不到图片上传入口 ref'; exit 1
fi

# 多图上传等待更久
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time $((3000 + ${#IMAGE_PATHS[@]} * 1500))
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP3"

rg -q '編輯影音內容|编辑照片/视频|移除貼文附件|Remove post attachment|Edit photo/video|Edit all' "$SNAP3" || {
  echo '图片未确认附着成功'
  exit 1
}

# 用 evaluate 确认实际附着的图片数量
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
  const dialog = document.querySelector("[role=dialog]");
  if (!dialog) return { ok: false, reason: "dialog not found" };
  const imgs = dialog.querySelectorAll("img[src*=\"blob:\"], img[src*=\"scontent\"]");
  return { ok: true, uploadedCount: imgs.length };
}'

CONTINUE_REF="$(rg 'button "(繼續|继续|Continue)".*\\[ref=e[0-9]+' "$SNAP3" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
if [ -n "$CONTINUE_REF" ]; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CONTINUE_REF"
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2200
fi

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => {
  const btn = Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button"))
    .find((el) => ["發佈", "发布", "发帖", "Post"].includes((el.getAttribute("aria-label") || el.textContent || "").trim()));
  if (!btn) return { ok: false, reason: "publish button not found" };
  const disabled = btn.getAttribute("aria-disabled") === "true" || btn.disabled === true;
  if (disabled) return { ok: false, reason: "publish button disabled" };
  btn.click();
  return { ok: true };
}'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 6000

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" "$PROFILE_URL"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$VERIFY"

if rg -Fq "$POST_TEXT" "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '发布动作已执行，但主页验证没命中正文，建议人工复核'
fi
```

## 关键提示

- 每次打开弹窗、输入内容、上传图片、点击 `继续` 后，都要重新 `snapshot`，不要沿用旧 `ref`
- Facebook 文案会随语言切换变化，发帖入口常见文案是 `在想些什么？`、`在想些什麼？`、`What's on your mind?`
- 图片上传优先使用隐藏的 `input[type=file]`（`--input-ref`），拿不到时再退到 `相片／影片` 按钮（`--ref`）
- 多图一次性传入所有 staged 路径，不需要逐张上传
- 多图上传后的等待时间按图片数量动态增加：`3000 + 图片数 * 1500` 毫秒
- 如果快照里已经直接出现最终 `發佈` / `Post` 按钮，没有 `继续`，就跳过 `CONTINUE_REF` 那一步
- `PROFILE_URL` 默认使用 `https://www.facebook.com/me`，会自动跳转到当前登录用户的主页
- Facebook 支持最多约 40 张图片每帖；建议单次不超过 10 张以保证上传稳定性
- 发布按钮的 `evaluate` 会先检查 `aria-disabled` 状态，避免点击被禁用的按钮

## 故障恢复

- **找不到发帖入口**：重新执行首页 `snapshot`，确认当前标签页真的是 Facebook 首页；如果首页加载不完整，用 `navigate` 重新加载
- **找不到正文框**：说明弹窗没有真的打开，重新点击发帖入口，再 `wait` + `snapshot`
- **找不到图片上传入口**：先用 `evaluate` 检查 dialog 里有没有隐藏的 `input[type=file]`：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay evaluate --target-id "$TARGET_ID" --fn '() => Array.from(document.querySelectorAll("[role=dialog] input[type=file]")).map((el) => ({ accept: el.accept, multiple: el.multiple }))'
```

- **上传后没看到 `編輯影音內容` 或 `移除貼文附件`**：重新 stage 一次图片，再重新执行上传；多图时确认每张 staged 文件都还在 `/tmp/openclaw/uploads`
- **多图只上传了部分**：检查 `evaluate` 返回的 `uploadedCount`，与预期图片数对比；如果不符，尝试先清理已上传的图片，重新从 `相片／影片` 步骤开始
- **发布按钮没找到或被禁用**：先执行下面这句查看当前弹窗按钮文案和状态

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay evaluate --target-id "$TARGET_ID" --fn '() => Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button")).map((el) => ({ label: el.getAttribute("aria-label") || el.textContent?.trim(), disabled: el.getAttribute("aria-disabled") }))'
```

- **快照显示登录流程**：不要切换到隔离浏览器，直接在你当前常用浏览器标签页里手动登录，然后从打开 Facebook 首页那一步继续
- **gateway 断连 (1006 abnormal closure)**：先执行 `"$OPENCLAW_BIN" gateway restart`，确认 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay tabs` 恢复正常后再继续
- **弹出 `捨棄貼文` 或 `Discard post` 确认框**：重新 `snapshot`，找到 `捨棄` / `Discard` 按钮点掉，然后从头开始
