---
name: ai-dev-flow-v0.8-lite-prototype
description: 默认关闭的 v0.8 精简工作流原型，仅供 LEAN-002 固定评估或用户明确点名时使用。
---

# ai-dev-flow v0.8 Lite 原型

> 状态：默认关闭、未发布、未接入现行 `skills/ai-dev-flow/SKILL.md`。删除本目录即可整体回退。

## 使用边界

仅在以下任一条件满足时加载本原型：

1. `LEAN-002` 固定评估明确指定本文件；
2. 用户明确要求试用 `v0.8-lite` 原型。

其他任务继续使用现行 v0.7 工作流。本原型不授权 commit、merge、push、release、外部写入、真实环境操作或状态跃迁。

## 最小流程

1. 读用户请求、项目规则、Git 状态和直接相关文件。
2. 先检查 authority、外部副作用、真实环境、敏感数据和不可逆风险。
3. 按下方条件路由；不确定时向更严格档升级。
4. 冻结允许修改文件与完成标准，再做最小改动。
5. 运行覆盖全部完成标准的确定性验证和 `git diff --check`。
6. 报告实际修改、验证、风险与未完成状态，不把自动化通过写成用户验收或交付完成。

## Lite 路由

只有同时满足以下条件才使用 Lite：

- 任务为 A/B 级、范围小且可回退；
- 用户已授权该改动；
- 无外部写入、delivery、发布、数据库迁移、敏感数据或不可逆动作；
- 无真实环境或用户观察要求；
- 每项完成标准都有确定性验证；
- 未命中项目规则要求独立 Review 的风险标记。

Lite 不创建 TASK、不调用 Reviewer、不进入 repair loop，也不提出流程性验收问题。验证失败时只做同一冻结范围内的直接修复；范围或风险改变则升级 Tracked。

## Tracked / Controlled

- 不满足 Lite，但仍是可隔离、可审查的仓库改动：Tracked。
- 涉及外部副作用、真实环境、delivery、发布、不可逆动作或高风险 authority：Controlled。
- 两档都使用 TASK 作为边界与事实源，并按 [CORE.md](references/CORE.md) 执行审核、修复和停止规则。
- 缺少所需 Reviewer、authority 或证据时必须 `Blocked` 或请求明确授权，不得自批或静默降级。

## 输出格式

最终交接只包含可验证事实：

- 修改文件及各自作用；
- 实际执行的验证命令与结果；
- Review、UA、commit、merge、release、Closed 各自状态；
- 剩余风险与下一步。

