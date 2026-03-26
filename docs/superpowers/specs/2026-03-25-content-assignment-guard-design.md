# Content Assignment Guard Design

日期：2026-03-25

## 背景

当前仓库已经具备四层能力：

- `social-push`：平台页面自动化发布
- `account-matrix`：账号与验证事实治理
- `matrix-orchestrator`：单节点预检、调度、结果回填
- `openclaw-cluster-orchestrator`：多 worker 路由与 cluster 台账

但“多人多号协作不打架”这件事，当前仍缺一个明确的保护层。

这次聚焦的问题不是：

- 同一账号被多人同时登录占用
- 一个内容批量分发到多个账号

而是两个更具体、也更高频的问题：

1. **同一内容被不同人重复提交并准备发布**
2. **内容虽然有人提前指定了目标账号，但实际发布时跑到了错误账号**

根据当前确认的业务约束，第一版必须满足：

- 不做“一稿多发”
- 每条内容的目标账号由人提前指定
- 如果发现重复内容或发错号，系统默认拦截
- 允许唯一的 OpenClaw 控制人做二次确认后继续
- 一旦出现问题，要先汇报问题，再给出可跳转的页面或定位点

## 本次子项目范围

本设计只覆盖一个聚焦子项目：

- `content-assignment-guard`

它不是新的发帖 skill，也不是完整的团队后台。

它是夹在“任务进入系统”和“真实执行发布”之间的一层**内容指派防撞层**，目标是把：

- 内容唯一性
- 目标账号一致性
- 冲突拦截
- 负责人 override
- 问题定位与跳转

这条链路做成结构化事实，而不是依赖人工记忆。

## 目标

- 确保一条内容在系统内只绑定一个目标账号
- 在任务入队前就发现重复内容冲突
- 在真实发布前再次校验任务账号与浏览器当前账号是否一致
- 对重复内容、账号不匹配、浏览器身份不匹配提供统一冲突模型
- 只允许 OpenClaw 控制人做 override
- 为每次拦截、override、取消留下可审计记录
- 为每次问题提供明确的 `jump_target`
- 尽量复用现有 `matrix-orchestrator` 与 `account-matrix`，不新增重后台

## 非目标

第一版明确不做：

- Web 控制台
- 数据库
- 自动分配目标账号
- 多级角色权限系统
- 审批流引擎
- 内容运营分析面板
- 复杂团队组织树
- 真正的多人同时在线协同编辑

## 为什么不直接做“团队矩阵后台”

“多人多号协作不打架”听起来像权限系统问题，但当前真实冲突点更靠近执行链路：

- 重复内容是否已经被别人占用
- 当前 job 指向的账号是否就是想发的账号
- 当前浏览器里登录的账号是不是任务指定账号

如果一开始就做完整的团队、组织、审批、权限后台，会同时引入：

- 角色模型
- 组织层级
- UI
- 持久化设计
- 审批与通知系统

这些都会让第一阶段失焦。

因此第一版不直接做“大团队矩阵平台”，而是先做一个能真实挡住误发和重复发的执行保护层。

## 方案比较

### 方案 A：只在发布前给出提示

做法：

- 在 `matrix-orchestrator` 预检里多输出几条 warning
- 让操作人自行判断是否继续

优点：

- 改动最小
- 上手最快

缺点：

- 只能“提醒”，不能真正防撞
- 容易被忽略
- 不能形成可审计的冲突记录

### 方案 B：增加内容指派防撞层

做法：

- 在任务入队时为内容生成唯一指纹
- 用单独台账记录内容已被哪个账号占用
- 在预检阶段再次核对账号与浏览器身份
- 冲突默认阻断，只允许控制 OpenClaw 的人 override

优点：

- 能直接挡住重复发和发错号
- 与现有 `matrix-orchestrator` 责任最匹配
- 不需要先上数据库
- 后续可以自然演进到运营矩阵与权限系统

缺点：

- 需要新增台账、状态机和 override 语义
- 需要定义“内容重复”的规范化算法

