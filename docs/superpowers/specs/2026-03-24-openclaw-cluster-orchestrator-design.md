# OpenClaw Cluster Orchestrator Design

日期：2026-03-24

## 背景

当前仓库已经具备三层能力：

- `social-push`：多平台真实发布执行层
- `account-matrix`：账号与验证事实治理层
- `matrix-orchestrator`：单节点预检、调度、结果回填层

但这些能力目前仍然主要围绕**单个 OpenClaw gateway / 单个执行节点**工作。

本项目的目标已经从“做一个传统矩阵 SaaS 后台”转向：

- 用 OpenClaw 自己做协作网络
- 允许一个主控 OpenClaw 协调多个执行 OpenClaw
- 让不同节点按平台、账号组、浏览器环境分工执行

也就是说，后续系统的重点不是单纯“多平台发帖”，而是：

- **主控层**
- **节点层**
- **分发层**
- **结果汇总层**

## 本次子项目范围

本设计只覆盖一个聚焦子项目：

- `openclaw-cluster-orchestrator`

这是一个新的独立 skill / CLI，用于把“单节点矩阵调度”升级为“OpenClaw 协作调度”。

第一版不直接上来做完整跨机器平台，而是采用：

- **逻辑上按主控 + 多 worker 节点设计**
- **实现上先用单 gateway 多 agent 跑通**
- **接口上从第一天就保留扩展到多 gateway / 多机器的边界**

这意味着第一版是：

- `remote-ready`
- 但不是完整的多机集群产品

## 目标

- 在当前仓库新增独立目录：
  - `openclaw-cluster-orchestrator/`
- 让一个主控 OpenClaw 能基于节点矩阵选择合适 worker
- 支持按平台、账号别名、能力标签分发任务
- 将 worker 执行结果回写到统一运行台账
- 与现有 `matrix-orchestrator`、`social-push`、`account-matrix` 清晰分层
- 第一版先支持：
  - 单 gateway
  - 多 agent
  - 主控 agent 调度 worker agent

## 非目标

第一版明确不做：

- Web 控制台
- 账号指标采集面板
- 权限中心
- 完整的多机器发现协议
- 节点自动弹性伸缩
- 真正的分布式一致性 / 数据库
- 复杂审批流

## 为什么不直接做“多个 OpenClaw 实例互控”

虽然最终目标是“一个 OpenClaw 控多个 OpenClaw”，但第一版如果直接做跨机器互控，会同时引入这些变量：

- 节点注册
- 网络连通
- 远程认证
- 远程 session 管理
- 版本同步
- 故障恢复

这会让第一阶段很容易失焦。

因此第一版采用：

- **同一个 gateway 内多 agent 模拟多节点**

这样可以先验证最重要的控制面问题：

- 节点选择是否合理
- 任务分发模型是否稳定
- 结果回传结构是否足够
- 失败重试与台账是否成立

一旦这些成立，后面再把“本地 agent 节点”替换为“远程 OpenClaw 节点”，成本会低很多。

## 方案比较

### 方案 A：继续增强现有 `matrix-orchestrator`

把节点调度直接继续塞进 `matrix-orchestrator/`。

优点：

- 目录少
- 上手快

缺点：

- 会把“单节点矩阵调度”和“集群控制面”耦合到一起
- 后续跨 gateway / 跨机器时边界会很快变脏

### 方案 B：新建独立 `openclaw-cluster-orchestrator/`

优点：

- 边界清楚
- 可以显式定义节点矩阵、分发契约、结果回收契约
- 与现有 `matrix-orchestrator` 保持上下层关系

缺点：

- 需要维护新的 skill 文档、模板和脚本

### 方案 C：直接做多 gateway 分布式版本

优点：

- 一步到位

缺点：

- 变量过多
- 调试成本高
- 很难先把控制面抽象做对

## 结论

采用：

- **方案 B**
- 并以 **“单 gateway 多 agent 模拟主控 + 多 worker”** 作为第一版实现策略

## 系统分层

后续系统分为四层：

### 1. Publish Skill Layer

由 `social-push` 提供：

- 页面自动化
- 平台 workflow
- 浏览器操作

### 2. Governance Layer

