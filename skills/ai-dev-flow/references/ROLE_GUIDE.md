# Role Guide

本文件定义 ai-dev-flow 中常见角色的职责边界。角色用于约束本轮输出的行为，不绑定具体 agent、模型或商业服务。

## 核心原则

- 同一 agent 可以在不同时间扮演不同角色。
- 同一轮输出必须声明当前角色。
- Reviewer 不修复。
- Engineer 不自批。
- Repairer 只修复审查指出的问题。
- Verifier 只验证，不改业务逻辑。
- Orchestrator 不直接改业务代码。

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