### 方案 C：直接做完整团队权限系统

做法：

- 引入团队、角色、审批、工作台、任务中心

优点：

- 长期看最完整

缺点：

- 当前过重
- 会显著拖慢已有执行链路演进
- 很容易先做出后台壳子，反而没把误发问题解决掉

## 结论

采用：

- **方案 B**

第一版将其定义为：

- **基于台账的内容指派防撞层**

并且：

- 不新建独立大 skill
- 主要作为 `matrix-orchestrator` 的新预检与写账能力落地
- `openclaw-cluster-orchestrator` 保持只管路由，不承担业务冲突判断

## 一句话架构

`content-assignment-guard` = 内容指纹生成器 + 内容占用台账 + 冲突记录器 + operator override 记录器 + 发布前账号一致性守门员

## 系统分层

后续链路分为五层：

### 1. Submitter Layer

外部提交者把内容和目标账号交给系统。

第一版不要求提交者直接操作 OpenClaw，也不要求他们拥有发布权限。

### 2. Governance Layer

由现有 `account-matrix` 提供：

- 哪个平台有哪些账号
- 账号显示名
- 哪些内容形态已验证

### 3. Assignment Guard Layer

本设计新增：

- 内容唯一性检查
- 目标账号一致性检查
- 浏览器当前账号一致性检查
- 冲突落账
- operator override 落账

### 4. Node Dispatch Layer

由现有 `matrix-orchestrator` 继续提供：

- 读取 job
- 调 preflight
- 调用 `social-push`
- 写 `result-ledger` / `run-log`

### 5. Cluster Control Layer

由现有 `openclaw-cluster-orchestrator` 提供：

- worker 路由
- 节点级台账

Cluster 层不直接判断内容冲突；它只负责把任务交给正确节点。

## 第一版目录与文件设计

第一版不新建顶级 skill 目录，直接在运行时文档中增加三类文件：

```text
docs/ops/
├── content-assignment-ledger.md
├── conflict-ledger.md
└── operator-override-ledger.md
```

并在 `matrix-orchestrator/` 内新增对应模板与脚本接入点。

### 1. `docs/ops/content-assignment-ledger.md`

用途：

- 记录“某条内容已经被哪个目标账号占用”

建议字段：

| 字段 | 说明 |
|---|---|
| `assignment_id` | 指派记录唯一 ID |
| `submission_ref` | 外部提交来源引用，如工单、消息 ID |
| `content_fingerprint` | 内容规范化指纹 |
| `platform` | 目标平台 |
| `account_alias` | 指定目标账号 |
| `content_type` | 内容形态 |
| `job_id` | 对应运行任务 ID |
| `status` | `reserved` / `queued` / `running` / `published` / `blocked` / `cancelled` |
| `notes` | 备注 |
| `created_at` | 创建时间 |

### 2. `docs/ops/conflict-ledger.md`

用途：

- 记录所有阻断型冲突

建议字段：

| 字段 | 说明 |
|---|---|
| `conflict_id` | 冲突唯一 ID |
| `assignment_id` | 关联内容指派记录 |
| `job_id` | 关联任务 ID |
| `conflict_type` | `duplicate_content` / `target_account_mismatch` / `browser_identity_mismatch` |
| `severity` | `block` |
| `status` | `open` / `overridden` / `cancelled` / `resolved` |
| `summary` | 问题摘要 |
| `requested_account` | 任务指定账号 |
| `observed_account` | 实际识别账号 |
| `jump_target` | 浏览器 URL 或本地定位点 |
| `notes` | 补充说明 |
| `timestamp` | 发生时间 |

### 3. `docs/ops/operator-override-ledger.md`

用途：

- 记录控制 OpenClaw 的人做过哪些 override

建议字段：

| 字段 | 说明 |
|---|---|
| `override_id` | override 唯一 ID |
| `conflict_id` | 对应冲突 ID |
| `job_id` | 关联任务 ID |
| `action` | `continue_once` / `cancel_job` |
| `operator_ref` | 控制 OpenClaw 的人或入口标识 |
| `reason` | override 原因 |
| `timestamp` | 操作时间 |

