## 发布 Instagram 图文 workflow

### 实测状态

- `2026-03-19` 单图发帖已 live 实测通过（chrome-relay，账号 NA NA / qiang8513）
- `2026-03-19` 二次 live 实测通过，使用 openclaw browser relay CLI 完整跑通单图全流程
- 实际成功链路是：侧边栏 `link "新貼文"` -> 展开菜单 `link "貼文"` -> `dialog "建立新貼文"` (上传页) -> `dialog "裁切"` -> `dialog "編輯"` -> `dialog "建立新貼文"` (compose) -> `button "分享"` -> `dialog "已分享貼文"`
- **"新貼文" 和 "貼文" 在快照中都是 `link`，不是 `button`** — ref 提取正则必须兼容 `link` 和 `button`
- 隐藏的 `input[type=file]` 在 `snapshot --format ai` 里不可见 — 上传必须用 `--element` CSS selector
- `upload` 命令在大文件时会触发 `gateway timeout after 20000ms`（exit code 1），但图片仍会成功上传到页面；**不要因此中断流程**
- caption 输入框实测文案是 `撰寫說明文字……` / `Write a caption...`
- 发布成功后 dialog 标题变为 `已分享貼文` / `Post shared`，内含 `已分享你的貼文。`
- 多图模板基于单图扩展，尚未 live 实测

### 怎么用

- 先把模板里的变量改成这次要发的内容和图片
- 默认通过 `chrome-relay` 复用你常用浏览器里的 Instagram 登录态
- Instagram 优先复用你当前常用浏览器里已经打开的 `instagram.com` 标签页；如果还没打开，自动 `open` 一个新的
- 整段从上到下执行，不要跳步，不要复用旧 `ref`
- 这个模板同时覆盖单图和多图两种发帖方式

### 标准模板：单图发帖

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
if [ -d "$HOME/.openclaw/workspace/skills/social-push" ]; then
  SKILL_ROOT="$HOME/.openclaw/workspace/skills/social-push"
else
  SKILL_ROOT="$HOME/.openclaw/skills/social-push"
fi
POST_TEXT='把这里替换成你的贴文文案'
IMAGE_SRC='/绝对路径/图片.jpg'

STAGE_SH="$SKILL_ROOT/scripts/stage_upload_media.sh"
CLEAN_SH="$SKILL_ROOT/scripts/cleanup_staged_media.sh"

find_instagram_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.instagram\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID="$(find_instagram_tab)"
if [ -z "$TARGET_ID" ]; then
  OPEN_OUT="$("$OPENCLAW_BIN" browser --browser-profile "$PROFILE" open 'https://www.instagram.com/')"
  TARGET_ID="$(printf '%s\n' "$OPEN_OUT" | sed -n 's/^id: //p')"
fi
[ -n "$TARGET_ID" ] || { echo '拿不到 Instagram tab id'; exit 1; }

