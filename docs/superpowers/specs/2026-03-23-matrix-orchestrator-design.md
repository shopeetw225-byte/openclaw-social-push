# Matrix Orchestrator Design

日期：2026-03-23

## 背景

当前仓库已经有两层能力：

- `social-push`：多平台发布执行层
- `account-matrix`：账号矩阵、验证矩阵、发布前检查模板层

但还缺一层真正可执行的调度器，用来在“读矩阵 → 做预检 → 调发布 → 写结果”之间形成闭环。

本设计新增一个独立的 `matrix-orchestrator` skill/CLI 形态，用作：

- 任务调度层
- 发布前决策层
- 结果回填层

它不会替代 `social-push`，而是建立在 `social-push` 之上。

## 目标

- 新增一个独立 `matrix-orchestrator/` 目录
- 作为 OpenClaw skill / CLI 工作，不做 Web 界面
- 读取运行时矩阵文档并生成明确的 `go / warn / block` 决策
- 在通过预检时调用现有 `social-push`
- 将结果写回：
  - 运行日志
  - 结果台账
  - 验证矩阵

## 非目标

- 不做 Web 控制台
- 不做权限系统
- 不做数据库
- 不做跨机器调度
- 不替代现有 `social-push` workflow

## 一句话架构

`matrix-orchestrator` = `account-matrix` 的事实读取器 + `social-push` 的调度前置层 + 发布结果回填器
