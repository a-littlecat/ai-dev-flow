# 单会话 Tracked TASK 简版模板（v0.10）

> 仅用于单会话、单执行者、范围明确、无交接、无 Repair、无真实环境/用户观察且非 Controlled 的 Tracked 任务。模板选择只看任务形状，不看模型名称或上下文窗口。进入 Repair、范围/风险变化或跨会话时升级为 `TASK_TEMPLATE.md`。

```markdown
# <TASK-ID>：<任务标题>

## Workflow Contract

- `schema_version`: `adf/v0.10.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B|C>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_requirement`: `<Required|Not Required>`
- `review_status`: `<Not Run|In Review|Passed|Needs Fix|Blocked>`
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
- 验证证据：<命令、退出码、关键结果>
- Review findings：<稳定 finding ID、严重度、状态；未运行且 Not Required 时写 none>
- UA 动作与结果：<等级、用户需做什么、Pending/Passed/Failed>
- 剩余风险与下一步：<无或明确列出>
```

写回规则与 `TASK_TEMPLATE.md` 相同：`review_requirement` 必须由 `policy/core.json` 路由结果派生；执行者不自批 Review；`Not Required + Not Run` 是合法未运行状态，不等于 `Passed`。自愿 Review 一旦开始或产生 finding，必须保留并处理真实状态。进入 Repair 时先升级完整模板，换 TASK 不重置同一 finding chain 的计数。
