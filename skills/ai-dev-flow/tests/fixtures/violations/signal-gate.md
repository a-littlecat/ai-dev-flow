# FIX-SIGNAL：信号门禁反例

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `FIX-SIGNAL`
- `task_type`: `repair`
- `task_class`: `C`
- `lifecycle`: `In Progress`
- `review_status`: `Needs Fix`
- `ua_level`: `UA5`
- `ua_status`: `Failed`
- `ua_evidence`: `#feedback`
- `overlays`: `real_env_signal`

## 用户验收反馈 / 实机测试反馈

<a id="feedback"></a>
- 反馈分类：原任务未完成
- 是否属于当前 TASK 范围：是
- 下一步建议：进入修复任务（repair_task）

## 实机测试信号复现（real_env_signal）

- RED 失败信号：命令返回失败。
- GREEN 通过信号：命令返回成功。

## 目标与边界

- 目标：验证缺少 SIGNAL 时阻止修复。
- 非目标：none
- 允许修改：fixture 输入。
- 禁止修改：合同规范。

## 完成标准与验证

- 完成标准：只产生 signal gate diagnostic。
- 验证命令或检查：对照 manifest 精确集合。

## Outcome

- Base / Diff：base=fixture-base
- 隔离位置：fixture/signal-gate
- 回滚方式：删除测试 fixture。
- UA 动作与结果：UA5 失败证据记录于 feedback 锚点。
