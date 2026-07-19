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

## 路由、审核与修复

[CORE.md](references/CORE.md) 中 `POLICY_JSON` 是三档路由、Reviewer 闸门和第 3 轮 repair 的唯一规则源；本文不复制第二套触发列表。

- Lite 不创建 TASK、不调用 Reviewer、不进入 repair loop，也不提出流程性验收问题。
- Tracked 使用 TASK；只有 policy 的确定性风险标记命中时才调用一个隔离只读 Reviewer。
- Controlled 使用完整 TASK，并在验收建议、delivery、merge 或 release 前强制独立 Review。
- policy 无法解析、字段未知或所需 authority/capability/evidence 缺失时，必须 `Blocked`，不得猜测降级。
- 验证失败只能在冻结范围内直接修复；范围或风险改变时重新路由。

## 输出格式

最终交接只包含可验证事实：

- 修改文件及各自作用；
- 实际执行的验证命令与结果；
- Review、UA、commit、merge、release、Closed 各自状态；
- 剩余风险与下一步。
