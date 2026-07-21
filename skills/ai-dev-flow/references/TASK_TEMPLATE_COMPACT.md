# v0.7 Compact TASK 兼容模板

> 本文件只为 v0.7 Writer/Reader、golden fixtures 和既有项目保留。v0.8 的 Lite 结果为 `DoNotUseSkill`，不创建 Compact TASK；新建任务按 `SKILL.md` 路由选择 `TASK_TEMPLATE_BRIEF.md` 或 `TASK_TEMPLATE.md`，全部 Controlled 使用完整模板。旧任务无需迁移。

```markdown
# <TASK-ID>：<任务标题>

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `<TASK-ID>`
- `task_type`: `<document|plan|code|review|repair|test>`
- `task_class`: `<A|B>`
- `lifecycle`: `<Draft|Ready|In Progress|Blocked|Review|Needs Fix|Accepted|Closed|Deferred|Cancelled>`
- `review_status`: `<Pending|In Review|Passed|Needs Fix|Do Not Merge>`
- `ua_level`: `<UA0|UA1|UA2|UA3|UA4|UA5|UA6|UA7|TBD>`
- `ua_status`: `<Not Required|Pending|Passed|Failed|Deferred|TBD>`

## 目标与边界

- 目标：<待填写>
- 非目标：<待填写>
- 允许修改：<待填写>
- 禁止修改：<待填写>

## 完成标准与验证

- [ ] <标准与证据>

## Outcome

- Base / Diff：<待填写>
- 修改文件：<待填写>
- 验证结果：<待填写>
- Review / UA：<待填写>
- 剩余风险：<待填写>
```

兼容写入只能更新现有 Contract 和 Outcome，不重建 legacy 的重复状态段落。条件未知时停止并写“待确认”，不得用本模板替代 v0.8 路由。
