# CMP-4A6C417：RED GREEN SIGNAL 顺序门禁收紧

> 基于真实 Git 变更 `4a6c417` 回填；不表示历史上存在此 TASK。

## Workflow Contract

- `schema_version`: `adf/v0.7.0`
- `task_id`: `CMP-4A6C417`
- `task_type`: `document`
- `task_class`: `A`
- `lifecycle`: `Review`
- `review_status`: `Passed`
- `ua_level`: `UA2`
- `ua_status`: `Pending`
- `commit_status`: `Committed`

## 目标与边界

- 目标：固定 RED、GREEN、SIGNAL 的顺序门禁。
- 非目标：不执行真实环境测试。
- 允许修改：PROMPTS、REAL_ENV_SIGNAL_GUIDE、TASK_TEMPLATE。
- 禁止修改：Skill 脚本与版本文件。

## 完成标准与验证

- 完成标准：三处规则的信号顺序一致。
- 验证命令或检查：检查 `4a6c417^..4a6c417` diff 与信号关键词。

## Outcome

- Base / Diff：base=4a6c417^;diff=4a6c417^..4a6c417
- 修改文件：PROMPTS、REAL_ENV_SIGNAL_GUIDE、TASK_TEMPLATE。
- 验证证据：`git show --stat 4a6c417`
- Review findings：none