## 为什么第一版不单独建 `docs/team/`

当前已确认的 override 权限只有一个来源：

- 控制 OpenClaw 的人

在这种约束下，第一版不需要复杂团队、成员、角色、组织层级表。

真正的“团队矩阵”在这里先收缩成：

- 谁提交内容并不决定谁有 override 权限
- 真正有发布最终控制权的人只有一个 operator

因此：

- `团队矩阵` 第一阶段先落在“内容指派与冲突控制”
- 等后续出现多个 operator、多个品牌 owner、多个 reviewer 时，再抽 `docs/team/` 和正式权限模型

## 核心标识设计

### 1. `content_fingerprint`

这是第一版最关键的键。

建议由以下内容规范化后生成：

- `content_type`
- `title`
- `body`
- `media_paths` 或媒体文件稳定摘要

第一版**不把 `platform` 和 `account_alias` 纳入指纹**。

原因：

- 当前已经确认“不做一稿多发”
- 同一份内容即使目标账号不同，也应视为潜在冲突

也就是说，第一版把“内容是否重复”定义为：

- **只看内容本体，不看目标账号**

### 2. `assignment_id`

每次内容进入系统时生成。

它代表：

- 这次提交动作本身

即使两次提交内容相同，也必须有不同 `assignment_id`，然后由系统用 `content_fingerprint` 判断冲突。

### 3. `jump_target`

第一版所有问题都必须带一个可跳转目标。

优先级建议为：

1. 当前浏览器页面 URL
2. 目标平台发帖页 URL
3. 对应冲突 ledger 或 queue 文件定位

如果运行环境暂时不支持自动 browser deep-link，至少也要提供明确 URL 或文件路径。

## 生命周期设计

### 阶段 1：内容进入系统

提交者提供：

- 目标平台
- 目标账号
- 内容形态
- 文本与媒体
- 外部来源引用

系统动作：

1. 生成 `assignment_id`
2. 计算 `content_fingerprint`
3. 查询 `content-assignment-ledger.md`

如果发现已有未终止记录使用同一 `content_fingerprint`：

- 不创建可运行 job
- 写 `conflict-ledger.md`
- 返回 `duplicate_content`

如果没有冲突：

- 创建 assignment 记录，状态为 `reserved`
- 创建 job
- assignment 状态推进为 `queued`

### 阶段 2：节点内预检

`matrix-orchestrator` 在原有验证矩阵检查之外，再增加三类校验：

1. `job.account_alias` 是否等于 assignment 指定账号
2. assignment 是否仍然是当前唯一有效占用记录
3. 浏览器当前识别出的账号是否与 `account-matrix` 中该账号一致

如果 `job.account_alias` 与 assignment 不一致：

- 记为 `target_account_mismatch`
- job 进入 `blocked`

如果浏览器当前账号与期望显示名不一致：

- 记为 `browser_identity_mismatch`
- job 进入 `blocked`

### 阶段 3：operator 处理冲突

发生冲突后，系统必须输出结构化问题摘要：

- `conflict_id`
- `job_id`
- `assignment_id`
- `conflict_type`
- `requested_account`
- `observed_account`
- `summary`
- `jump_target`

OpenClaw 控制人收到问题后，只能做两个动作：

- `continue_once`
- `cancel_job`

### 阶段 4：override 后继续

如果 operator 选择 `continue_once`：

1. 写 `operator-override-ledger.md`
2. 该 override 只对当前 `conflict_id + job_id + attempt_no` 生效
3. 重新执行同一 job

第一版 override 不允许全局豁免，也不允许永久关闭某类校验。

### 阶段 5：终态

终态应同步体现在两个地方：

- `content-assignment-ledger.md`
- 原有 `result-ledger.md`

推荐终态含义：

- `published`：真实发布完成
- `blocked`：被冲突或校验阻断
- `cancelled`：operator 取消

## 状态模型

