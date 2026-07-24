# 单会话 Tracked TASK 简版模板

> Skill 包 `0.8.2` 开发线沿用，当前尚未形成对应 tag / Release。仅用于同时满足以下条件的 Tracked 任务：运行在大上下文模型上（完整任务与 diff 可留在会话内）、预期单会话内完成、无跨会话交接需求。其余 Tracked 任务与全部 Controlled 任务一律使用 `TASK_TEMPLATE.md`。Contract schema 仍为 `adf/v0.7.0`，不随模板简化而变化。

```markdown
# <TASK-ID>：<任务标题>

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B|C>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_status`: `<Pending|In Review|Passed|Needs Fix|Do Not Merge>`
- `ua_level`: `<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>`
- `ua_status`: `<Not Required|Pending|Passed|Failed|Deferred|TBD>`

## 目标与边界

- 目标：<可观察结果>
- 允许修改：<文件/模块>
- 禁止修改：<文件/模块/动作>
- 未授权动作：<merge/push/release/delete/external sync/Closed 等>

## 完成标准与验证

- [ ] <完成标准>：<验证命令/人工步骤/证据>
- [ ] `git diff --check` 通过，diff 可归属当前 TASK。

## Outcome

- Base / Diff：<base..HEAD 或工作区范围>
- 修改文件：<路径和作用>
- 验证命令与结果：<命令、退出码、关键结果>
- Review / UA：<稳定 finding ID、严重度、状态；或 Skipped by policy（review_status 保持 Pending）；UA 动作与结果>
- 剩余风险与下一步：<无或明确列出>
```

写回规则与 `TASK_TEMPLATE.md` 相同：执行者不自批 Review；`Skipped by policy` 不等于 `Passed`，未做真实只读 Review 时 `review_status` 保持 `Pending`；进入 repair、范围/风险变化或出现跨会话需求时，升级回完整模板并记录 repair chain，换 TASK 不重置计数。
