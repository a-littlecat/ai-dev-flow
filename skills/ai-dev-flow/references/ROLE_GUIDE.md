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
- 角色不是 subagent；一个角色可以由主 agent 执行，也可以由 harness 的 subagent 辅助。
- subagents 是可选加速能力，不是默认依赖。

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

## Subagent 使用原则

ai-dev-flow 不禁止 harness 或模型自动使用 subagents。它限制的是无边界、不可追踪、不可审查、不可回滚的 subagent 行为。

subagents 是可选加速能力，不是默认依赖。没有可靠 subagents 的 harness，应使用普通独立会话或手动步骤；流程仍然可以通过 Markdown、Git 和 TASK 文件稳定运行。

### 只读 subagents

只读 subagents 默认允许，适合辅助：

- Reviewer：基于 diff 检查范围、风险和完成标准。
- Verifier：运行或复核验证命令、整理测试结果。
- Orchestrator：读取 TASK_BOARD，推荐下一步、Batch 或 Wave 候选。
- Archivist：做文档检查、Markdown 链接检查和记录一致性检查。

只读 subagents 不得修改业务代码、测试、配置或文档；不得改变任务状态，除非用户或项目规则允许。

### 写代码 subagents

Engineer / Repairer 可以在受控条件下使用写代码 subagent，但必须更严格记录边界和 diff。

写代码 subagent 必须声明：

- 任务编号。
- 当前角色。
- 当前模式。
- 允许修改范围。
- 禁止修改范围。
- 验证方式。

写代码 subagent 必须遵守 TASK 边界，记录修改文件、验证结果和遗留风险。它不得自我批准，最终仍需 Reviewer 审查。

中高风险任务仍建议独立审核会话或明确 Reviewer 隔离。

### 多个写代码 subagents 并行

多个写代码 subagents 并行默认需要用户确认，且默认使用独立分支或 Worktree。

并行前必须检查：

- 文件锁。
- 模块锁。
- 依赖关系。
- diff 归属。

多个写代码 subagents 不得默认共享同一工作区修改同一批文件。如果无法确认隔离和 diff 归属，必须停止并标记 `Blocked` 或待确认。

### 内部不可见 subagents

如果 model / harness 内部自动使用 subagents，但不暴露每个内部子代理细节，主 agent 不需要为每个内部 subagent 单独创建 TASK 文件。但主 agent 必须汇总能力使用情况，并保证最终 TASK 边界、diff、验证证据、未验证项和风险清楚。

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
