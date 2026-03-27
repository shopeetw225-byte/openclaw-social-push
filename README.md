# OpenClaw Social-Push

OpenClaw Social-Push 是一个基于浏览器自动化的多平台发布仓库。它复用你已经登录的 Chrome / Chromium 会话，通过 Browser Relay 扩展完成发帖，不依赖各平台官方 API Key。

这个仓库已经不只是单一的 `social-push` skill。当前主线能力包括发布层、账号治理层、节点内调度层和 cluster 主控层，运行状态通过 markdown ledger 管理，适合在本地或小型多 agent 环境里持续演进。

## 项目是什么

- `social-push`：负责真正的浏览器发帖 workflow。
- `account-matrix`：负责账号矩阵、验证矩阵和 preflight 模板。
- `matrix-orchestrator`：负责节点内预检、排队、执行和结果写回。
- `openclaw-cluster-orchestrator`：负责 worker 选择、readiness 检查和 cluster fan-out。
- `docs/` 下的运行时台账：负责记录账号、任务、结果、冲突和节点状态。

## 适合谁

- 需要把同一份内容分发到多个社交平台的运营或实验团队。
- 想用 OpenClaw + 浏览器自动化，而不是平台 API，对接发布流程的人。
- 需要把账号归属、验证状态、任务队列和发布结果留在仓库里协作管理的人。

## 当前能力边界

- 仓库内已经覆盖 `Instagram`、`Threads`、`X/Twitter`、`Facebook`、`小红书`、`微博`、`微信公众号`、`掘金`、`Reddit`、`知乎` 共 10 个平台的 workflow 定义。
- 已有真实或接近真实验证的链路主要是：知乎 `article / idea`、Reddit `text_post`、Instagram 单图、Threads 纯文字 / 单图。
- `cluster` 目前是 V1 形态，重点支持 `publish` 任务、`local_agent` worker、readiness 预检和 retry / requeue。
- 仓库里还带有 `card-preview/` 与 `ai-news-pipeline/` 这两条实验线，但当前最稳定的主路径仍是多平台发布矩阵。

## 快速开始

1. 启动 OpenClaw Gateway。

```bash
openclaw gateway start
curl http://localhost:18789/health
```

2. 安装 Browser Relay 扩展，并在目标标签页把扩展点成 `ON`。

```bash
openclaw browser extension install
openclaw browser snapshot
```

3. 把仓库放到 OpenClaw workspace 里，通常使用 `skills/social-push`。

4. 在 `~/.openclaw/openclaw.json` 里至少配置一个 channel，并确保目标平台账号已经在浏览器里登录。

5. 如果你要跑矩阵 / cluster 流程，继续看根目录的 `GUIDE.md` 和 `docs/cluster/`、`docs/matrix/`。

## 常用命令

```bash
# 浏览器连通性
openclaw gateway start
openclaw browser extension install
openclaw browser --browser-profile chrome-relay tabs

# 节点内预检与执行
python3 matrix-orchestrator/scripts/run_preflight.py --job-json '{"platform":"zhihu","account_alias":"main","content_type":"idea"}'
python3 matrix-orchestrator/scripts/run_next_job.py
python3 matrix-orchestrator/scripts/enqueue_guarded_job.py ...

# Cluster 主控
python3 openclaw-cluster-orchestrator/scripts/cluster_status.py --include-readiness
python3 openclaw-cluster-orchestrator/scripts/run_next_cluster_job.py
python3 openclaw-cluster-orchestrator/scripts/requeue_cluster_job.py --job-id cluster-job-0003

# 本地上传暂存
./scripts/stage_upload_media.sh <source-file> [name-prefix]
./scripts/cleanup_staged_media.sh <staged-file> [staged-file ...]
```

## 仓库结构

```text
README.md
GUIDE.md
SKILL.md
account-matrix/                    账号矩阵与验证模板
matrix-orchestrator/               节点内预检、调度、结果回写
openclaw-cluster-orchestrator/     cluster 主控、worker 选择、重试工具
docs/
  matrix/                          主矩阵运行时台账
  cluster/                         cluster 节点矩阵与 cluster 台账
  nodes/                           node-local 运行时台账
  ops/                             内容指派、冲突、override 台账
references/                        各平台 workflow 说明
scripts/                           上传暂存与清理脚本
card-preview/                      社媒卡片预览实验目录
ai-news-pipeline/                  AI 新闻抓取、生成、发布实验目录
```

## 当前开发进度

- 发布执行主链路已经成型，核心方式是浏览器自动化，不是平台 API 集成。
- 账号矩阵、验证矩阵、任务队列、结果 ledger 已经按 markdown ledger 方式固定下来。
- `matrix-orchestrator` 与 `openclaw-cluster-orchestrator` 已有成套脚本和测试，cluster V1 已支持 readiness 检查、节点 fan-out、结果汇总与 retry / requeue。
- 截至 `2026-03-27`，`docs/cluster/node-matrix.md` 中已有 3 个 worker 定义，其中 2 个是 `ready`，1 个是 `paused`。
- 真实发布覆盖仍然不均匀，当前应以 `docs/matrix/verification-matrix.md` 和 `docs/cluster/cluster-result-ledger.md` 作为事实来源。

## 已知限制 / 下一步

- 平台支持并不等于都完成了真实发帖验证，部分 workflow 仍是模板级或提交流程级验证。
- Browser Relay 必须提前附着并处于 `ON`，目标账号也必须已经登录，否则任务会在预检或派发阶段被拦下。
- 上传型平台建议先把素材暂存到 `/tmp/openclaw/uploads`，避免浏览器文件选择阶段失焦或读不到路径。
- 当前还没有完整 dashboard、指标面板、团队权限模型或 OA / IM 深度集成。
- 下一阶段最值得做的是继续补真实验证覆盖、扩充 worker 容量，并把非 `publish` 型 job 逐步补齐。

## 相关文档

- [GUIDE.md](./GUIDE.md)：安装、配置、channel、cluster 使用手册
- [docs/matrix/verification-matrix.md](./docs/matrix/verification-matrix.md)：平台验证状态
- [docs/cluster/node-matrix.md](./docs/cluster/node-matrix.md)：当前 worker 矩阵
- [docs/project-portfolio-status.html](./docs/project-portfolio-status.html)：当前这 5 个项目的作用与开发进度总览