由 `account-matrix` 提供：

- 账号矩阵
- 验证矩阵
- 发布前检查规则

### 3. Node Dispatch Layer

由现有 `matrix-orchestrator` 提供单节点任务调度能力：

- 读取 job
- 预检
- 调用 `social-push`
- 写 ledger / run-log / verification

### 4. Cluster Control Layer

由新建 `openclaw-cluster-orchestrator` 提供：

- 节点选择
- worker 分发
- 节点健康检查
- 节点级运行记录
- 将任务路由到正确的 OpenClaw agent / 节点

## 一句话架构

`openclaw-cluster-orchestrator` = 节点矩阵读取器 + worker 选择器 + 任务分发器 + 节点结果汇总器

## 第一版目录设计

```text
openclaw-cluster-orchestrator/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── dispatch-contract.md
├── templates/
│   ├── node-matrix.md
│   ├── cluster-job-queue.md
│   ├── cluster-result-ledger.md
│   └── cluster-run-log.md
└── scripts/
    ├── load_node_matrix.py
    ├── select_worker.py
    ├── dispatch_to_worker.py
    ├── append_cluster_result_ledger.py
    ├── append_cluster_run_log.py
    └── run_next_cluster_job.py
```

对应运行时文件：

```text
docs/cluster/
├── node-matrix.md
├── cluster-job-queue.md
├── cluster-result-ledger.md
└── cluster-run-log.md
```

## 核心数据模型

### 1. Node Matrix

记录“有哪些 OpenClaw worker 节点，以及它们能做什么”。

建议字段：

| 字段 | 含义 |
|---|---|
| `node_id` | 节点唯一标识，如 `worker-zhihu-01` |
| `mode` | `local_agent` / `remote_gateway` |
| `agent_id` | 单 gateway 场景下对应的 agent id |
| `gateway_endpoint` | 远程 gateway 地址，第一版可空 |
| `platforms` | 节点支持的平台列表 |
| `account_aliases` | 节点可操作的账号别名 |
| `browser_profiles` | 可使用的浏览器控制方式 |
| `capabilities` | 如 `publish`, `collect_metrics`, `risk_check` |
| `status` | `ready`, `paused`, `offline` |
| `notes` | 备注 |

第一版重点使用：

- `node_id`
- `mode`
- `agent_id`
- `platforms`
- `account_aliases`
- `capabilities`
- `status`

### 2. Cluster Job Queue

记录待分发到 worker 节点的任务。

建议字段：

| 字段 | 含义 |
|---|---|
| `job_id` | 集群任务 id |
| `attempt_no` | 当前 cluster 级调度尝试次数 |
| `job_type` | `publish`, `collect_metrics`, `risk_check` |
| `platform` | 目标平台 |
| `account_alias` | 目标账号别名 |
| `content_type` | 内容形态 |
| `preferred_node` | 可选指定节点 |
| `payload_json` | 标准化任务载荷 |
| `status` | `pending`, `routing`, `running`, `done`, `failed`, `blocked` |
| `notes` | 备注 |

第一版只要求稳定支持：

- `publish`

其他 `job_type` 先预留，不实现实际执行。

### 3. Cluster Result Ledger

记录每次任务被哪个 worker 接走、结果是什么。

建议字段：

| 字段 | 含义 |
|---|---|
| `job_id` | 任务 id |
| `attempt_no` | 当前 cluster 级调度尝试次数 |
| `node_id` | 实际执行节点 |
| `agent_id` | 实际执行 agent |
| `job_type` | 任务类型 |
| `result_status` | 结果状态 |
| `evidence` | 证据 |
| `notes` | 说明 |
| `timestamp` | 时间 |

### 4. Cluster Run Log

记录路由与节点交互过程事件。

建议字段：

| 字段 | 含义 |
|---|---|
| `job_id` | 任务 id |
| `attempt_no` | 当前 cluster 级调度尝试次数 |
| `node_id` | 关联节点，可空 |
| `event` | 事件名 |
| `status` | 当前事件状态 |
| `notes` | 备注 |
| `timestamp` | 时间 |

建议事件：

- `job_started`
- `worker_selected`
- `dispatch_started`
- `dispatch_finished`
- `ledger_updated`