### `content-assignment-ledger` 状态

- `reserved`
- `queued`
- `running`
- `published`
- `blocked`
- `cancelled`

### `conflict-ledger` 状态

- `open`
- `overridden`
- `cancelled`
- `resolved`

### `operator-override-ledger` 动作

- `continue_once`
- `cancel_job`

## 与现有系统的接入点

### 1. `account-matrix`

继续提供：

- `platform + account_alias`
- `display_name`
- `browser_profile`

本设计不会把账号事实再复制一份。

### 2. `matrix-orchestrator`

这是第一版的主要接入点。

建议新增能力：

- 生成或读取 `content_fingerprint`
- 读取 `docs/ops/content-assignment-ledger.md`
- 在预检阶段增加重复内容与账号一致性校验
- 冲突时写 `docs/ops/conflict-ledger.md`
- 接受一个显式 override 输入

### 3. `openclaw-cluster-orchestrator`

保持最小改动：

- cluster job 可以携带 `assignment_id` 与 `content_fingerprint`
- 但 cluster 层不解释这些字段的业务含义
- 真正的阻断判断仍在 node-local `matrix-orchestrator`

### 4. `social-push`

不修改发布 workflow 本体。

唯一新增要求是：

- 在可行时返回当前页面 URL、当前识别账号或可定位信息，供 `jump_target` 使用

## 页面跳转策略

用户明确要求“遇到问题先汇报，再跳转到页面”，因此第一版必须定义跳转策略。

建议策略：

### 场景 A：浏览器身份不匹配

跳转目标：

- 当前已打开的目标平台页面 URL

目的：

- 让 operator 直接看到当前登录的是谁

### 场景 B：任务账号与 assignment 不匹配

跳转目标：

- 该 job 对应的 queue / ledger 文件位置

目的：

- 让 operator 先定位是 job 写错了，还是 assignment 写错了

### 场景 C：重复内容

跳转目标：

- 首条占用该 `content_fingerprint` 的 assignment 记录

目的：

- 让 operator 快速判断是重复提交，还是新任务应该取消旧任务

## 审计要求

第一版的所有高风险动作都必须可追踪：

- 谁先占用了内容
- 哪次 job 被拦
- 为什么被拦
- 谁 override
- override 的理由是什么

不允许“口头确认后继续，但系统里没有记录”。

## 测试策略

第一版测试重点不在页面操作，而在状态机和台账正确性：

### 单元测试

- 相同内容生成相同 `content_fingerprint`
- 目标账号不同但内容相同，仍判为重复冲突
- 已 `cancelled` 的 assignment 不再阻塞新任务
- `target_account_mismatch` 正确阻断
- `browser_identity_mismatch` 正确阻断
- override 只对单次 job attempt 生效

### 集成测试

- 内容入队成功后，assignment 与 job 同步创建
- 冲突发生时，queue / conflict-ledger / override-ledger 状态一致
- operator `continue_once` 后允许同一 job 再跑一次
- `cancel_job` 后 assignment 进入 `cancelled`

### 手工验证

- 构造两条内容完全相同、目标账号不同的任务，确认第二条被阻断
- 构造 job 指向 `main`，但浏览器实际登录 `alt`，确认被阻断并返回 `jump_target`
- 执行一次 operator override，确认只对本次任务有效

## 演进边界

如果后续出现以下需求，再进入下一阶段：

- 多个 operator
- 平台 owner 与品牌 owner 分离
- reviewer 审核后才能 override
- 团队与组织层级
- 审批流

到那时再抽出真正的：

- `docs/team/`
- 权限模型
- 团队矩阵 skill

而不是在第一版提前做重。

## 一句话总结

当前“多人多号协作不打架”的最小可行解，不是先做权限后台，而是先做：

- **内容唯一指派**
- **发布前账号一致性拦截**
- **唯一 operator override**
- **带 jump target 的冲突汇报**

把这条链路跑通后，后续的团队矩阵、运营矩阵、数据矩阵、权限组织都会有真实事实可依附。