STAGED=''
cleanup() {
  [ -n "$STAGED" ] && bash "$CLEAN_SH" "$STAGED" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SNAP1="/tmp/ig-home-$$.txt"
SNAP2="/tmp/ig-menu-$$.txt"
SNAP3="/tmp/ig-upload-$$.txt"
SNAP4="/tmp/ig-crop-$$.txt"
SNAP5="/tmp/ig-edit-$$.txt"
SNAP6="/tmp/ig-compose-$$.txt"
VERIFY="/tmp/ig-verify-$$.txt"

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" 'https://www.instagram.com/'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$SNAP1"

# 步骤1：点击侧边栏 "新貼文"（实测是 link，不是 button）
NEW_POST_REF="$(rg '(link|button) ".*(新貼文|New post).*\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEW_POST_REF" ] || { echo '找不到 新貼文 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEW_POST_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

# 步骤2：点击展开菜单里的 "貼文"（实测也是 link）
POST_TYPE_REF="$(rg '(link|button) ".*(貼文 貼文|貼文|Post).*\[ref=e[0-9]+' "$SNAP2" | grep -v '新貼文' | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$POST_TYPE_REF" ] || { echo '找不到 貼文 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$POST_TYPE_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP3"

# 步骤3：上传图片
# 隐藏的 input[type=file] 在快照中不可见，必须用 --element CSS selector
STAGED="$(bash "$STAGE_SH" "$IMAGE_SRC" instagram)"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --element 'input[type=file][multiple]' "$STAGED" || \
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --element 'input[type=file]' "$STAGED"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 4000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP4"

# 步骤4：裁切页 -> 下一步
rg -q '裁切|Crop' "$SNAP4" || { echo '上传后没有进入裁切页'; exit 1; }

NEXT_REF="$(rg 'button "(下一步|Next)".*\[ref=e[0-9]+' "$SNAP4" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEXT_REF" ] || { echo '找不到裁切页下一步按钮 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP5"

# 步骤5：編輯页 -> 下一步
rg -q '編輯|Edit' "$SNAP5" || { echo '没有进入編輯页'; exit 1; }

NEXT_REF2="$(rg 'button "(下一步|Next)".*\[ref=e[0-9]+' "$SNAP5" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEXT_REF2" ] || { echo '找不到編輯页下一步按钮 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEXT_REF2"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP6"

# 步骤6：建立新貼文 compose 页 -> 填 caption -> 分享
rg -q '建立新貼文|Create new post' "$SNAP6" || { echo '没有进入建立新貼文 compose 页'; exit 1; }

CAPTION_REF="$(rg 'textbox ".*(撰寫說明|Write a caption|說明文字).*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$CAPTION_REF" ] || CAPTION_REF="$(rg 'textbox .*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$CAPTION_REF" ] || { echo '找不到 caption 输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CAPTION_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$CAPTION_REF" "$POST_TEXT" --slowly

SHARE_REF="$(rg 'button "(分享|Share)".*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$SHARE_REF" ] || { echo '找不到 分享 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$SHARE_REF"
# 先等 5 秒，Instagram 会先显示 "分享中" dialog，完成后变为 "已分享貼文"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 5000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$VERIFY"

# 如果仍在 "分享中"，再等 5 秒
if rg -q '分享中|Sharing' "$VERIFY" && ! rg -q '已分享貼文|Post shared' "$VERIFY"; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 5000
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$VERIFY"
fi

if rg -q '已分享貼文|Post shared|已分享你的貼文|Your post has been shared' "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '分享按钮已点击，但没有看到成功确认，建议人工复核'
fi
```

### 标准模板：多图发帖

```bash
PROFILE='chrome-relay'
OPENCLAW_BIN='/Users/openclawcn/.homebrew/bin/openclaw'
if [ -d "$HOME/.openclaw/workspace/skills/social-push" ]; then
  SKILL_ROOT="$HOME/.openclaw/workspace/skills/social-push"
else
  SKILL_ROOT="$HOME/.openclaw/skills/social-push"
fi
POST_TEXT='把这里替换成你的贴文文案'
IMAGE_PATHS=(
  '/绝对路径/图片1.jpg'
  '/绝对路径/图片2.jpg'
)

STAGE_SH="$SKILL_ROOT/scripts/stage_upload_media.sh"
CLEAN_SH="$SKILL_ROOT/scripts/cleanup_staged_media.sh"

find_instagram_tab() {
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" tabs | sed -n '/https:\/\/www\.instagram\.com\//{n;s/^ *id: //p;}' | tail -n1
}

TARGET_ID="$(find_instagram_tab)"
if [ -z "$TARGET_ID" ]; then
  OPEN_OUT="$("$OPENCLAW_BIN" browser --browser-profile "$PROFILE" open 'https://www.instagram.com/')"
  TARGET_ID="$(printf '%s\n' "$OPEN_OUT" | sed -n 's/^id: //p')"
fi
[ -n "$TARGET_ID" ] || { echo '拿不到 Instagram tab id'; exit 1; }
[ "${#IMAGE_PATHS[@]}" -ge 2 ] || { echo '多图模板至少需要 2 张图片，单图请用单图模板'; exit 1; }

STAGED_PATHS=()
cleanup() {
  [ "${#STAGED_PATHS[@]}" -gt 0 ] && bash "$CLEAN_SH" "${STAGED_PATHS[@]}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SNAP1="/tmp/ig-home-$$.txt"
SNAP2="/tmp/ig-menu-$$.txt"
SNAP3="/tmp/ig-upload-$$.txt"
SNAP4="/tmp/ig-crop-$$.txt"
SNAP5="/tmp/ig-edit-$$.txt"
SNAP6="/tmp/ig-compose-$$.txt"
VERIFY="/tmp/ig-verify-$$.txt"

check_carousel_state() {
  local SNAP_PATH="$1"
  local STAGE_NAME="$2"
  if rg -Eq '向右雙箭頭|右雙箭頭|左雙箭頭|左箭頭|右箭頭|上一張|下一張|左右箭頭|雙箭頭|Right double arrow|Double arrow|Right arrow|Left arrow|Chevron|Carousel|carousel|Next|Previous|Prev' "$SNAP_PATH"; then
    return 0
  fi
  local EVAL_OUT="/tmp/ig-carousel-${STAGE_NAME}-$$.txt"
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" evaluate --target-id "$TARGET_ID" --fn '() => Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button")).map((el) => (el.getAttribute("aria-label") || el.textContent || "").trim()).filter(Boolean)' >"$EVAL_OUT"
  rg -Eq '向右雙箭頭|右雙箭頭|左雙箭頭|左箭頭|右箭頭|上一張|下一張|左右箭頭|雙箭頭|Right double arrow|Double arrow|Right arrow|Left arrow|Chevron|Carousel|carousel|Next|Previous|Prev|Arrow|箭頭' "$EVAL_OUT"
}

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" focus "$TARGET_ID"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" navigate --target-id "$TARGET_ID" 'https://www.instagram.com/'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 3000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$SNAP1"

# 步骤1：点击 "新貼文"（link，不是 button）
NEW_POST_REF="$(rg '(link|button) ".*(新貼文|New post).*\[ref=e[0-9]+' "$SNAP1" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEW_POST_REF" ] || { echo '找不到 新貼文 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEW_POST_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP2"

# 步骤2：点击 "貼文"（link，不是 button）
POST_TYPE_REF="$(rg '(link|button) ".*(貼文 貼文|貼文|Post).*\[ref=e[0-9]+' "$SNAP2" | grep -v '新貼文' | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$POST_TYPE_REF" ] || { echo '找不到 貼文 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$POST_TYPE_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 1800
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP3"

# 步骤3：上传所有图片
STAGED_FILES=()
for i in "${!IMAGE_PATHS[@]}"; do
  STAGED_FILES+=("$(bash "$STAGE_SH" "${IMAGE_PATHS[$i]}" "instagram-$((i + 1))")")
done
STAGED_PATHS+=("${STAGED_FILES[@]}")

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --element 'input[type=file][multiple]' "${STAGED_FILES[@]}" || \
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" upload --target-id "$TARGET_ID" --element 'input[type=file]' "${STAGED_FILES[@]}"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time $((3000 + ${#IMAGE_PATHS[@]} * 1500))
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP4"

# 步骤4：裁切页 -> 下一步
rg -q '裁切|Crop' "$SNAP4" || { echo '多图上传后没有进入裁切页'; exit 1; }
check_carousel_state "$SNAP4" "crop" || echo '注意：多图裁切页没有看到 carousel 导航，可能只识别了一张图'

NEXT_REF="$(rg 'button "(下一步|Next)".*\[ref=e[0-9]+' "$SNAP4" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEXT_REF" ] || { echo '找不到裁切页下一步按钮 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEXT_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP5"

# 步骤5：編輯页 -> 下一步
rg -q '編輯|Edit' "$SNAP5" || { echo '多图没有进入編輯页'; exit 1; }

NEXT_REF2="$(rg 'button "(下一步|Next)".*\[ref=e[0-9]+' "$SNAP5" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$NEXT_REF2" ] || { echo '找不到編輯页下一步按钮 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$NEXT_REF2"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 2000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 7000 --out "$SNAP6"

# 步骤6：建立新貼文 compose 页 -> 填 caption -> 分享
rg -q '建立新貼文|Create new post' "$SNAP6" || { echo '多图没有进入建立新貼文 compose 页'; exit 1; }

CAPTION_REF="$(rg 'textbox ".*(撰寫說明|Write a caption|說明文字).*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$CAPTION_REF" ] || CAPTION_REF="$(rg 'textbox .*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$CAPTION_REF" ] || { echo '找不到 caption 输入框 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$CAPTION_REF"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" 'Meta+A'
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" press --target-id "$TARGET_ID" Backspace
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" type --target-id "$TARGET_ID" "$CAPTION_REF" "$POST_TEXT" --slowly

SHARE_REF="$(rg 'button "(分享|Share)".*\[ref=e[0-9]+' "$SNAP6" | sed -E 's/.*\[ref=(e[0-9]+).*/\1/' | head -n1)"
[ -n "$SHARE_REF" ] || { echo '找不到 分享 ref'; exit 1; }

"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" click --target-id "$TARGET_ID" "$SHARE_REF"
# 先等 5 秒，Instagram 会先显示 "分享中" dialog，完成后变为 "已分享貼文"
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 5000
"$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$VERIFY"

# 如果仍在 "分享中"，再等 5 秒（多图上传需要更久）
if rg -q '分享中|Sharing' "$VERIFY" && ! rg -q '已分享貼文|Post shared' "$VERIFY"; then
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" wait --target-id "$TARGET_ID" --time 5000
  "$OPENCLAW_BIN" browser --browser-profile "$PROFILE" snapshot --target-id "$TARGET_ID" --format ai --limit 5000 --out "$VERIFY"
fi

if rg -q '已分享貼文|Post shared|已分享你的貼文|Your post has been shared' "$VERIFY"; then
  echo "发布成功: $POST_TEXT"
else
  echo '分享按钮已点击，但没有看到成功确认，建议人工复核'
fi
```

## 关键提示

- **"新貼文" 和 "貼文" 在 Instagram 侧边栏里是 `link` 元素，不是 `button`** — ref 提取正则必须用 `(link|button)` 兼容两种
- 点击 "貼文" 时需要排除 "新貼文"，用 `grep -v '新貼文'` 过滤
- 隐藏的 `input[type=file]` 在 `snapshot --format ai` 输出里不可见 — 上传必须用 `--element 'input[type=file][multiple]'` CSS selector，不能依赖 `--input-ref`
- 上传可能触发 gateway timeout（20s），但图片仍会成功上传；后续 `wait` + `snapshot` 能正确看到裁切页（upload 命令的 exit code 为 1 时不要直接 exit，继续检查页面状态）
- 点击分享后 Instagram 会先显示 `"分享中"` dialog，不要立刻判断失败；需要多等一轮再 `snapshot` 确认是否变为 `"已分享貼文"`
- 入口顺序固定是：首页 → 点 `新貼文` → 点 `貼文` → `建立新貼文` dialog → 上传 → 裁切 → 編輯 → compose → 分享
- caption 输入框的 placeholder 实测是 `撰寫說明文字……`（繁中）或 `Write a caption...`（英文），提取时优先精确匹配，再退到通用 `textbox` 匹配
- 点击分享后会先出现 `dialog "分享中"` / `Sharing`，等上传完成后才变为 `dialog "已分享貼文"` / `Post shared`
- 发布成功后的确认 dialog 实测标题是 `已分享貼文` / `Post shared`
- 每次经过弹窗、裁切页、編輯页、compose 页后，都要重新 `snapshot`，不要沿用旧 `ref`
- 多图一次性传入所有 staged 路径，不需要逐张上传
- 多图上传等待时间按图片数量动态增加：`3000 + 图片数 * 1500` 毫秒

## 故障恢复

- **找不到 "新貼文" 入口**：重新执行首页 `snapshot`，确认当前标签页真的是 Instagram 首页；如果是 `/create/select/` 等子页面，先 `navigate` 回首页
- **找不到 "貼文" 子菜单项**：说明 "新貼文" 没有正确展开菜单，重新点击 "新貼文" 再 `snapshot`
- **上传后没有进入裁切页**：可能 gateway timeout 但图片未到达；先等 3 秒再重新 `snapshot`；如果仍然没有，重新 stage + upload
- **找不到 caption 输入框**：说明还没进入 compose 页，检查是否跳过了裁切或编辑步骤
- **分享按钮找不到**：先用 `evaluate` 列出当前弹窗所有按钮：

```bash
"$OPENCLAW_BIN" browser --browser-profile chrome-relay evaluate --target-id "$TARGET_ID" --fn '() => Array.from(document.querySelectorAll("[role=dialog] [role=button], [role=dialog] button")).map((el) => ({ label: el.getAttribute("aria-label") || el.textContent?.trim(), disabled: el.getAttribute("aria-disabled") }))'
```

- **弹出 `捨棄貼文？` 确认框**：重新 `snapshot`，找到 `捨棄` / `Discard` 按钮点掉，然后从头开始
- **快照显示登录流程**：不要切换到隔离浏览器，直接在你当前常用浏览器标签页里手动登录，然后从打开 Instagram 首页那一步继续
- **gateway 断连 (1006 abnormal closure)**：先执行 `"$OPENCLAW_BIN" gateway restart`，确认 `"$OPENCLAW_BIN" browser --browser-profile chrome-relay tabs` 恢复正常后再继续
- **tab not found 错误**：relay extension 可能未 attach 到当前标签页，重新执行 `find_instagram_tab` 获取最新 tab id；如果所有 IG tab 都 not found，用 `open` 新建一个