## Cluster 状态机

第一版 cluster queue 使用固定状态流转：

```text
pending -> routing -> running -> done
pending -> routing -> blocked
pending -> routing -> failed
pending -> routing -> running -> failed
```

说明：

- `pending`
  - 尚未开始路由
- `routing`
  - 已进入 worker 选择阶段，但还未把任务交给 worker
- `running`
  - 已成功派发给 worker，并正在等待 worker 终态结果
- `done`
  - worker 返回成功终态，如 `publish_ok` 或 `publish_filtered`
- `blocked`
  - 主控无法找到合法 worker，或被 routing 规则显式拦截
- `failed`
  - 已选到 worker，但派发失败或 worker 返回失败终态

第一版 cluster ledger 的 `result_status` 允许值固定为：

- `routing_blocked`
- `dispatch_error`
- `runner_error`
- `preflight_blocked`
- `publish_ok`
- `publish_filtered`
- `publish_failed`

映射规则：

- 主控找不到可用 worker
  - queue `status = blocked`
  - ledger `result_status = routing_blocked`
- 主控调 worker agent 失败
  - queue `status = failed`
  - ledger `result_status = dispatch_error`
- worker 返回 `preflight_blocked`
  - queue `status = blocked`
  - ledger `result_status = preflight_blocked`
- worker 返回 `publish_ok` / `publish_filtered`
  - queue `status = done`
  - ledger 保持同名状态
- worker 返回 `publish_failed` / `runner_error`
  - queue `status = failed`
  - ledger 保持同名状态

## 节点选择规则

第一版 worker 选择规则保持简单、确定性：

1. 只选 `status = ready` 的节点
2. `capabilities` 必须覆盖任务类型
3. `platforms` 必须匹配目标平台
4. 如果 job 指定了 `account_alias`，节点必须覆盖该账号
5. 如果 job 指定 `preferred_node`，优先该节点
6. 多个节点都可用时，按固定顺序选择：
   - `preferred_node`
   - 精确 `account_alias` 命中
   - `platform` 专属节点
   - 其余 fallback 节点

第一版不做：

- 动态负载均衡
- 打分调度
- 自动抢占

## 调度流程

### 第一版完整链路

1. 主控读取 `docs/cluster/cluster-job-queue.md`
2. 找到下一条 `pending` job
3. 读取 `docs/cluster/node-matrix.md`
4. 选出 worker 节点
5. 将标准化任务分发给对应 worker agent
6. worker agent 内部继续调用现有 `matrix-orchestrator` 或 `social-push`
7. 主控等待 worker 返回终态结果
8. 写入 `cluster-result-ledger.md`
9. 写入 `cluster-run-log.md`
10. 更新 cluster queue 终态

## Worker 执行边界

主控层不直接替代 worker 的平台执行逻辑。

第一版 worker 契约固定如下：

- `openclaw-cluster-orchestrator`
  - 负责“把任务派给谁”
- `matrix-orchestrator`
  - 负责“节点内该不该跑、怎么回填节点本地矩阵”
- `social-push`
  - 负责“页面上怎么发”

也就是说：

- cluster orchestrator 不写平台 workflow
- cluster orchestrator 不直接理解页面 ref
- cluster orchestrator 只管理节点级任务路由

### V1 Worker 统一入口

第一版 worker **必须** 通过 `matrix-orchestrator` 执行，不允许同一版本里有的 worker 直接调 `social-push`、有的 worker 走 `matrix-orchestrator`。

统一入口定义为：

- worker agent 接到 cluster job 后
- 只运行一次节点本地 `matrix-orchestrator`
- 由节点本地 `matrix-orchestrator` 再调用 `social-push`

这样第一版只有一个 worker contract，不会在 planning 和 implementation 时产生二义性。

### V1 节点本地运行时目录

为避免多个 worker agent 共享同一组 `docs/matrix/*` 运行时文件，第一版每个 worker 节点都拥有独立 runtime 目录：

```text
docs/nodes/<node_id>/matrix/
├── account-matrix.md
├── verification-matrix.md
├── job-queue.md
├── result-ledger.md
└── run-log.md
```

cluster orchestrator 不直接操作共享的 `docs/matrix/*`。

