# Account Matrix Skill Design

日期：2026-03-23

## 背景

当前仓库里的 `social-push` 已经逐步沉淀了平台 workflow、真实联调结果和部分经验规则，但“账号台账”和“验证状态”仍然散落在 README、GUIDE、参考文件和对话记忆中。

为了避免继续把账号信息、验证状态和发布逻辑耦合进 `social-push` 本体，本设计新增一个 **独立 skill**，专门负责：

- 账号矩阵模板
- 验证矩阵模板
- 发布前账号/验证状态检查规则

该 skill 作为当前仓库内的独立目录存在，**不修改现有 `social-push` 的运行逻辑**，也不替代它的发布功能。

## 目标

- 在当前仓库内新增一个独立 skill 目录，例如 `account-matrix/`
- 该 skill 只负责账号与验证事实管理，不直接发帖
- 提供两份可复用模板：
  - 账号矩阵
  - 验证矩阵
- 让未来的 agent 能在需要时触发这个 skill，先查“哪个平台用哪个号、哪个形态验证到了哪一步”

## 非目标

- 不改变现有 `social-push` 的平台路由与发布行为
- 不把真实账号信息写死进模板
- 不在这个 skill 里直接执行浏览器发布
- 不做数据库或自动同步系统

## 方案选型

本次已比较过 3 条路线：

### 方案 A：独立 skill 目录

在仓库根目录新建平级目录：

```text
account-matrix/
```

优点：

- 和 `social-push` 边界清晰
- 不会污染现有发布 skill 的职责
- 以后可以单独安装、移动、演化

缺点：

- 需要维护一份新的 skill 元数据和模板文件

### 方案 B：只放 docs 模板

只在 `docs/` 下新增矩阵模板，不做 skill。

优点：

- 结构最轻

缺点：

- 不能被 skill 触发机制直接使用
- 后续 agent 很难稳定发现它

### 方案 C：继续塞进 social-push

把账号矩阵和验证矩阵直接做成 `social-push` 的一部分。

优点：

- 文件集中

缺点：

- 发布逻辑与账号治理再次耦合
- 后续越改越重，职责边界会持续恶化

### 结论

采用 **方案 A：独立 skill 目录**。

## 目录设计

计划新增：

```text
account-matrix/
├── SKILL.md
└── templates/
    ├── account-matrix.md
    ├── verification-matrix.md
    └── preflight-checklist.md
```

如后续需要再扩展：

```text
account-matrix/
├── SKILL.md
├── templates/
│   ├── account-matrix.md
│   ├── verification-matrix.md
│   └── preflight-checklist.md
└── references/
    └── status-definitions.md
```

第一版先不新增 `references/`，避免过度设计。

## 安装与使用方式

该 skill 在当前仓库中以独立目录存在，但**不会因为目录存在就自动变成可发现 skill**。第一版明确支持的使用方式只有一种：

1. 当前仓库中的 `account-matrix/` 作为源码目录维护
2. 真正安装时，将该目录单独复制或软链接到：

```text
~/.openclaw/skills/account-matrix
```

也就是说：

- 仓库中的 `account-matrix/` 是维护源
- `~/.openclaw/skills/account-matrix` 是运行时安装位置

更新约定：

- 如果安装方式是软链接，仓库改动会即时反映到安装位置
- 如果安装方式是复制，后续每次更新都需要重新复制到 `~/.openclaw/skills/account-matrix`

第一版不依赖 nested skills 自动发现机制，也不要求改动现有 `social-push` 安装路径。

## Skill 职责

### 1. 账号矩阵模板

记录“哪个平台默认用哪个账号”的基础事实。

建议字段：

| 字段 | 说明 |
|------|------|
| `account_alias` | 内部简称，如 `main` / `alt` / `brand` |
| `platform` | 平台名，如 `zhihu` / `reddit` |
| `display_name` | 页面上能看到的账号名 |
| `browser_profile` | 当前浏览器控制方案，如 `chrome-relay` |
| `default` | 是否该平台默认账号 |
| `notes` | 备注，如“仅用于测试图帖” |

### 2. 验证矩阵模板

记录“这个账号在这个平台的这个内容形态，验证到哪一步”。

建议字段：

