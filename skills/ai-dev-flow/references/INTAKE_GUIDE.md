# Intake 指南

Intake 用于在 `create_task` 或 `plan_task` 前记录需求上下文。它的目标是让 AI agent 不要从一句模糊需求直接进入任务拆分或代码执行。

## Intake 是什么

- 需求进入项目流程前的整理记录。
- 用来保存用户原话、背景、目标、非目标、成功标准、约束和模糊点。
- 可帮助判断下一步应进入 `plan_task`、`create_task`、`status_report`，或先 `Blocked` 等待澄清。

## Intake 不是什么

- Intake 不是 TASK。
- Intake 不进入任务状态机。
- Intake 不直接执行代码。
- Intake 不替代 plan / RFC。
- Intake 不替代用户确认。

## 什么时候需要 Intake

- 用户需求较长、较模糊或包含多个方向。
- 需求可能影响多个模块、长期计划或项目规则。
- 成功标准、非目标、约束或风险尚不清楚。
- 需要在拆任务前记录合理假设。

## 什么时候可以跳过 Intake

- 用户已经给出明确 TASK 文件。
- 小范围 A/B 文档任务，目标和完成标准都清楚。
- 只做状态汇总、只读审查或简单问题回答。

## Intake 到 Plan / Task 的转换

- 需求范围大、影响多模块或风险高：转为 `plan_task`。
- 需求清楚且可拆成小任务：转为 `create_task`。
- 缺少关键信息：标记为 Blocked，等待用户澄清。
- 只是了解当前状态：转为 `status_report`。

转换时必须保留：

- 原始需求摘要。
- 关键假设。
- 成功标准。
- 非目标。
- 模糊点处理方式。

## Intake 文件建议位置

```text
docs/intake/
├── INTAKE-001.md
└── INTAKE-002.md
```

如果项目较小，也可以只在 `docs/TASK_BOARD.md` 或任务文件中记录需求来源摘要。

## INTAKE-xxx.md 模板

```markdown
# INTAKE-xxx：需求标题

## 原始需求

- 用户原话：
- 相关链接：
- 背景：

## 目标

- 待填写

## 非目标

- 待填写

## 成功标准

- 待填写

## 约束

- 时间：
- 技术：
- 兼容性：
- 安全：
- 用户体验：

## 模糊点

| 问题 | 是否阻塞 | 建议处理 |
| --- | --- | --- |
| 待填写 | 是 / 否 | 询问用户 / 做合理假设 / 写入风险 |

## 可逆性判断

- 变更是否容易回滚：是 / 否 / 待确认
- 如果判断错误的代价：低 / 中 / 高

## 建议下一步

- create_task
- plan_task
- status_report
- Blocked，等待用户补充
```

## Intake 输出提示词

```text
请使用 ai-dev-flow 的 Intake 流程整理以下需求，不要拆任务，不要改代码。

输入：
<粘贴需求>

要求：
1. 当前模式：create_task 前的 Intake。
2. 输出 INTAKE-xxx.md 内容草案。
3. 写清原始需求、目标、非目标、成功标准、约束、模糊点和可逆性判断。
4. 合理假设必须显式标记。
5. 如果有阻塞问题，标记 Blocked 并列出需要用户回答的问题。
6. 建议下一步：plan_task / create_task / status_report / Blocked。
7. 不要修改业务代码，不要创建 TASK，不要执行 Git 操作。
```
