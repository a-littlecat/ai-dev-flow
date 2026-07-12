# FIX-FEEDBACK-SCOPE：反馈范围反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-FEEDBACK-SCOPE`
- `task_type`: `repair`
- `task_class`: `C`
- `lifecycle`: `In Progress`
- `review_status`: `Needs Fix`
- `ua_level`: `UA5`
- `ua_status`: `Failed`
- `ua_evidence`: `#feedback`

## 用户验收反馈 / 实机测试反馈

<a id="feedback"></a>
- 反馈分类：新需求或范围扩大
- 是否属于当前 TASK 范围：否
- 下一步建议：进入修复任务（repair_task）

## 目标与边界

- 目标：验证 scope expansion 会阻止当前任务修复。
- 非目标：none
- 允许修改：fixture 输入。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：只产生 scope diagnostic。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base
- 隔离位置：fixture/feedback-scope
- 回滚方式：删除测试 fixture。
- UA 动作与结果：UA5 失败证据记录于 feedback 锚点。
