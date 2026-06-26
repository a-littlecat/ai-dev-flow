# Role Guide

本文件定义 ai-dev-flow 中常见角色的职责边界。角色用于约束本轮输出的行为，不绑定具体 agent、模型或商业服务。

## 核心原则

- 角色不是会话，不要求每个角色都单独开一个会话。
- 同一 agent 可以在不同时间扮演不同角色。
- 同一轮输出必须声明当前角色。
- Reviewer 不修复。
- Engineer 不自批。
- Repairer 只修复审查指出的问题。
- Verifier 只验证，不改业务逻辑。
- Orchestrator 不直接改业务代码。
- 子 agent 是可选加速手段，不是默认依赖。

## 角色表

| 角色 | 职责 | 不得做 | 模型能力建议 |
| --- | --- | --- | --- |
| Orchestrator | 总览、分拣、状态报告、选择下一步 | 不直接改业务代码 | 低到中 |
| Planner | Intake、Plan、RFC、任务拆分 | 不直接执行代码 | 中到高 |
| Engineer | 执行 scoped coding task | 不自我批准，不扩大范围 | 中到高 coding |
| Reviewer | 审查 diff、风险、完成标准 | 不直接修复 | 高 judgment |
| Verifier | 运行验证、整理证据 | 不扩大修改范围 | 低到中 |
| Repairer | 根据审查意见修复 | 不做无关优化 | 中到高 coding |
| Archivist | 更新 TASK_BOARD、CHANGELOG、DECISIONS、Memory | 不改业务代码 | 低到中 |

## 角色不等于会话

ai-dev-flow 使用“角色”来约束当前输出的职责边界，不用它来强制规定会话数量。

默认最小会话模型：

- 总览会话：Orchestrator / Planner / Archivist。
- 执行会话：Engineer / Verifier / Repairer。
- 审核会话：Reviewer。

这意味着一个会话可以在不同阶段切换多个角色，但每一轮输出必须声明当前角色、当前模式和允许范围。这样可以降低“每个角色都要开新会话”的负担，也能避免同一轮里一边写代码一边批准自己的改动。

如果同一会话切换角色，必须遵守：

- 切换前先完成上一角色的输出，例如 Engineer 完成修改和验证记录后，才能进入 Verifier 或交给 Reviewer。
- Reviewer 角色不得直接修复；如果需要修复，应切回 Repairer，并只处理审查指出的问题。
- Engineer / Repairer 不得自我批准；最终是否允许进入验收建议，应由 Reviewer 或独立审查步骤给出。
- 中高风险任务仍建议使用独立审核会话，避免同一上下文里遗漏风险。

## 子 agent 使用原则

子 agent 可以用来加速，但不是 ai-dev-flow 的默认依赖。没有可靠子 agent 的 harness，应使用普通独立会话或手动步骤。

推荐使用子 agent 的场景：

- 只读审查：基于 diff 检查范围、风险和完成标准。
- 验证：运行或复核验证命令、整理证据。
- 状态分拣：读取 TASK_BOARD，推荐下一步、Batch 或 Wave 候选。
- 文档检查：检查链接、模板字段、状态机一致性和文字冲突。

不推荐或禁止：

- 不推荐默认让多个写代码的子 agent 共享同一工作区。
- 不允许子 agent 自动 merge、push、release 或 delete。
- 不允许写代码的子 agent 自我批准。
- 不允许子 agent 跳过 Git baseline、diff review、任务文件更新或用户确认。

如果 harness 支持可靠子 agent，可以优先把 Reviewer / Verifier 交给子 agent，减少额外人工开审核会话的负担。但 C/D 任务、高风险任务、真实环境任务、UA5 / UA6 / UA7 任务仍建议保留独立审核会话。

代码并行仍必须遵守 Parallel Wave 规则：每个代码任务默认使用独立分支或 Worktree，逐任务记录 base commit、HEAD、diff 范围、验证结果和审查结论。

## 角色选择建议

- 需求模糊：Planner。
- 任务分拣：Orchestrator。
- 执行代码任务：Engineer。
- 审查 diff：Reviewer。
- 根据审查修复：Repairer。
- 运行验证和整理证据：Verifier。
- 更新长期记录：Archivist。

## 角色切换规则

- 从 Engineer 切到 Reviewer 前，应完成验证并记录 diff。
- 从 Reviewer 切到 Repairer 前，应有明确审查结论。
- 从 Repairer 回到 Reviewer 时，应重新审查修复 diff。
- 从任意角色执行危险操作前，必须用户确认。

## 输出格式

```markdown
## 当前角色

- 角色：Orchestrator / Planner / Engineer / Reviewer / Verifier / Repairer / Archivist
- 当前模式：
- 允许做：
- 不得做：
- 是否需要用户确认：
```