| 字段 | 说明 |
|------|------|
| `platform` | 平台名 |
| `account_alias` | 对应账号简称 |
| `content_type` | 内容形态，如 `article` / `idea` / `text_post` / `image_post` |
| `status` | 验证状态 |
| `last_verified` | 最后验证日期 |
| `evidence` | 证据，如 URL、content id、API 200 |
| `notes` | 备注，如“提交流程已验证但被过滤” |

### 3. 发布前检查规则

该 skill 不发帖，但要提醒后续 agent：

- 发布前先确认当前平台默认账号
- 发布前先检查当前内容形态是否真实验证过
- 如果某形态只到“提交流程已验证”，不要对外误报为“已成功”

第一版将这部分规则落为一个明确文件：

```text
account-matrix/templates/preflight-checklist.md
```

这样“检查规则”不再只是抽象描述，而是一个固定模板产物。

## 状态词设计

为避免不同文件里出现混乱表述，验证矩阵统一使用以下状态：

| 状态 | 含义 |
|------|------|
| `workflow_only` | 只有 workflow，未做页面级验证 |
| `page_verified` | 页面入口与控件可见性已验证 |
| `submit_ok` | 提交流程已验证 |
| `real_publish_ok` | 真实发布成功 |
| `submit_ok_filtered` | 提交成功，但被平台/社区过滤移除 |

第一版模板只定义这些状态，不额外发明更多词。

并且这些状态不会只停留在设计文档中，第一版必须同时写进：

- `account-matrix/SKILL.md`
- `account-matrix/templates/verification-matrix.md`

这样后续填写模板时不会漂出新的状态词。

## 平台与内容形态枚举

为避免模板刚上线就出现 `reddit` / `Reddit` / `reddit-text` / `text_post` 这类漂移，第一版要在模板中冻结最小枚举。

### platform 推荐值

- `zhihu`
- `reddit`
- `x`
- `threads`
- `facebook`
- `xiaohongshu`
- `weibo`
- `wechat-official-account`
- `juejin`
- `instagram`

### content_type 推荐值

- `article`
- `column`
- `idea`
- `text_post`
- `image_post`
- `link_post`
- `longform`
- `short_post`

这些值第一版只作为模板内的“Allowed values”说明，不要求代码校验，但要求写死在模板头部。

命名对齐原则：

- 第一版推荐与 `social-push` 中的命名保持一致
- 但 `account-matrix` 不直接导入 `social-push` 文件
- 如果后续出现命名差异，应通过显式映射处理，而不是隐式依赖

## Skill 触发条件

`SKILL.md` 的描述应聚焦在这些触发场景：

- 用户想维护账号台账
- 用户想记录某个平台/某账号的验证状态
- 用户想在发布前确认“哪个账号是默认账号”
- 用户想确认“某个内容形态到底有没有真实验证过”

这个 skill **不**应该在“直接发帖”场景下抢 `social-push` 的触发。

## 与 social-push 的关系

`account-matrix` 和 `social-push` 的职责拆分如下：

| 能力 | account-matrix | social-push |
|------|----------------|------------|
| 维护账号模板 | 是 | 否 |
| 维护验证状态模板 | 是 | 否 |
| 选择账号策略 | 提供模板与规则 | 可参考，但不依赖 |
| 浏览器自动发帖 | 否 | 是 |
| 平台 workflow | 否 | 是 |

关键原则：

- `account-matrix` 提供事实模板
- `social-push` 继续负责发布
- 第一版两者之间不建立强依赖
- 两者只做“推荐对齐”，例如平台名和内容形态命名尽量保持一致，但 `account-matrix` 不直接导入或读取 `social-push` 文件

## 实现边界

第一版只实现：

- 独立目录
- 一个最小可触发的 `SKILL.md`
- 三份模板文件

即：

- `templates/account-matrix.md`
- `templates/verification-matrix.md`
- `templates/preflight-checklist.md`

第一版不实现：

- 模板自动填充脚本
- 账号校验脚本
- 和 `social-push` 的联动逻辑

## 验证方式

该 skill 是模板型 skill，第一版验证重点是：

1. 目录结构清晰
2. `SKILL.md` 触发描述准确
3. 三份模板字段完整且无真实账号信息
4. 不修改现有 `social-push` 文件

## 预期成果

完成后，仓库中会多一个可以独立存在的 skill：

- 名称建议：`account-matrix`
- 作用：账号与验证状态治理
- 风格：模板版，不带真实账号，不影响现有发布功能

后续如果需要，再基于它扩展“发布前账号确认”或“验证矩阵自动更新”。