相反，它会：

1. 把 cluster job 转换成节点本地 job row
2. 写入目标节点自己的 `docs/nodes/<node_id>/matrix/job-queue.md`
3. 调目标 worker agent
4. 由 worker agent 在自己的节点 runtime 内运行：

```bash
python3 matrix-orchestrator/scripts/run_next_job.py \
  --queue docs/nodes/<node_id>/matrix/job-queue.md \
  --account-matrix docs/nodes/<node_id>/matrix/account-matrix.md \
  --verification-matrix docs/nodes/<node_id>/matrix/verification-matrix.md \
  --result-ledger docs/nodes/<node_id>/matrix/result-ledger.md \
  --run-log docs/nodes/<node_id>/matrix/run-log.md
```

### V1 标准化 Worker Payload

cluster orchestrator 发给 worker 的标准化任务载荷，至少包含：

| 字段 | 含义 |
|---|---|
| `job_id` | cluster job id |
| `attempt_no` | cluster 尝试次数 |
| `node_id` | 目标节点 |
| `job_type` | 当前固定为 `publish` |
| `platform` | 平台 |
| `account_alias` | 账号别名 |
| `content_type` | 内容形态 |
| `title` | 标题 |
| `body` | 正文 |
| `media_paths` | 媒体路径 |
| `preferred_node` | 可选偏好节点 |
| `cluster_notes` | cluster 层备注 |

worker 不负责自己重新挑节点，只负责消费这份标准化 payload。

## 分发契约

### 第一版：本地 agent 分发

主控通过 OpenClaw CLI 调用目标 agent：

```bash
"$OPENCLAW_BIN" agent --json --agent <worker-agent-id> -m "<normalized job prompt>"
```

结果必须等待到终态：

- `stop`
- `error`
- `aborted`

不能把中间 commentary 或 `toolUse` 当成最终结果。

### 第二版预留：远程 gateway 分发

后续扩展时，`mode = remote_gateway` 的节点会改为：

- 通过远程 gateway endpoint 调目标 worker
- 仍然复用相同的标准化 job payload

因此第一版的脚本需要把：

- **节点选择**
- **任务分发**

这两层拆开，不要写死为单一本地命令。

## 错误处理

第一版需要显式区分三类失败：

### 1. Routing Failure

没有可用 worker 节点：

- 记为 `blocked`
- 原因如 `no_ready_worker`

### 2. Dispatch Failure

主控调 worker 失败：

- 记为 `dispatch_error`
- 原因如 gateway 不可达、session 超时、worker 不响应

### 3. Worker Execution Failure

worker 收到任务，但实际执行失败：

- 由 worker 返回明确结果
- 如 `publish_failed`

主控只负责把结果准确回填，不擅自改写平台语义。

## 测试策略

第一版至少要覆盖：

### 单元测试

- 节点矩阵解析
- worker 选择规则
- cluster queue 状态流转
- ledger / run-log 追加
- dispatch 终态等待逻辑

### 集成测试

- 用 fake worker runner 模拟：
  - 成功发布
  - 节点不可用
  - worker 超时
  - worker 返回失败

### 手动验证

第一版至少做一次：

- 主控 agent -> worker agent -> `social-push`

的真实闭环验证。

## 成功标准

这个子项目完成的标准不是“看起来像集群”，而是：

1. 单 gateway 下可以稳定跑多 agent 路由
2. 主控能按节点矩阵正确选 worker
3. worker 返回结果后，主控能准确写入 cluster ledger / log
4. 中间态不会被误判为成功
5. 目录与契约已经为未来多 gateway 扩展留好边界

## 这版设计不回答的问题

这些问题后续再独立成 spec：

- 节点自动注册
- 远程 gateway 认证
- 指标采集与可视化
- 热点聚合
- 风险扫描与违规检测
- 竞品监测
- 组织与权限模型

## 一句话总结

`openclaw-cluster-orchestrator` 第一版不是“完整多机集群平台”，而是：

- **一个面向多 OpenClaw 协作的主控层**
- **先用单 gateway 多 agent 把控制面跑通**
- **再把同一套契约扩展到真正的多 gateway / 多机器**
