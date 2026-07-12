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
- 任务范围：current
- 下一步建议：进入修复（repair_task）
- RED：命令返回失败。
- GREEN：命令返回成功。
